"""S10: the proactive morning routine, triggered by the GitHub Actions cron (POST /api/jobs/daily)."""

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import Case, Document, Hit, InfoRequest, ListEntry, Merchant, log
from .tools import gemini, google, screening
from .workflow import draft_email, request_info, upload_link

EXPIRY_WINDOW = 30


def run(db: Session, today: date | None = None, refresh_lists: bool = True) -> dict:
    today = today or date.today()
    summary = {"new_list_entries": 0, "rescreen_hits": [], "renewals": [], "reviews": [], "reminders": [],
               "escalations": [], "replies": []}
    log(db, "routine_started", actor="routine", day=today.isoformat())

    # 1. Sanctions delta: screen approved merchants against entries first seen today only.
    if refresh_lists:
        try:
            screening.refresh(db, today)
        except Exception as e:
            log(db, "list_refresh_failed", actor="routine", error=str(e)[:200])
    delta = list(db.scalars(select(ListEntry).where(ListEntry.first_seen == today)))
    summary["new_list_entries"] = len(delta)
    approved = list(db.scalars(select(Merchant).where(Merchant.status == "approved")))
    if delta:
        for m in approved:
            subjects = [{"name": m.name, "kind": "entity", "country": m.country, "activity": m.category}] + [
                {"name": o["name"], "kind": "individual", "dob": o.get("dob"), "nationality": o.get("nationality")}
                for o in m.owners]
            for r in screening.screen(db, subjects, delta):
                db.add(Hit(merchant_id=m.id, subject=r["subject"], entry_id=r["entry"].id, score=r["score"],
                           verdict=r["verdict"], reasons=r["reasons"]))
                if r["verdict"] == "likely_match":
                    _case(db, m, "rescreen_hit", today, f"New {r['entry'].source} entry '{r['entry'].name}' may "
                                                        f"match {r['subject']}: {'; '.join(r['reasons'])}")
                    summary["rescreen_hits"].append(f"{m.name}: {r['subject']} ~ {r['entry'].name}")
                log(db, "rescreened", m.id, actor="routine", subject=r["subject"], entry=r["entry"].name,
                    verdict=r["verdict"])

    # 2. Documents expiring within 30 days -> renewal case + upload request.
    soon = today + timedelta(days=EXPIRY_WINDOW)
    for d in db.scalars(select(Document).join(Merchant).where(
            Merchant.status == "approved", Document.status == "extracted",
            Document.expires_on.is_not(None), Document.expires_on <= soon)):
        m = d.merchant
        if any(c.kind == "renewal" and c.status == "open" and d.doc_type in c.detail for c in m.cases):
            continue
        _case(db, m, "renewal", d.expires_on, f"{d.doc_type} expires {d.expires_on:%d %b %Y}")
        request_info(db, m, [{"doc_type": d.doc_type, "text": f"Upload your renewed {d.doc_type.replace('_', ' ')} "
                                                                f"(current one expires {d.expires_on:%d %b %Y})."}],
                     due=min(d.expires_on, today + timedelta(days=14)))
        m.status = "approved"  # a renewal does not suspend a live merchant
        summary["renewals"].append(f"{m.name}: {d.doc_type} expires {d.expires_on:%d %b}")

    # 3. Periodic reviews that fall due.
    for m in approved:
        if m.next_review and m.next_review <= today and not any(
                c.kind == "periodic_review" and c.status == "open" for c in m.cases):
            _case(db, m, "periodic_review", today, f"{m.risk_tier} risk: periodic review due {m.next_review:%d %b %Y}")
            summary["reviews"].append(m.name)

    # 4. Overdue information requests: reminders with a firmer tone, escalate after the second.
    for req in db.scalars(select(InfoRequest).where(InfoRequest.status == "open", InfoRequest.due_on < today)):
        m = req.merchant
        if req.reminders >= 2:
            req.status = "escalated"
            log(db, "request_escalated", m.id, actor="routine", days_overdue=(today - req.due_on).days)
            summary["escalations"].append(m.name)
            continue
        req.reminders += 1
        body = draft_email(m, req.items, today + timedelta(days=3), upload_link(req.id), reminder=req.reminders)
        google.send(m.email, f"Reminder: documents still needed for {m.name}", body, req.thread_id)
        log(db, "reminder_sent", m.id, actor="routine", reminder=req.reminders)
        summary["reminders"].append(f"{m.name} (#{req.reminders})")

    # 5. Merchant replies in request threads.
    summary["replies"] = check_replies(db)

    # 6. Digest for the analyst.
    db.flush()
    summary["waiting_decision"] = [m.name for m in db.scalars(select(Merchant).where(Merchant.status == "ready"))]
    google.send(settings().agent_email, f"Wekil digest {today:%d %b %Y}", _digest(summary))
    log(db, "routine_finished", actor="routine", **{k: v if isinstance(v, int) else len(v) for k, v in summary.items()})
    db.commit()
    return summary


class Reply(BaseModel):
    intent: Literal["documents_coming", "question", "refusal", "other"]
    summary: str


def check_replies(db: Session) -> list[str]:
    out = []
    for req in db.scalars(select(InfoRequest).where(InfoRequest.status == "open", InfoRequest.thread_id.is_not(None))):
        for r in google.replies(req.thread_id):
            if r["id"] in req.reply_ids:
                continue
            c = gemini.ask(f"Classify this merchant reply to our document request and summarise it in one sentence."
                           f"\nREQUEST: {[i['text'] for i in req.items]}\nREPLY: {r['text']}", Reply)
            req.reply_ids = [*req.reply_ids, r["id"]]
            log(db, "merchant_replied", req.merchant_id, actor="merchant", intent=c.intent, summary=c.summary)
            out.append(f"{req.merchant.name}: {c.intent.replace('_', ' ')}: {c.summary}")
    return out


def _case(db: Session, m: Merchant, kind: str, due: date, detail: str) -> None:
    db.add(Case(merchant_id=m.id, kind=kind, due_on=due, detail=detail))
    log(db, "case_opened", m.id, actor="routine", kind=kind, detail=detail)


def _digest(s: dict) -> str:
    lines = ["Good morning. Here is what Wekil did overnight and what needs you today.", ""]
    for key, title in [("waiting_decision", "Ready for your decision"), ("rescreen_hits", "Possible sanctions matches"),
                       ("renewals", "Renewals requested"), ("reviews", "Periodic reviews due"),
                       ("reminders", "Reminders sent"), ("escalations", "Escalated (no reply after 2 reminders)"),
                       ("replies", "Merchant replies")]:
        if s.get(key):
            lines += [f"{title}:", *[f"  - {x}" for x in s[key]], ""]
    lines.append(f"New sanctions-list entries screened: {s['new_list_entries']}")
    lines.append(f"\nOpen Wekil: {settings().frontend_url}")
    return "\n".join(lines)

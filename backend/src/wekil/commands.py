"""The command bar: plain-English requests -> Gemini function calling over Wekil's tools.

Read tools run immediately. Write tools (emails, calendar) are never executed by the model: they come back as a
proposed plan that the analyst confirms in the UI (POST /api/commands/confirm)."""

from datetime import date, timedelta

from google.genai import types
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import InfoRequest, Merchant, log, now
from .tools import gemini, google, screening
from .workflow import draft_email, request_info, upload_link

WRITE_TOOLS = {"send_reminders", "schedule_review", "request_documents"}


def _find(db: Session, name: str) -> Merchant:
    m = db.scalar(select(Merchant).where(func.lower(Merchant.name).contains(name.lower().strip())))
    if not m:
        raise ValueError(f"No merchant matching '{name}'")
    return m


def tools(db: Session) -> dict:
    def search_applications(status: str = "", waiting_more_than_days: int = 0, name: str = "") -> list[dict]:
        """Find merchant applications. status is one of submitted, reviewing, awaiting_merchant, ready, approved,
        rejected, needs_attention (empty = any). waiting_more_than_days filters on days since the latest open
        information request (or since application if none)."""
        q = select(Merchant)
        if status:
            q = q.where(Merchant.status == status)
        if name:
            q = q.where(func.lower(Merchant.name).contains(name.lower()))
        out = []
        for m in db.scalars(q):
            open_req = next((r for r in reversed(m.requests) if r.status == "open"), None)
            since = (open_req.created_at if open_req else m.created_at)
            days = (now() - since).days
            if days >= waiting_more_than_days:
                out.append({"name": m.name, "status": m.status, "risk_tier": m.risk_tier, "days_waiting": days,
                            "open_request_due": open_req.due_on.isoformat() if open_req else None})
        return out

    def explain_risk(merchant_name: str) -> dict:
        """Explain a merchant's risk tier: score factors, document findings, sanctions hits and memo."""
        m = _find(db, merchant_name)
        return {"name": m.name, "tier": m.risk_tier, "score": m.risk_score, "factors": m.risk_factors,
                "document_findings": m.issues, "registry": m.registry_check,
                "hits": [{"subject": h.subject, "entry": h.entry.name, "verdict": h.verdict, "reasons": h.reasons,
                          "analyst_decision": h.decision} for h in m.hits], "memo": m.memo}

    def screen_name(name: str, kind: str = "entity") -> list[dict]:
        """Screen any name against the OFAC and UN sanctions lists. kind is 'entity' or 'individual'."""
        return [{"entry": r["entry"].name, "list": r["entry"].source, "similarity": r["score"],
                 "verdict": r["verdict"], "reasons": r["reasons"]}
                for r in screening.screen(db, [{"name": name, "kind": kind}])] or [{"result": "no candidates"}]

    def summarize_queue() -> dict:
        """Counts of applications by status, decisions waiting, overdue requests."""
        counts = dict(db.execute(select(Merchant.status, func.count()).group_by(Merchant.status)).all())
        overdue = db.scalars(select(InfoRequest).where(InfoRequest.status == "open",
                                                       InfoRequest.due_on < date.today()))
        return {"by_status": counts, "overdue_requests": [r.merchant.name for r in overdue],
                "ready_for_decision": [m.name for m in db.scalars(select(Merchant).where(Merchant.status == "ready"))]}

    def send_reminders(merchant_names: list[str]) -> str:
        """WRITE: email a reminder to each merchant about their open information request."""
        sent = []
        for n in merchant_names:
            m = _find(db, n)
            req = next((r for r in reversed(m.requests) if r.status == "open"), None)
            if not req:
                continue
            req.reminders += 1
            body = draft_email(m, req.items, max(req.due_on, date.today() + timedelta(days=2)),
                               upload_link(req.id), reminder=req.reminders)
            google.send(m.email, f"Reminder: documents still needed for {m.name}", body, req.thread_id)
            log(db, "reminder_sent", m.id, actor="analyst", via="command", reminder=req.reminders)
            sent.append(m.name)
        return f"Reminders sent to: {', '.join(sent) or 'nobody (no open requests)'}"

    def schedule_review(merchant_name: str, review_date: str) -> str:
        """WRITE: set a merchant's next periodic review date (YYYY-MM-DD) and put it on the compliance calendar."""
        m = _find(db, merchant_name)
        m.next_review = date.fromisoformat(review_date)
        google.event(f"Periodic KYB review: {m.name}", m.next_review)
        log(db, "review_scheduled", m.id, actor="analyst", via="command", date=review_date)
        return f"Review for {m.name} scheduled on {review_date}"

    def request_documents(merchant_name: str, items: list[str]) -> str:
        """WRITE: email the merchant a request for the listed items with an upload link (due in 5 days)."""
        m = _find(db, merchant_name)
        request_info(db, m, [{"doc_type": None, "text": t} for t in items])
        return f"Requested {len(items)} item(s) from {m.name}"

    return {f.__name__: f for f in (search_applications, explain_risk, screen_name, summarize_queue,
                                    send_reminders, schedule_review, request_documents)}


SYSTEM = (gemini.SYSTEM + " Today is {today}. You answer the compliance analyst's requests by calling tools. "
          "Read tools give you facts; never guess. When the request needs an action (emails, scheduling, "
          "requesting documents), call the write tool: it will be shown to the analyst for confirmation, so say "
          "what you propose. Answer in at most 5 short sentences or a short list.")


def run(db: Session, text: str) -> dict:
    fns = tools(db)
    config = types.GenerateContentConfig(
        tools=list(fns.values()), temperature=0.1, system_instruction=SYSTEM.format(today=date.today()),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    contents: list = [types.Content(role="user", parts=[types.Part.from_text(text=text)])]
    proposals, steps = [], []
    for _ in range(6):
        resp = gemini.call(contents, config)
        if not resp.function_calls:
            return {"answer": resp.text, "proposals": proposals, "steps": steps}
        contents.append(resp.candidates[0].content)
        parts = []
        for fc in resp.function_calls:
            args = dict(fc.args or {})
            if fc.name in WRITE_TOOLS:
                proposals.append({"tool": fc.name, "args": args})
                result = {"status": "proposed; waiting for the analyst to confirm"}
            else:
                try:
                    result = {"result": fns[fc.name](**args)}
                except Exception as e:
                    result = {"error": str(e)}
            steps.append({"tool": fc.name, "args": args})
            parts.append(types.Part.from_function_response(name=fc.name, response=result))
        contents.append(types.Content(role="user", parts=parts))
    return {"answer": "I could not finish that request.", "proposals": proposals, "steps": steps}


def confirm(db: Session, proposals: list[dict]) -> list[str]:
    fns = tools(db)
    results = [fns[p["tool"]](**p["args"]) for p in proposals if p["tool"] in WRITE_TOOLS]
    db.commit()
    return results

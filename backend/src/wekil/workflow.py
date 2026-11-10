"""The per-application review: S1 intake -> S2 documents -> S3 registry -> S5 screening -> S6 risk
-> either S7 information request (loop) or S9 memo for the analyst. Every step is logged."""

from datetime import date, timedelta

from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import Hit, InfoRequest, Merchant, SessionLocal, log, now
from .tools import documents, gemini, google, registry, risk, screening

REQUEST_DAYS = 5
LINK_AGE = 7 * 24 * 3600


def signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings().app_secret, salt="upload")


def upload_link(request_id: int) -> str:
    return f"{settings().frontend_url}/upload/{signer().dumps(request_id)}"


def current_docs(m: Merchant) -> dict:
    """Latest non-superseded document per type."""
    return {d.doc_type: d for d in m.documents if d.status != "superseded"}


def review(merchant_id: int) -> None:
    """Run in a background task with its own session."""
    with SessionLocal() as db:
        m = db.get(Merchant, merchant_id)
        try:
            _review(db, m)
        except Exception as e:  # keep the case visible to a human instead of failing silently
            db.rollback()
            m.status = "needs_attention"
            log(db, "review_failed", m.id, error=str(e)[:300])
        db.commit()


def _review(db: Session, m: Merchant) -> None:
    m.status = "reviewing"
    log(db, "review_started", m.id)
    db.commit()

    docs = current_docs(m)
    for d in docs.values():  # S2 extraction (only new files)
        if d.status == "pending":
            f = documents.extract(d.data, d.mime, d.doc_type)
            d.fields, d.expires_on, d.status = f.model_dump(mode="json"), f.expiry_date, "extracted"
            log(db, "document_read", m.id, doc_type=d.doc_type, document_type=f.document_type,
                concerns=f.concerns)
            db.commit()
    fields = {t: d.fields for t, d in docs.items() if d.status == "extracted"}
    missing, issues = documents.check(m, fields)  # S1 + S2 consistency
    m.issues = issues
    log(db, "consistency_checked", m.id, missing=missing, blockers=sum(i["severity"] == "blocker" for i in issues),
        warnings=sum(i["severity"] == "warning" for i in issues))

    m.registry_check = registry.lookup(m.name, m.country, m.registration_no)  # S3
    log(db, "registry_checked", m.id, source=m.registry_check.get("source"), status=m.registry_check.get("status"))

    _screen(db, m)  # S5
    m.risk_score, m.risk_tier, m.risk_factors = risk.score(m, m.hits, m.registry_check, issues)  # S6
    log(db, "risk_scored", m.id, tier=m.risk_tier, score=m.risk_score)

    asks = [{"doc_type": t, "text": f"Upload your {documents.DOC_TYPES[t]}."} for t in missing]
    asks += [{"doc_type": i["doc_type"], "text": ask_text(i)}
             for i in issues if i["ask"] and i["severity"] == "blocker"]
    if asks:  # S7
        request_info(db, m, asks)
        return
    m.memo = risk.memo(m, fields, m.registry_check, m.hits, issues)  # S9
    m.status = "ready"
    log(db, "memo_drafted", m.id, recommendation=m.memo.split("\n")[0][:200])


def ask_text(issue: dict) -> str:
    """Turn a finding into an instruction the merchant can act on."""
    doc = documents.DOC_TYPES.get(issue["doc_type"], "document")
    if "expired" in issue["text"]:
        return f"Upload a renewed {doc}; the one we received expired {issue['text'].split('expired ', 1)[1]}"
    return f"{issue['text']} Upload a corrected {doc}, or reply to this email to explain."


def _screen(db: Session, m: Merchant) -> None:
    subjects = [{"name": m.name, "kind": "entity", "country": m.country, "activity": m.category}]
    subjects += [{"name": o["name"], "kind": "individual", "dob": o.get("dob"), "nationality": o.get("nationality")}
                 for o in m.owners]
    seen = {(h.subject, h.entry_id) for h in m.hits}
    results = screening.screen(db, subjects)
    for r in results:
        if (r["subject"], r["entry"].id) not in seen:
            db.add(Hit(merchant_id=m.id, subject=r["subject"], entry_id=r["entry"].id, score=r["score"],
                       verdict=r["verdict"], reasons=r["reasons"]))
    db.flush()
    db.refresh(m, ["hits"])
    log(db, "screened", m.id, subjects=len(subjects), candidates=len(results),
        likely_matches=sum(r["verdict"] == "likely_match" for r in results))


def request_info(db: Session, m: Merchant, items: list[dict], due: date | None = None) -> InfoRequest:
    due = due or date.today() + timedelta(days=REQUEST_DAYS)
    req = InfoRequest(merchant_id=m.id, items=items, due_on=due)
    db.add(req)
    db.flush()
    body = draft_email(m, items, due, upload_link(req.id), reminder=0)
    req.thread_id = google.send(m.email, f"{m.name}: documents needed to finish your merchant review", body)
    google.event(f"KYB due: {m.name}", due, f"{len(items)} item(s) requested.\n{settings().frontend_url}/m/{m.id}")
    m.status = "awaiting_merchant"
    log(db, "info_requested", m.id, items=[i["text"] for i in items], due=due.isoformat(), emailed=bool(req.thread_id))
    return req


def draft_email(m: Merchant, items: list[dict], due: date, link: str, reminder: int) -> str:
    tone = ["friendly and clear", "polite but firmer: this is a reminder", "firm: final reminder before the "
            "application is closed"][min(reminder, 2)]
    bullet = "\n".join(f"- {i['text']}" for i in items)
    try:
        return gemini.write(
            f"Write a short plain-text email (no subject line) from the Wekil compliance team to {m.name} about "
            f"their merchant application. Tone: {tone}. It must list exactly these items:\n{bullet}\n"
            f"Due date: {due:%A %d %B %Y}. Upload link (include it on its own line): {link}\n"
            "Sign off as 'Wekil Compliance'. No placeholders, no markdown.")
    except RuntimeError:
        return f"Hello {m.name},\n\nTo finish your merchant review we need:\n{bullet}\n\nPlease upload by " \
               f"{due:%d %B %Y}:\n{link}\n\nWekil Compliance"


def decide(db: Session, m: Merchant, approve: bool, note: str = "") -> None:
    """Human decision (maker-checker: Wekil prepared, the analyst decides)."""
    m.status, m.decided_at = ("approved" if approve else "rejected"), now()
    if approve:
        months = risk.REVIEW_MONTHS.get(m.risk_tier or "medium", 12)
        m.next_review = date.today() + timedelta(days=30 * months)
        google.event(f"Periodic KYB review: {m.name}", m.next_review, f"{m.risk_tier} risk, every {months} months")
    body = gemini_outcome(m, approve, note)
    google.send(m.email, f"{m.name}: your merchant application was {m.status}", body)
    log(db, "decided", m.id, actor="analyst", outcome=m.status, note=note,
        next_review=m.next_review.isoformat() if m.next_review else None)


def gemini_outcome(m: Merchant, approve: bool, note: str) -> str:
    try:
        return gemini.write(f"Write a brief plain-text email from Wekil Compliance telling {m.name} their merchant "
                            f"application was {'approved' if approve else 'not approved'}. "
                            f"Analyst note to reflect (if any): {note!r}. No markdown, sign off 'Wekil Compliance'.")
    except RuntimeError:
        return f"Hello {m.name},\n\nYour merchant application was {m.status}.\n\nWekil Compliance"


def pending_merchants(db: Session) -> list[Merchant]:
    return list(db.scalars(select(Merchant).where(Merchant.status.in_(["submitted", "reviewing"]))))

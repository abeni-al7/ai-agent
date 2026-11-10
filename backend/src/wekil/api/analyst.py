"""Analyst console API (bearer-token auth)."""

import io
from datetime import date, timedelta
from functools import lru_cache

import jwt
import pypdfium2 as pdfium
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Response
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .. import commands
from ..config import settings
from ..db import Case, Document, Event, Hit, InfoRequest, Merchant, get_db, log, now
from ..tools import risk
from ..workflow import decide, request_info, review

router = APIRouter(prefix="/api")


class Login(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: Login):
    s = settings()
    if body.email.lower() != s.analyst_email.lower() or body.password != s.analyst_password:
        raise HTTPException(401, "Wrong email or password")
    token = jwt.encode({"sub": s.analyst_email, "exp": now() + timedelta(hours=12)}, s.app_secret, "HS256")
    return {"token": token, "email": s.analyst_email}


def analyst(authorization: str = Header("")) -> str:
    try:
        return jwt.decode(authorization.removeprefix("Bearer "), settings().app_secret, ["HS256"])["sub"]
    except jwt.PyJWTError as e:
        raise HTTPException(401, "Sign in again") from e


secured = APIRouter(prefix="/api", dependencies=[Depends(analyst)])


def card(m: Merchant) -> dict:
    return {"id": m.id, "name": m.name, "legal_form": m.legal_form, "category": m.category, "country": m.country,
            "status": m.status, "risk_tier": m.risk_tier, "risk_score": m.risk_score, "created_at": m.created_at,
            "next_review": m.next_review, "blockers": sum(i["severity"] == "blocker" for i in m.issues),
            "open_hits": sum(h.verdict == "likely_match" and not h.decision for h in m.hits)}


@secured.get("/merchants")
def merchants(status: str = "", db: Session = Depends(get_db)):
    q = select(Merchant).order_by(Merchant.created_at)
    if status:
        q = q.where(Merchant.status.in_(status.split(",")))
    return [card(m) for m in db.scalars(q)]


@secured.get("/merchants/{mid}")
def merchant(mid: int, db: Session = Depends(get_db)):
    m = db.get(Merchant, mid) or _404()
    events = db.scalars(select(Event).where(Event.merchant_id == mid).order_by(Event.at))
    return card(m) | {
        "registration_no": m.registration_no, "tin": m.tin, "email": m.email, "phone": m.phone, "address": m.address,
        "monthly_volume_etb": m.monthly_volume_etb, "owners": m.owners, "issues": m.issues,
        "registry": m.registry_check,
        "risk_factors": m.risk_factors, "memo": m.memo, "decided_at": m.decided_at,
        "documents": [{"id": d.id, "doc_type": d.doc_type, "filename": d.filename, "mime": d.mime, "status": d.status,
                       "fields": d.fields, "expires_on": d.expires_on, "uploaded_at": d.uploaded_at}
                      for d in m.documents],
        "hits": [{"id": h.id, "subject": h.subject, "score": h.score, "verdict": h.verdict, "reasons": h.reasons,
                  "decision": h.decision, "entry": {"id": h.entry.id, "source": h.entry.source, "name": h.entry.name,
                                                    "kind": h.entry.kind, "details": h.entry.details,
                                                    "aliases": h.entry.aliases[:5]}} for h in m.hits],
        "requests": [{"id": r.id, "items": r.items, "due_on": r.due_on, "status": r.status, "reminders": r.reminders,
                      "created_at": r.created_at} for r in m.requests],
        "cases": [{"id": c.id, "kind": c.kind, "detail": c.detail, "due_on": c.due_on, "status": c.status}
                  for c in m.cases],
        "events": [{"actor": e.actor, "action": e.action, "detail": e.detail, "at": e.at} for e in events]}


@secured.get("/documents/{did}/preview")
def document_preview(did: int, db: Session = Depends(get_db)):
    d = db.get(Document, did) or _404()
    return Response(preview(d.id, d.mime, d.data), media_type="image/webp",
                    headers={"Cache-Control": "private, max-age=86400"})


@lru_cache(maxsize=256)
def preview(did: int, mime: str, data: bytes) -> bytes:
    """First page as a small WebP, so the analyst sees the document beside its fields on any browser."""
    if mime == "application/pdf":
        img = pdfium.PdfDocument(data)[0].render(scale=1.4).to_pil()
    else:
        img = Image.open(io.BytesIO(data))
    img.thumbnail((900, 1270))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "WEBP", quality=82)
    return buf.getvalue()


@secured.get("/documents/{did}/file")
def document_file(did: int, db: Session = Depends(get_db)):
    d = db.get(Document, did) or _404()
    return Response(d.data, media_type=d.mime, headers={"Cache-Control": "private, max-age=3600"})


class Decision(BaseModel):
    approve: bool
    note: str = ""


@secured.post("/merchants/{mid}/decision")
def decision(mid: int, body: Decision, db: Session = Depends(get_db)):
    m = db.get(Merchant, mid) or _404()
    if m.status != "ready":
        raise HTTPException(409, "Only applications ready for decision can be decided")
    if body.approve and any(h.verdict == "likely_match" and not h.decision for h in m.hits):
        raise HTTPException(409, "Confirm or dismiss the possible sanctions match first")
    decide(db, m, body.approve, body.note)
    db.commit()
    return card(m)


class HitDecision(BaseModel):
    decision: str  # confirmed | dismissed
    note: str = ""


@secured.post("/hits/{hid}")
def hit_decision(hid: int, body: HitDecision, db: Session = Depends(get_db)):
    h = db.get(Hit, hid) or _404()
    if body.decision not in ("confirmed", "dismissed"):
        raise HTTPException(400, "decision must be confirmed or dismissed")
    h.decision = body.decision
    m = h.merchant
    m.risk_score, m.risk_tier, m.risk_factors = risk.score(m, m.hits, m.registry_check, m.issues)
    log(db, f"hit_{body.decision}", m.id, actor="analyst", subject=h.subject, entry=h.entry.name, note=body.note)
    for c in m.cases:
        if c.kind == "rescreen_hit" and c.status == "open" and h.entry.name in c.detail:
            c.status = "closed"
    db.commit()
    return {"risk_tier": m.risk_tier, "risk_score": m.risk_score}


@secured.post("/merchants/{mid}/review")
def rerun(mid: int, bg: BackgroundTasks, db: Session = Depends(get_db)):
    m = db.get(Merchant, mid) or _404()
    log(db, "review_requested", m.id, actor="analyst")
    db.commit()
    bg.add_task(review, mid)
    return {"ok": True}


class Ask(BaseModel):
    items: list[str]


@secured.post("/merchants/{mid}/request")
def ask(mid: int, body: Ask, db: Session = Depends(get_db)):
    m = db.get(Merchant, mid) or _404()
    request_info(db, m, [{"doc_type": None, "text": t} for t in body.items if t.strip()])
    db.commit()
    return card(m)


@secured.post("/cases/{cid}/close")
def close_case(cid: int, db: Session = Depends(get_db)):
    c = db.get(Case, cid) or _404()
    c.status = "closed"
    log(db, "case_closed", c.merchant_id, actor="analyst", kind=c.kind)
    db.commit()
    return {"ok": True}


@secured.get("/today")
def today(db: Session = Depends(get_db)):
    t = date.today()
    ms = list(db.scalars(select(Merchant)))
    overdue = db.scalars(select(InfoRequest).where(InfoRequest.status.in_(["open", "escalated"]),
                                                   InfoRequest.due_on < t))
    cases = db.scalars(select(Case).where(Case.status == "open").order_by(Case.due_on))
    feed = db.scalars(select(Event).order_by(desc(Event.at)).limit(40))
    names = {m.id: m.name for m in ms}
    return {
        "ready": [card(m) for m in ms if m.status == "ready"],
        "attention": [card(m) for m in ms if m.status == "needs_attention"],
        "in_progress": [card(m) for m in ms if m.status in ("submitted", "reviewing")],
        "awaiting": [card(m) for m in ms if m.status == "awaiting_merchant"],
        "overdue": [{"merchant_id": r.merchant_id, "merchant": r.merchant.name, "due_on": r.due_on,
                     "reminders": r.reminders, "status": r.status} for r in overdue],
        "cases": [{"id": c.id, "merchant_id": c.merchant_id, "merchant": c.merchant.name, "kind": c.kind,
                   "detail": c.detail, "due_on": c.due_on} for c in cases],
        "feed": [{"merchant_id": e.merchant_id, "merchant": names.get(e.merchant_id), "actor": e.actor,
                  "action": e.action, "detail": e.detail, "at": e.at} for e in feed],
        "counts": {s: sum(m.status == s for m in ms) for s in
                   ("awaiting_merchant", "ready", "approved", "rejected", "reviewing")},
    }


class Command(BaseModel):
    text: str


class Confirm(BaseModel):
    proposals: list[dict]


@secured.post("/commands")
def command(body: Command, db: Session = Depends(get_db)):
    result = commands.run(db, body.text)
    log(db, "command", actor="analyst", text=body.text[:300], tools=[s["tool"] for s in result["steps"]])
    db.commit()
    return result


@secured.post("/commands/confirm")
def command_confirm(body: Confirm, db: Session = Depends(get_db)):
    return {"results": commands.confirm(db, body.proposals)}


def _404():
    raise HTTPException(404, "Not found")

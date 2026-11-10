"""Public merchant portal API: apply, and answer an information request through a signed link."""

import json

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile
from itsdangerous import BadSignature, SignatureExpired
from sqlalchemy.orm import Session

from ..db import Document, InfoRequest, Merchant, get_db, log
from ..tools.documents import DOC_TYPES, REQUIRED
from ..workflow import LINK_AGE, review, signer

router = APIRouter(prefix="/api")
MAX_BYTES = 8 * 1024 * 1024
CATEGORIES = ["retail", "restaurant", "coffee_export", "pharmacy", "electronics", "travel_agency", "education",
              "logistics", "money_transfer", "charity", "precious_metals", "crypto", "gambling"]


@router.get("/meta")
def meta():
    return {"doc_types": DOC_TYPES, "required": REQUIRED, "categories": CATEGORIES}


async def _docs(files: list[UploadFile], types: list[str], merchant_id: int) -> list[Document]:
    if len(files) != len(types) or any(t not in DOC_TYPES for t in types):
        raise HTTPException(400, "Each file needs a valid document type")
    docs = []
    for f, t in zip(files, types, strict=True):
        data = await f.read()
        if len(data) > MAX_BYTES or not (f.content_type or "").startswith(("image/", "application/pdf")):
            raise HTTPException(400, f"{f.filename}: PDF or image up to 8 MB")
        docs.append(Document(merchant_id=merchant_id, doc_type=t, filename=f.filename or t, mime=f.content_type,
                             data=data))
    return docs


@router.post("/apply")
async def apply(bg: BackgroundTasks, application: str = Form(...), doc_types: str = Form("[]"),
                files: list[UploadFile] = (), db: Session = Depends(get_db)):
    a = json.loads(application)
    if a.get("legal_form") not in REQUIRED or not a.get("name") or not a.get("email"):
        raise HTTPException(400, "Name, email and a valid legal form are required")
    m = Merchant(**{k: a.get(k) for k in ("name", "legal_form", "category", "registration_no", "tin", "email",
                                         "phone", "address") if a.get(k) is not None},
                 country=(a.get("country") or "ET").upper()[:2],
                 monthly_volume_etb=int(a.get("monthly_volume_etb") or 0),
                 owners=[o for o in a.get("owners", []) if o.get("name")])
    db.add(m)
    db.flush()
    db.add_all(await _docs(list(files), json.loads(doc_types), m.id))
    log(db, "application_received", m.id, actor="merchant", documents=len(files))
    db.commit()
    bg.add_task(review, m.id)
    return {"id": m.id, "status": m.status}


def _request(db: Session, token: str) -> InfoRequest:
    try:
        req_id = signer().loads(token, max_age=LINK_AGE)
    except SignatureExpired as e:
        raise HTTPException(410, "This link has expired. Reply to our email and we will send a new one.") from e
    except BadSignature as e:
        raise HTTPException(404, "Invalid link") from e
    req = db.get(InfoRequest, req_id)
    if not req:
        raise HTTPException(404, "Invalid link")
    return req


@router.get("/upload/{token}")
def request_view(token: str, db: Session = Depends(get_db)):
    req = _request(db, token)
    return {"merchant": req.merchant.name, "items": req.items, "due_on": req.due_on, "status": req.status,
            "doc_types": DOC_TYPES}


@router.post("/upload/{token}")
async def request_answer(token: str, bg: BackgroundTasks, doc_types: str = Form("[]"),
                         files: list[UploadFile] = (), note: str = Form(""), db: Session = Depends(get_db)):
    req = _request(db, token)
    if req.status != "open":
        raise HTTPException(409, "This request was already answered")
    m: Merchant = req.merchant
    new = await _docs(list(files), json.loads(doc_types), m.id)
    for d in m.documents:
        if d.doc_type in {n.doc_type for n in new} and d.status != "superseded":
            d.status = "superseded"
    db.add_all(new)
    req.status = "answered"
    log(db, "merchant_uploaded", m.id, actor="merchant", documents=[d.doc_type for d in new], note=note[:500])
    db.commit()
    if m.status != "approved":  # renewals for live merchants are re-read without reopening onboarding
        bg.add_task(review, m.id)
    else:
        bg.add_task(_refresh_documents, m.id)
    return {"ok": True}


def _refresh_documents(merchant_id: int) -> None:
    from ..db import SessionLocal
    from ..tools import documents
    from ..workflow import current_docs

    with SessionLocal() as db:
        m = db.get(Merchant, merchant_id)
        for d in current_docs(m).values():
            if d.status == "pending":
                f = documents.extract(d.data, d.mime, d.doc_type)
                d.fields, d.expires_on, d.status = f.model_dump(mode="json"), f.expiry_date, "extracted"
                log(db, "document_read", m.id, doc_type=d.doc_type, expires_on=str(f.expiry_date))
        for c in m.cases:
            if c.kind == "renewal" and c.status == "open":
                c.status = "closed"
                log(db, "case_closed", m.id, kind="renewal", reason="renewed document received")
        db.commit()

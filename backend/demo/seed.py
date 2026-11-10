"""Demo state. Usage (from backend/):
  uv run python demo/seed.py reset        wipe merchants/events (keeps sanctions lists), seed the existing book,
                                          and run real reviews for Tana (-> info request) and Blue Horizon (-> ready)
  uv run python demo/seed.py list-update  add today's synthetic sanctions-list entry used by the morning routine
"""

import pathlib
import sys
from datetime import date, timedelta

from sqlalchemy import delete

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from merchants import MERCHANTS  # noqa: E402

from wekil.db import Case, Document, Event, Hit, InfoRequest, ListEntry, Merchant, SessionLocal, log, now  # noqa: E402
from wekil.workflow import review  # noqa: E402

DOCS = pathlib.Path(__file__).parent / "documents"
TODAY = date.today()


def merchant(slug: str, **extra) -> Merchant:
    m = MERCHANTS[slug]
    return Merchant(**{k: m[k] for k in ("name", "legal_form", "category", "registration_no", "tin", "email", "phone",
                                         "address", "monthly_volume_etb", "country")},
                    owners=[{k: o[k] for k in ("name", "dob", "nationality", "share")} for o in m["owners"]], **extra)


def files(slug: str, extracted: bool) -> list[Document]:
    m, out = MERCHANTS[slug], []
    for p in sorted((DOCS / slug).iterdir()):
        if "renewed" in p.stem:
            continue
        fields, expires = {}, None
        if extracted:  # existing merchants were read when they were onboarded
            fields = {"document_type": p.stem, "name": m["name"], "tin": m["tin"],
                      "registration_no": m["registration_no"], "concerns": []}
            if p.stem == "business_license":
                expires = date.fromisoformat(m["license_expiry"])
            if p.stem == "owner_id":
                o = m["owners"][0]
                fields |= {"name": o["name"], "dob": o["dob"], "id_number": m["id_number"]}
                expires = date.fromisoformat(m["id_expiry"])
            fields["expiry_date"] = expires.isoformat() if expires else None
        out.append(Document(doc_type=p.stem, filename=p.name, data=p.read_bytes(), fields=fields, expires_on=expires,
                            mime="image/png" if p.suffix == ".png" else "application/pdf",
                            status="extracted" if extracted else "pending"))
    return out


def reset() -> None:
    with SessionLocal() as db:
        for t in (Event, Hit, Case, InfoRequest, Document, Merchant):
            db.execute(delete(t))
        db.execute(delete(ListEntry).where(ListEntry.source == "DEMO"))
        db.commit()

        # Existing book: two approved merchants, one waiting on an overdue request.
        for slug, tier, months_ago in (("lalibela", "low", 11), ("hawassa", "medium", 5)):
            m = merchant(slug, status="approved", risk_tier=tier,
                         created_at=now() - timedelta(days=30 * months_ago + 6),
                         decided_at=now() - timedelta(days=30 * months_ago), risk_score=10 if tier == "low" else 40,
                         risk_factors=["+0 Seeded: approved before the demo"],
                         next_review=TODAY + timedelta(days=30 * (24 if tier == "low" else 12) - 30 * months_ago),
                         registry_check={"source": "Ethiopian business register (simulated)", "status": "match"},
                         memo="**Summary** Approved after full KYB review.")
            m.documents = files(slug, extracted=True)
            db.add(m)
            db.flush()
            log(db, "decided", m.id, actor="analyst", outcome="approved", note="Onboarded before the demo")
        m = merchant("merkato", status="awaiting_merchant", created_at=now() - timedelta(days=9))
        m.documents = files("merkato", extracted=True)
        db.add(m)
        db.flush()
        db.add(InfoRequest(merchant_id=m.id, due_on=TODAY - timedelta(days=2), created_at=now() - timedelta(days=7),
                           items=[{"doc_type": None, "text": "Upload a bank letter confirming the payout account is "
                                                             "in the business owner's name."}]))
        log(db, "info_requested", m.id, items=["Bank letter for the payout account"],
            due=(TODAY - timedelta(days=2)).isoformat(), emailed=False)
        db.commit()

        # Fresh applications reviewed for real by Wekil (Gemini, lists, registry, Gmail, Calendar).
        ids = []
        for slug in ("tana", "blue"):
            m = merchant(slug)
            docs = files(slug, extracted=False)
            if slug == "tana":
                docs = [d for d in docs if d.doc_type != "tin_certificate"]  # forgot the TIN certificate
            m.documents = docs
            db.add(m)
            db.flush()
            log(db, "application_received", m.id, actor="merchant", documents=len(docs))
            ids.append(m.id)
        db.commit()
    for mid in ids:
        review(mid)
        print("reviewed", mid)


def list_update() -> None:
    with SessionLocal() as db:
        db.merge(ListEntry(id="DEMO:2026-001", source="DEMO", name="TADESSE, Kebede Alemu", kind="individual",
                           aliases=["Kebede Alemu"], first_seen=TODAY,
                           details={"programs": "Synthetic list update for the demo (not a real designation)",
                                    "dob": "12 Mar 1979", "nationality": "Ethiopia",
                                    "address": "Hawassa, Sidama, Ethiopia"}))
        db.commit()
    print("added DEMO:2026-001")


if __name__ == "__main__":
    {"reset": reset, "list-update": list_update}[sys.argv[1]]()

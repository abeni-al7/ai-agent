"""Tables and session. One file: the data model is small and read together."""

from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, LargeBinary, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from .config import settings


def now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map = {dict: JSON, list: JSON}


class Merchant(Base):
    __tablename__ = "merchants"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    legal_form: Mapped[str] = mapped_column(String(30))  # sole_trader | plc | share_company
    category: Mapped[str] = mapped_column(String(60))
    country: Mapped[str] = mapped_column(String(2), default="ET")
    registration_no: Mapped[str] = mapped_column(String(60), default="")
    tin: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(40), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    monthly_volume_etb: Mapped[int] = mapped_column(default=0)
    owners: Mapped[list] = mapped_column(default=list)  # [{name, dob, nationality, share}]
    status: Mapped[str] = mapped_column(String(30), default="submitted")
    risk_tier: Mapped[str | None] = mapped_column(String(20))
    risk_score: Mapped[int | None]
    risk_factors: Mapped[list] = mapped_column(default=list)
    issues: Mapped[list] = mapped_column(default=list)  # consistency findings
    registry_check: Mapped[dict] = mapped_column("registry", default=dict)
    memo: Mapped[str | None] = mapped_column(Text)
    next_review: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    documents: Mapped[list["Document"]] = relationship(back_populates="merchant", order_by="Document.id")
    hits: Mapped[list["Hit"]] = relationship(back_populates="merchant", order_by="Hit.id")
    requests: Mapped[list["InfoRequest"]] = relationship(back_populates="merchant", order_by="InfoRequest.id")
    cases: Mapped[list["Case"]] = relationship(back_populates="merchant", order_by="Case.id")


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"))
    doc_type: Mapped[str] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(200))
    mime: Mapped[str] = mapped_column(String(80))
    data: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    fields: Mapped[dict] = mapped_column(default=dict)
    expires_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | extracted | failed | superseded
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    merchant: Mapped[Merchant] = relationship(back_populates="documents")


class Hit(Base):
    __tablename__ = "hits"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"))
    subject: Mapped[str] = mapped_column(String(200))
    entry_id: Mapped[str] = mapped_column(ForeignKey("list_entries.id"))
    score: Mapped[int]
    verdict: Mapped[str] = mapped_column(String(20))  # likely_match | likely_not
    reasons: Mapped[list] = mapped_column(default=list)
    decision: Mapped[str | None] = mapped_column(String(20))  # confirmed | dismissed (analyst)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    merchant: Mapped[Merchant] = relationship(back_populates="hits")
    entry: Mapped["ListEntry"] = relationship()


class InfoRequest(Base):
    __tablename__ = "requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"))
    items: Mapped[list] = mapped_column(default=list)  # [{doc_type?, text}]
    due_on: Mapped[date] = mapped_column(Date)
    thread_id: Mapped[str | None] = mapped_column(String(60))
    reminders: Mapped[int] = mapped_column(default=0)
    reply_ids: Mapped[list] = mapped_column(default=list)  # Gmail message ids already read
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | answered | escalated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    merchant: Mapped[Merchant] = relationship(back_populates="requests")


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"))
    kind: Mapped[str] = mapped_column(String(30))  # renewal | periodic_review | rescreen_hit
    detail: Mapped[str] = mapped_column(Text)
    due_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    merchant: Mapped[Merchant] = relationship(back_populates="cases")


class Event(Base):
    """Append-only audit trail: no code path updates or deletes rows."""

    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[int | None] = mapped_column(ForeignKey("merchants.id"))
    actor: Mapped[str] = mapped_column(String(20))  # wekil | analyst | merchant | routine
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[dict] = mapped_column(default=dict)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ListEntry(Base):
    __tablename__ = "list_entries"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)  # "<source>:<uid>"
    source: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(300))
    aliases: Mapped[list] = mapped_column(default=list)
    kind: Mapped[str] = mapped_column(String(20))  # individual | entity
    details: Mapped[dict] = mapped_column(default=dict)  # dob, nationality, programs, address
    first_seen: Mapped[date] = mapped_column(Date)


engine = create_engine(settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


@event.listens_for(Session, "before_flush")
def _protect_audit_log(session, *_):
    if any(isinstance(o, Event) for o in [*session.dirty, *session.deleted]):
        raise PermissionError("events are append-only")


def get_db():
    with SessionLocal() as db:
        yield db


def log(db: Session, action: str, merchant_id: int | None = None, actor: str = "wekil", **detail) -> None:
    db.add(Event(merchant_id=merchant_id, actor=actor, action=action, detail=detail))

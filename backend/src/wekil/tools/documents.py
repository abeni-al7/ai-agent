"""S1 intake + S2 extraction and consistency."""

from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel
from rapidfuzz import fuzz

from . import gemini

DOC_TYPES = {
    "business_license": "Business (trade) licence",
    "tin_certificate": "TIN registration certificate",
    "memorandum": "Memorandum of association",
    "owner_id": "Owner ID (Kebele ID, Fayda or passport)",
}
REQUIRED = {
    "sole_trader": ["business_license", "tin_certificate", "owner_id"],
    "plc": ["business_license", "tin_certificate", "memorandum", "owner_id"],
    "share_company": ["business_license", "tin_certificate", "memorandum", "owner_id"],
}


class Shareholder(BaseModel):
    name: str
    nationality: str | None = None
    share_percent: float | None = None


class Extracted(BaseModel):
    document_type: Literal["business_license", "tin_certificate", "memorandum", "owner_id", "other"]
    name: str | None = None  # business name, or the person's full name on an ID
    tin: str | None = None
    registration_no: str | None = None
    license_no: str | None = None
    activity: str | None = None
    address: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    dob: date | None = None
    nationality: str | None = None
    id_number: str | None = None
    shareholders: list[Shareholder] = []
    concerns: list[str] = []  # tampering signs, internal contradictions, illegible parts


def extract(data: bytes, mime: str, declared: str) -> Extracted:
    return gemini.ask(
        f"The merchant uploaded this as a '{DOC_TYPES.get(declared, declared)}'. Identify what it really is and "
        "extract the fields that appear on it. Dates as ISO YYYY-MM-DD (convert Ethiopian-calendar dates to "
        "Gregorian if both are shown use the Gregorian one). Leave fields that are not on the document empty. "
        "List concrete concerns only (e.g. edited text, mismatched fonts, missing seal, illegible). This environment "
        "uses synthetic documents watermarked SPECIMEN: ignore that watermark, do not list it as a concern.",
        Extracted, files=[(data, mime)])


def same(a: str | None, b: str | None, threshold: int = 85) -> bool:
    return bool(a and b) and fuzz.token_set_ratio(norm(a), norm(b)) >= threshold


def norm(name: str) -> str:
    drop = {"plc", "p.l.c", "p.l.c.", "sc", "s.c", "s.c.", "ltd", "llc", "share", "company", "co", "trading"}
    return " ".join(w for w in name.lower().replace(",", " ").split() if w not in drop)


def check(merchant, docs: dict[str, dict], today: date | None = None) -> tuple[list[str], list[dict]]:
    """Return (missing doc types, issues). Issues: {severity: blocker|warning, text, doc_type, ask: bool}."""
    today = today or date.today()
    missing = [t for t in REQUIRED[merchant.legal_form] if t not in docs]
    issues: list[dict] = []

    def add(severity, text, doc_type=None, ask=False):
        issues.append({"severity": severity, "text": text, "doc_type": doc_type, "ask": ask})

    for t, f in docs.items():
        if f.get("document_type") not in (t, None):
            add("blocker", f"The file uploaded as {DOC_TYPES[t]} looks like a '{f['document_type']}'.", t, True)
        for c in f.get("concerns", []):
            add("warning", f"{DOC_TYPES[t]}: {c}", t)
        if t in ("business_license", "owner_id") and (exp := f.get("expiry_date")):
            exp = date.fromisoformat(str(exp))
            if exp < today:
                add("blocker", f"{DOC_TYPES[t]} expired on {exp:%d %b %Y}.", t, True)
            elif exp < today + timedelta(days=30):
                add("warning", f"{DOC_TYPES[t]} expires on {exp:%d %b %Y}, within 30 days.", t, True)

    for t in ("business_license", "tin_certificate", "memorandum"):
        if (n := docs.get(t, {}).get("name")) and not same(n, merchant.name):
            add("blocker", f"Business name on the {DOC_TYPES[t]} ('{n}') differs from the application "
                           f"('{merchant.name}').", t, True)
    for t in ("business_license", "tin_certificate"):
        if (tin := docs.get(t, {}).get("tin")) and merchant.tin and digits(tin) != digits(merchant.tin):
            add("blocker", f"TIN on the {DOC_TYPES[t]} ({tin}) differs from the application ({merchant.tin}).", t, True)

    owners = [o["name"] for o in merchant.owners]
    for s in docs.get("memorandum", {}).get("shareholders", []):
        if not any(same(s["name"], o) for o in owners):
            pct = f" ({s['share_percent']:g}%)" if s.get("share_percent") else ""
            add("blocker", f"The memorandum lists {s['name']}{pct} as a shareholder, but the application does "
                           "not declare them as an owner.", "memorandum", True)
    if (idn := docs.get("owner_id", {}).get("name")) and owners and not any(same(idn, o) for o in owners):
        add("blocker", f"The ID belongs to '{idn}', who is not a declared owner.", "owner_id", True)
    return missing, issues


def digits(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())

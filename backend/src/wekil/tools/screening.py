"""S5 sanctions screening: official OFAC + UN lists, fuzzy candidates in code, triage by Gemini."""

import csv
import io
import re
from datetime import date
from typing import Literal

import httpx
from lxml import etree
from pydantic import BaseModel
from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import ListEntry
from . import gemini
from .documents import norm

OFAC = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/{}.CSV"
UN = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
THRESHOLD = 86


def _get(url: str) -> bytes:
    r = httpx.get(url, follow_redirects=True, timeout=120)
    r.raise_for_status()
    return r.content


def _ofac() -> list[dict]:
    aliases: dict[str, list[str]] = {}
    for row in csv.reader(io.StringIO(_get(OFAC.format("ALT")).decode("latin-1"))):
        if len(row) > 3:
            aliases.setdefault(row[0], []).append(row[3].strip())
    out = []
    for row in csv.reader(io.StringIO(_get(OFAC.format("SDN")).decode("latin-1"))):
        if len(row) < 12 or row[2].strip() in ("vessel", "aircraft"):
            continue
        remarks = row[11]
        out.append({"id": f"OFAC:{row[0]}", "source": "OFAC", "name": row[1].strip(),
                    "aliases": aliases.get(row[0], []),
                    "kind": "individual" if row[2].strip() == "individual" else "entity",
                    "details": {"programs": row[3].strip(), "dob": _grab(r"DOB ([^;]+)", remarks),
                                "nationality": _grab(r"nationality ([^;]+)", remarks),
                                "address": _grab(r"(?:Address|located in) ([^;]+)", remarks)}})
    return out


def _un() -> list[dict]:
    root = etree.fromstring(_get(UN))
    out = []
    for kind, tag in (("individual", "INDIVIDUAL"), ("entity", "ENTITY")):
        for el in root.iter(tag):
            def t(p: str, el=el) -> str:
                return " ".join(x.strip() for x in el.xpath(p) if x and x.strip())

            name = " ".join(filter(None, (t(f"{n}/text()") for n in
                                          ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME"))))
            out.append({"id": f"UN:{t('REFERENCE_NUMBER/text()')}", "source": "UN", "name": name,
                        "aliases": [a for a in el.xpath(f"{tag}_ALIAS/ALIAS_NAME/text()") if a.strip()],
                        "kind": kind,
                        "details": {"programs": t("UN_LIST_TYPE/text()"),
                                    "dob": t(f"{tag}_DATE_OF_BIRTH//text()"),
                                    "nationality": t("NATIONALITY/VALUE/text()"),
                                    "address": t(f"{tag}_ADDRESS//text()")}})
    return out


def _grab(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text or "")
    return m.group(1).strip().rstrip(".") if m else None


def refresh(db: Session, today: date | None = None) -> list[ListEntry]:
    """Download both lists and insert entries not seen before. Returns today's new entries (the delta)."""
    today = today or date.today()
    known = set(db.scalars(select(ListEntry.id)))
    new = [ListEntry(**e, first_seen=today) for e in _ofac() + _un() if e["id"] not in known]
    db.add_all(new)
    db.commit()
    return new


def tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[^\w]+", norm(name)) if len(t) > 2]


def name_score(subject: list[str], listed: list[str]) -> float:
    """Every token of the listed name must closely match some token of the subject. Extra subject tokens
    (Ethiopian grandfather names) cost nothing; transliteration variants (Germay/Ghermay) still match."""
    if not listed or not subject:
        return 0
    return sum(process.extractOne(t, subject, scorer=fuzz.ratio)[1] for t in listed) / len(listed)


def candidates(name: str, entries: list[ListEntry], kind: str | None = None) -> list[tuple[ListEntry, int]]:
    """Deterministic fuzzy candidates over names and aliases; best score per entry, top 3."""
    subject = tokens(name)
    best: dict[str, tuple[ListEntry, int]] = {}
    for e in entries:
        if kind and e.kind != kind:
            continue
        for n in (e.name, *e.aliases):
            listed = tokens(n or "")
            if e.kind == "individual" and len(listed) < 2:  # a single given name is not a candidate
                continue
            score = name_score(subject, listed)
            if score >= THRESHOLD and score > best.get(e.id, (e, 0))[1]:
                best[e.id] = (e, int(score))
    return sorted(best.values(), key=lambda x: -x[1])[:3]


class Triage(BaseModel):
    verdict: Literal["likely_match", "likely_not"]
    reasons: list[str]


def triage(subject: dict, entry: ListEntry, score: int) -> Triage:
    return gemini.ask(
        "Decide if our subject is the same party as the sanctions-list entry. Compare every available "
        "identifier (full name and order, date of birth, nationality, address/country, entity vs person, "
        "business activity). A similar name alone is not a match. Give 2-4 short, specific reasons citing the "
        f"evidence.\n\nSUBJECT: {subject}\n\nLIST ENTRY ({entry.source} {entry.id}): name={entry.name}; "
        f"aliases={entry.aliases[:8]}; kind={entry.kind}; details={entry.details}\nName similarity: {score}/100",
        Triage)


def screen(db: Session, subjects: list[dict], entries: list[ListEntry] | None = None) -> list[dict]:
    """subjects: [{name, kind: individual|entity, dob?, nationality?, country?, activity?}]"""
    entries = entries if entries is not None else list(db.scalars(select(ListEntry)))
    results = []
    for s in subjects:
        for entry, score in candidates(s["name"], entries, s.get("kind")):
            t = triage(s, entry, score)
            results.append({"subject": s["name"], "entry": entry, "score": score, **t.model_dump()})
    return results

"""Deterministic parts: consistency checks, risk rules, name matching. (Gemini calls are not unit-tested.)"""

from datetime import date
from types import SimpleNamespace

from wekil.tools import documents, risk, screening


def merchant(**kw):
    base = dict(name="Tana Spice Traders PLC", legal_form="plc", tin="0039927154", category="retail", country="ET",
                monthly_volume_etb=100_000, owners=[{"name": "Meron Tesfaye Alemu", "nationality": "ET"}])
    return SimpleNamespace(**(base | kw))


def test_missing_documents_follow_legal_form():
    missing, _ = documents.check(merchant(), {"business_license": {}})
    assert missing == ["tin_certificate", "memorandum", "owner_id"]
    missing, _ = documents.check(merchant(legal_form="sole_trader"), {})
    assert "memorandum" not in missing


def test_expired_licence_and_undeclared_shareholder_are_blockers():
    docs = {"business_license": {"document_type": "business_license", "name": "Tana Spice Traders P.L.C.",
                                 "tin": "0039 927 154", "expiry_date": "2026-01-01"},
            "memorandum": {"document_type": "memorandum", "name": "Tana Spice Traders",
                           "shareholders": [{"name": "Meron Tesfaye"}, {"name": "Dawit Haile", "share_percent": 30}]}}
    _, issues = documents.check(merchant(), docs, today=date(2026, 11, 10))
    texts = " | ".join(i["text"] for i in issues if i["severity"] == "blocker")
    assert "expired" in texts and "Dawit Haile (30%)" in texts
    assert "differs" not in texts  # P.L.C./spacing variants are the same name and TIN


def test_licence_expiring_soon_is_a_warning():
    docs = {"business_license": {"document_type": "business_license", "expiry_date": "2026-11-25"}}
    _, issues = documents.check(merchant(), docs, today=date(2026, 11, 10))
    assert [i["severity"] for i in issues] == ["warning"]


def test_risk_tiers():
    m = merchant()
    assert risk.score(m, [], {"status": "match"}, [])[1] == "low"
    assert risk.score(merchant(category="gambling"), [], {}, [])[1] == "prohibited"
    hit = SimpleNamespace(verdict="likely_match", decision=None)
    assert risk.score(m, [hit], {"status": "match"}, [])[1] in ("medium", "high")
    hit.decision = "confirmed"
    assert risk.score(m, [hit], {}, [])[1] == "prohibited"


def test_name_matching_handles_grandfather_names_and_transliteration():
    subject = screening.tokens("Ermias Germay Tekle")
    assert screening.name_score(subject, screening.tokens("GHERMAY, Ermias")) >= screening.THRESHOLD
    assert screening.name_score(subject, screening.tokens("HAILE, Dawit")) < screening.THRESHOLD

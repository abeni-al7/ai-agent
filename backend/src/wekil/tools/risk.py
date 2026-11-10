"""S6 risk tier (deterministic rules) + S9 decision memo (Gemini writes, never decides)."""

from . import gemini

HIGH_RISK_CATEGORIES = {"money_transfer", "crypto", "gambling", "precious_metals", "arms", "charity"}
PROHIBITED_CATEGORIES = {"arms", "gambling"}  # gambling is unlicensed in Ethiopia since Dec 2025
HIGH_RISK_COUNTRIES = {"IR", "KP", "MM", "SY", "AF", "RU", "SS", "YE"}
TIERS = [(70, "high"), (35, "medium"), (0, "low")]
REVIEW_MONTHS = {"low": 24, "medium": 12, "high": 6}


def score(merchant, hits: list, registry: dict, issues: list) -> tuple[int, str, list[str]]:
    factors: list[tuple[int, str]] = []
    if merchant.category in PROHIBITED_CATEGORIES:
        return 100, "prohibited", [f"Category '{merchant.category}' is not permitted for onboarding."]
    if merchant.category in HIGH_RISK_CATEGORIES:
        factors.append((30, f"High-risk category: {merchant.category}"))
    countries = {merchant.country} | {o.get("nationality", "") for o in merchant.owners}
    if bad := countries & HIGH_RISK_COUNTRIES:
        factors.append((35, f"Links to high-risk jurisdiction: {', '.join(sorted(bad))}"))
    if any(h.verdict == "likely_match" and h.decision != "dismissed" for h in hits):
        factors.append((60, "Possible sanctions match awaiting analyst confirmation"))
    elif hits:
        factors.append((5, f"{len(hits)} name-similarity hit(s) triaged as not the same party"))
    if any(h.decision == "confirmed" for h in hits):
        return 100, "prohibited", ["Analyst confirmed a sanctions match."]
    if registry.get("status") in ("not_found", "name_mismatch"):
        factors.append((20, f"Registry check: {registry['status'].replace('_', ' ')}"))
    if merchant.legal_form != "sole_trader" and len(merchant.owners) > 3:
        factors.append((10, "More than three owners: ownership is harder to verify"))
    if merchant.monthly_volume_etb > 5_000_000:
        factors.append((15, "Expected volume above ETB 5M per month"))
    if n := sum(i["severity"] == "warning" for i in issues):
        factors.append((5 * min(n, 3), f"{n} document warning(s)"))
    total = min(sum(p for p, _ in factors), 99)
    tier = next(t for floor, t in TIERS if total >= floor)
    return total, tier, [f"+{p} {why}" for p, why in factors] or ["No risk factors found"]


def memo(merchant, docs: dict, registry: dict, hits: list, issues: list) -> str:
    return gemini.write(
        "Write the KYB decision memo (markdown, max 220 words) for the analyst who will approve or reject. "
        "Sections: **Summary** (one sentence with recommendation: approve / approve with conditions / reject), "
        "**Verified**, **Open points**, **Risk** (tier and the main factors), **Monitoring** (review frequency). "
        "Recommend only; the analyst decides. Use only the facts below.\n\n"
        f"Merchant: {merchant.name} ({merchant.legal_form}, {merchant.category}, {merchant.country}); "
        f"declared owners: {merchant.owners}; expected monthly volume ETB {merchant.monthly_volume_etb:,}.\n"
        f"Extracted documents: {docs}\nRegistry: {registry}\n"
        f"Screening: {[(h.subject, h.entry.name, h.verdict, h.reasons) for h in hits]}\n"
        f"Consistency findings: {issues}\nRisk: tier {merchant.risk_tier}, score {merchant.risk_score}, "
        f"factors {merchant.risk_factors}; periodic review every "
        f"{REVIEW_MONTHS.get(merchant.risk_tier, 12)} months.")

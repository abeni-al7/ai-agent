"""S3 registry lookup: GLEIF (global LEI), UK Companies House, and a labelled simulation for Ethiopia
(the Ethiopian business register has no public API)."""

import httpx

from ..config import settings
from .documents import same

# Simulated Ethiopian Ministry of Trade register: registration_no -> registered name, form, status.
ET_REGISTER = {
    "AA/14/7/2/0019482/2015": ("Selam Coffee Roasters", "sole_trader", "active"),
    "AA/12/1/3/0048817/2014": ("Tana Spice Traders PLC", "plc", "active"),
    "AA/09/4/1/0031205/2013": ("Blue Horizon Trading PLC", "plc", "active"),
    "AA/10/2/6/0022931/2016": ("Merkato Mobile Accessories", "sole_trader", "active"),
    "AA/03/5/2/0011845/2012": ("Lalibela Crafts Export PLC", "plc", "active"),
    "AA/05/8/1/0017720/2015": ("Hawassa Fresh Produce PLC", "plc", "active"),
}


def lookup(name: str, country: str, registration_no: str = "") -> dict:
    try:
        if country == "ET":
            return _ethiopia(name, registration_no)
        if country == "GB" and settings().companies_house_key:
            return _companies_house(name)
        return _gleif(name)
    except httpx.HTTPError as e:
        return {"source": "registry", "status": "unavailable", "note": str(e)[:200]}


def _ethiopia(name: str, reg: str) -> dict:
    hit = ET_REGISTER.get(reg.strip())
    base = {"source": "Ethiopian business register (simulated)", "registration_no": reg}
    if not hit:
        return base | {"status": "not_found", "note": "No record under this registration number."}
    reg_name, form, status = hit
    return base | {"status": "match" if same(reg_name, name) else "name_mismatch", "registered_name": reg_name,
                   "legal_form": form, "registry_status": status}


def _gleif(name: str) -> dict:
    r = httpx.get("https://api.gleif.org/api/v1/lei-records", params={"filter[entity.legalName]": name,
                                                                      "page[size]": 3}, timeout=20)
    r.raise_for_status()
    for rec in r.json().get("data", []):
        e = rec["attributes"]["entity"]
        if same(e["legalName"]["name"], name, 90):
            return {"source": "GLEIF", "status": "match", "lei": rec["attributes"]["lei"],
                    "registered_name": e["legalName"]["name"], "country": e["legalAddress"]["country"],
                    "registry_status": e["status"]}
    return {"source": "GLEIF", "status": "not_found", "note": "No LEI record with a matching legal name."}


def _companies_house(name: str) -> dict:
    auth = (settings().companies_house_key, "")
    base = "https://api.company-information.service.gov.uk"
    r = httpx.get(f"{base}/search/companies", params={"q": name, "items_per_page": 3}, auth=auth, timeout=20)
    r.raise_for_status()
    for item in r.json().get("items", []):
        if same(item["title"], name, 90):
            officers = httpx.get(f"{base}/company/{item['company_number']}/officers", auth=auth, timeout=20)
            names = [o["name"] for o in officers.json().get("items", []) if not o.get("resigned_on")]
            return {"source": "UK Companies House", "status": "match", "company_number": item["company_number"],
                    "registered_name": item["title"], "registry_status": item.get("company_status"),
                    "officers": names[:10]}
    return {"source": "UK Companies House", "status": "not_found", "note": "No company with a matching name."}

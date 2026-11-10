"""Synthetic demo merchants (fictional people and businesses). Shared by the document generator and the seed."""

from datetime import date, timedelta

TODAY = date.today()
INBOX = "abenezeralebachew3+{}@gmail.com"


def d(days: int) -> str:
    return (TODAY + timedelta(days=days)).isoformat()


MERCHANTS = {
    # 1. Clean sole trader, applies live in the demo -> ready for decision.
    "selam": dict(
        name="Selam Coffee Roasters", legal_form="sole_trader", category="retail",
        registration_no="AA/14/7/2/0019482/2015", tin="0045812736", phone="+251 911 402 118",
        address="Bole Sub-city, Woreda 03, Addis Ababa", monthly_volume_etb=850_000,
        owners=[dict(name="Selamawit Bekele Haile", dob="1990-04-18", nationality="ET", share=100)],
        activity="Roasting and retail sale of coffee", license_no="BL/AA/14/0019482", license_issue="2025-07-08",
        license_expiry="2027-07-07", id_number="FAN 4821 7730 1905", id_expiry="2031-04-18"),
    # 2. Expired licence + missing TIN certificate -> information request -> uploads -> re-review.
    "tana": dict(
        name="Tana Spice Traders PLC", legal_form="plc", category="retail",
        registration_no="AA/12/1/3/0048817/2014", tin="0039927154", phone="+251 912 778 230",
        address="Addis Ketema Sub-city, Merkato, Addis Ababa", monthly_volume_etb=1_400_000,
        owners=[dict(name="Meron Tesfaye Alemu", dob="1987-11-02", nationality="ET", share=60),
                dict(name="Yonas Girma Wolde", dob="1984-05-21", nationality="ET", share=40)],
        activity="Wholesale and retail of spices and grains", license_no="BL/AA/12/0048817",
        license_issue="2025-10-16", license_expiry=d(-26), renewed_expiry=d(339),
        id_number="FAN 3307 9152 6648", id_expiry="2030-11-02"),
    # 3. Owner's name resembles a real OFAC entry (GHERMAY, Ermias) -> Gemini triages as likely not the same.
    "blue": dict(
        name="Blue Horizon Trading PLC", legal_form="plc", category="electronics",
        registration_no="AA/09/4/1/0031205/2013", tin="0051203398", phone="+251 913 556 047",
        address="Kirkos Sub-city, Kazanchis, Addis Ababa", monthly_volume_etb=2_300_000,
        owners=[dict(name="Ermias Germay Tekle", dob="1996-02-11", nationality="ET", share=50),
                dict(name="Hanna Mulugeta Asfaw", dob="1993-09-03", nationality="ET", share=50)],
        activity="Import and retail of consumer electronics", license_no="BL/AA/09/0031205",
        license_issue="2026-03-02", license_expiry="2027-03-01", id_number="FAN 6610 2087 4413",
        id_expiry="2032-02-11"),
    # 4-6: already in the book before the demo (seeded), used by the morning routine.
    "lalibela": dict(
        name="Lalibela Crafts Export PLC", legal_form="plc", category="retail",
        registration_no="AA/03/5/2/0011845/2012", tin="0028810457", phone="+251 911 230 965",
        address="Arada Sub-city, Piassa, Addis Ababa", monthly_volume_etb=600_000,
        owners=[dict(name="Tigist Abebe Kassa", dob="1982-01-30", nationality="ET", share=100)],
        activity="Export of handicrafts and textiles", license_no="BL/AA/03/0011845",
        license_issue="2025-12-01", license_expiry=d(19), renewed_expiry=d(384),
        id_number="FAN 2209 5518 0736", id_expiry="2029-01-30"),
    "hawassa": dict(
        name="Hawassa Fresh Produce PLC", legal_form="plc", category="logistics",
        registration_no="AA/05/8/1/0017720/2015", tin="0047731902", phone="+251 916 118 402",
        address="Hawassa City, Tabor Sub-city, Sidama", monthly_volume_etb=1_900_000,
        owners=[dict(name="Kebede Alemu Tadesse", dob="1979-03-12", nationality="ET", share=70),
                dict(name="Rahel Desta Gebre", dob="1988-07-19", nationality="ET", share=30)],
        activity="Cold-chain distribution of fruit and vegetables", license_no="BL/SD/05/0017720",
        license_issue="2026-01-15", license_expiry="2027-01-14", id_number="FAN 7714 0362 9921",
        id_expiry="2030-03-12"),
    "merkato": dict(
        name="Merkato Mobile Accessories", legal_form="sole_trader", category="electronics",
        registration_no="AA/10/2/6/0022931/2016", tin="0060318845", phone="+251 918 640 371",
        address="Addis Ketema Sub-city, Merkato, Addis Ababa", monthly_volume_etb=300_000,
        owners=[dict(name="Abel Tsegaye Mekonnen", dob="1995-12-08", nationality="ET", share=100)],
        activity="Retail of mobile phone accessories", license_no="BL/AA/10/0022931",
        license_issue="2026-02-10", license_expiry="2027-02-09", id_number="FAN 9905 3374 1180",
        id_expiry="2033-12-08"),
}

for slug, m in MERCHANTS.items():
    m["email"] = INBOX.format(slug)
    m["country"] = "ET"

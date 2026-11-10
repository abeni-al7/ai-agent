"""Render synthetic KYB documents (watermarked SPECIMEN) for the demo merchants.

Run: uv run python demo/make_documents.py   -> demo/documents/<merchant>/<doc>.pdf|png
"""

import html
import pathlib
import subprocess
import sys
import tempfile
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from merchants import MERCHANTS  # noqa: E402

OUT = pathlib.Path(__file__).parent / "documents"
CHROME = "google-chrome"

CSS = """
@page { size: A4; margin: 0 }
* { box-sizing: border-box }
body { margin: 0; font: 13px/1.5 'Noto Serif', 'Noto Serif Ethiopic', Georgia, serif; color: #1d1d1b }
.sheet { width: 210mm; height: 297mm; padding: 22mm 20mm; position: relative; overflow: hidden;
         background: #fbf8f1; border: 10px double #6b5a2e }
.wm { position: absolute; inset: 0; display: grid; place-items: center; pointer-events: none }
.wm span { transform: rotate(-32deg); font: 700 46px 'Noto Sans', sans-serif; color: rgba(160, 30, 30, .13);
           letter-spacing: 4px; text-align: center }
.am { font-family: 'Noto Serif Ethiopic', serif }
header { text-align: center; border-bottom: 2px solid #6b5a2e; padding-bottom: 10px; margin-bottom: 18px }
header .am { font-size: 15px } header h1 { font-size: 20px; margin: 6px 0 2px; letter-spacing: 1px }
header h2 { font-size: 14px; margin: 0; font-weight: 400 }
table { width: 100%; border-collapse: collapse; margin: 12px 0 }
td, th { border: 1px solid #b9ad8a; padding: 7px 9px; text-align: left; vertical-align: top }
th { background: #efe8d6; width: 38% }
.seal { position: absolute; right: 26mm; bottom: 34mm; width: 34mm; height: 34mm; border-radius: 50%;
        border: 3px solid #2f4d8a; color: #2f4d8a; display: grid; place-items: center; text-align: center;
        font: 600 9px 'Noto Sans', sans-serif; transform: rotate(-12deg); opacity: .8 }
.sign { position: absolute; left: 20mm; bottom: 36mm; font-size: 12px }
.sign i { font: italic 22px 'Noto Serif', serif; display: block; margin-bottom: 2px }
.foot { position: absolute; bottom: 12mm; left: 20mm; right: 20mm; font: 10px 'Noto Sans', sans-serif;
        color: #7a6f55; text-align: center }
p { margin: 8px 0 }
"""
WM = '<div class="wm"><span>SPECIMEN · SYNTHETIC TEST DOCUMENT<br>NOT A REAL OR VALID DOCUMENT</span></div>'
FOOT = '<div class="foot">Synthetic document generated for the Wekil demo. All people and businesses are fictional.</div>'


def e(x) -> str:
    return html.escape(str(x))


def fmt(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d %B %Y")


def page(title_am: str, title: str, office: str, rows: list[tuple[str, str]], extra: str = "", seal: str = "") -> str:
    trs = "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in rows)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="sheet">
{WM}<header><div class="am">የኢትዮጵያ ፌዴራላዊ ዴሞክራሲያዊ ሪፐብሊክ</div>
<div style="font-size:12px">Federal Democratic Republic of Ethiopia</div>
<div class="am" style="margin-top:6px">{e(title_am)}</div><h1>{e(title)}</h1><h2>{e(office)}</h2></header>
<table>{trs}</table>{extra}
<div class="sign"><i>{e(seal or 'A. Wondimu')}</i>Registrar (specimen)</div>
<div class="seal">SPECIMEN<br>REGISTRAR<br>SEAL</div>{FOOT}</div></body></html>"""


def license_(m: dict, expiry: str, issue: str) -> str:
    return page("የንግድ ፈቃድ", "BUSINESS LICENCE", "Trade Bureau (specimen issuing office)", [
        ("Licence number", m["license_no"]), ("Business name", m["name"]),
        ("Licence holder / manager", m["owners"][0]["name"]), ("Registration number", m["registration_no"]),
        ("Taxpayer ID (TIN)", m["tin"]), ("Business activity", m["activity"]), ("Business address", m["address"]),
        ("Date of issue", fmt(issue)), ("Valid until", fmt(expiry))],
        "<p>This licence must be renewed annually before its expiry date.</p>")


def tin(m: dict) -> str:
    return page("የግብር ከፋይ መለያ ቁጥር ምዝገባ ምስክር ወረቀት", "TAXPAYER REGISTRATION CERTIFICATE",
                "Revenue Authority (specimen issuing office)", [
                    ("Taxpayer name", m["name"]), ("Taxpayer identification number (TIN)", m["tin"]),
                    ("Taxpayer type", "Individual business" if m["legal_form"] == "sole_trader" else "Company"),
                    ("Registered address", m["address"]), ("Date of registration", fmt(m["license_issue"]))])


def memorandum(m: dict) -> str:
    rows = "".join(f"<tr><td>{e(o['name'])}</td><td>Ethiopian</td><td>{o['share']}%</td></tr>" for o in m["owners"])
    body = (f"<p>We, the undersigned, have agreed to form a private limited company under the Commercial Code "
            f"of Ethiopia with the following particulars.</p>"
            f"<p><b>Article 1. Name.</b> The name of the company is <b>{e(m['name'])}</b>.</p>"
            f"<p><b>Article 2. Head office.</b> {e(m['address'])}.</p>"
            f"<p><b>Article 3. Objective.</b> {e(m['activity'])}.</p>"
            f"<p><b>Article 4. Capital and shareholders.</b></p>"
            f"<table><tr><th>Shareholder</th><th>Nationality</th><th>Share</th></tr>{rows}</table>"
            f"<p><b>Article 5. Management.</b> {e(m['owners'][0]['name'])} is appointed general manager.</p>")
    return page("የመመስረቻ ጽሑፍ", "MEMORANDUM OF ASSOCIATION", "Document Authentication (specimen)", [
        ("Company name", m["name"]), ("Registration number", m["registration_no"]),
        ("Date", fmt(m["license_issue"]))], body)


def owner_id(m: dict) -> str:
    o = m["owners"][0]
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
body {{ margin: 0; background: #d9dee3; font: 14px 'Noto Sans', 'Noto Sans Ethiopic', sans-serif }}
.card {{ width: 860px; height: 540px; margin: 30px; border-radius: 28px; position: relative; overflow: hidden;
  background: linear-gradient(135deg, #e9f2ea, #f6efdc 60%, #e4ecf6); box-shadow: 0 6px 24px rgba(0,0,0,.25) }}
.top {{ background: #1f5f3f; color: #fff; padding: 16px 28px; font-size: 18px }} .top small {{ display: block; opacity: .85 }}
.photo {{ position: absolute; left: 32px; top: 120px; width: 190px; height: 240px; border-radius: 10px;
  background: linear-gradient(#b8c2cc, #8d99a6); display: grid; place-items: center; color: #fff; font-size: 64px }}
.f {{ position: absolute; left: 250px; top: 112px; right: 30px }} .f div {{ margin: 0 0 12px }}
.f b {{ display: block; font-size: 12px; color: #4a5a52; font-weight: 600 }} .f span {{ font-size: 21px }}
.wm {{ position: absolute; inset: 0; display: grid; place-items: center; transform: rotate(-20deg);
  color: rgba(170,30,30,.16); font: 800 38px sans-serif; text-align: center }}
</style></head><body><div class="card"><div class="top">የኢትዮጵያ ብሔራዊ መታወቂያ · National ID (specimen)
<small>Synthetic test card for the Wekil demo; not a real document</small></div>
<div class="photo">{e(o['name'][0])}</div><div class="f">
<div><b>Full name / ሙሉ ስም</b><span>{e(o['name'])}</span></div>
<div><b>Date of birth</b><span>{fmt(o['dob'])}</span></div>
<div><b>Nationality</b><span>Ethiopian</span></div>
<div><b>ID number (FAN)</b><span>{e(m['id_number'])}</span></div>
<div><b>Expiry date</b><span>{fmt(m['id_expiry'])}</span></div></div>
<div class="wm">SPECIMEN · SYNTHETIC<br>NOT VALID</div></div></body></html>"""


def render(html_text: str, out: pathlib.Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html_text)
    args = [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--hide-scrollbars"]
    if out.suffix == ".png":
        args += ["--window-size=920,600", f"--screenshot={out}"]
    else:
        args += [f"--print-to-pdf={out}"]
    subprocess.run([*args, f"file://{f.name}"], check=True, capture_output=True)


def main() -> None:
    for slug, m in MERCHANTS.items():
        d = OUT / slug
        render(license_(m, m["license_expiry"], m["license_issue"]), d / "business_license.pdf")
        render(tin(m), d / "tin_certificate.pdf")
        if m["legal_form"] != "sole_trader":
            render(memorandum(m), d / "memorandum.pdf")
        render(owner_id(m), d / "owner_id.png")
        if "renewed_expiry" in m:
            render(license_(m, m["renewed_expiry"], date.today().isoformat()), d / "business_license_renewed.pdf")
        print(slug, sorted(p.name for p in d.iterdir()))


if __name__ == "__main__":
    main()

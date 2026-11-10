import { useState } from "react";
import { api } from "../api";
import { DOC_LABEL } from "../ui";
import { FilePick, PortalShell } from "./Portal";

const FORMS = [
  { key: "sole_trader", label: "Sole trader", am: "የግል ነጋዴ" },
  { key: "plc", label: "Private limited company (PLC)", am: "ኃ/የተ/የግ/ማ" },
  { key: "share_company", label: "Share company", am: "አክሲዮን ማኅበር" },
];
const REQUIRED: Record<string, string[]> = {
  sole_trader: ["business_license", "tin_certificate", "owner_id"],
  plc: ["business_license", "tin_certificate", "memorandum", "owner_id"],
  share_company: ["business_license", "tin_certificate", "memorandum", "owner_id"],
};
const CATEGORIES = ["retail", "restaurant", "coffee_export", "pharmacy", "electronics", "travel_agency", "education", "logistics",
  "money_transfer", "charity"];
const blankOwner = { name: "", dob: "", nationality: "ET", share: 100 };

export function ApplyPage() {
  const [step, setStep] = useState(1);
  const [b, setB] = useState({ name: "", legal_form: "sole_trader", category: "retail", registration_no: "", tin: "", email: "",
    phone: "", address: "", monthly_volume_etb: "" });
  const [owners, setOwners] = useState([{ ...blankOwner }]);
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState<number | null>(null);
  const set = (k: keyof typeof b) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setB({ ...b, [k]: e.target.value });
  const need = REQUIRED[b.legal_form];

  async function submit() {
    setBusy(true); setError("");
    const fd = new FormData();
    const chosen = need.filter((t) => files[t]);
    fd.append("application", JSON.stringify({ ...b, owners: owners.map((o) => ({ ...o, share: Number(o.share) })) }));
    fd.append("doc_types", JSON.stringify(chosen));
    chosen.forEach((t) => fd.append("files", files[t]!));
    try { setDone((await api<{ id: number }>("/api/apply", { method: "POST", body: fd })).id); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  if (done) return (
    <PortalShell>
      <div className="portal__done">
        <h1>Application received</h1>
        <p>Your reference is <span className="serial">WK {String(done).padStart(6, "0")}</span>.</p>
        <p>We are checking your documents now. If anything is missing we will email {b.email} with a link to send it; otherwise you will hear our decision by email.</p>
      </div>
    </PortalShell>
  );

  return (
    <PortalShell>
      <h1>Apply to accept payments</h1>
      <p className="muted" lang="am">ክፍያ ለመቀበል ያመልክቱ</p>
      <ol className="steps" aria-label="Progress">
        {["Business", "Owners", "Documents"].map((s, i) => <li key={s} aria-current={step === i + 1 ? "step" : undefined} className={step > i + 1 ? "is-done" : ""}>{s}</li>)}
      </ol>

      {step === 1 && (
        <form className="form" onSubmit={(e) => { e.preventDefault(); setStep(2); }}>
          <label>Registered business name <small lang="am">የንግድ ስም</small><input value={b.name} onChange={set("name")} required /></label>
          <fieldset><legend>Legal form <small lang="am">የንግድ ዓይነት</small></legend>
            {FORMS.map((f) => <label key={f.key} className="choice"><input type="radio" name="form" checked={b.legal_form === f.key} onChange={() => setB({ ...b, legal_form: f.key })} />{f.label} <small lang="am">{f.am}</small></label>)}
          </fieldset>
          <label>What you sell<select value={b.category} onChange={set("category")}>{CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}</select></label>
          <div className="form__row">
            <label>Registration number<input value={b.registration_no} onChange={set("registration_no")} placeholder="AA/14/7/2/0019482/2015" required /></label>
            <label>TIN<input value={b.tin} onChange={set("tin")} inputMode="numeric" placeholder="10 digits" required /></label>
          </div>
          <label>Business address<input value={b.address} onChange={set("address")} required /></label>
          <div className="form__row">
            <label>Email for updates<input type="email" value={b.email} onChange={set("email")} required /></label>
            <label>Phone<input type="tel" value={b.phone} onChange={set("phone")} placeholder="+251 9…" required /></label>
          </div>
          <label>Expected payments per month (ETB)<input inputMode="numeric" value={b.monthly_volume_etb} onChange={set("monthly_volume_etb")} required /></label>
          <button className="btn btn--primary btn--wide">Continue to owners</button>
        </form>
      )}

      {step === 2 && (
        <form className="form" onSubmit={(e) => { e.preventDefault(); setStep(3); }}>
          <p className="muted">List everyone who owns 10% or more of the business, as on your memorandum.</p>
          {owners.map((o, i) => (
            <fieldset key={i} className="owner-card"><legend>Owner {i + 1}</legend>
              <label>Full name, as on their ID<input value={o.name} required onChange={(e) => setOwners(owners.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} /></label>
              <div className="form__row">
                <label>Date of birth<input type="date" value={o.dob} required onChange={(e) => setOwners(owners.map((x, j) => j === i ? { ...x, dob: e.target.value } : x))} /></label>
                <label>Share (%)<input inputMode="numeric" value={o.share} required onChange={(e) => setOwners(owners.map((x, j) => j === i ? { ...x, share: Number(e.target.value) } : x))} /></label>
              </div>
              {owners.length > 1 && <button type="button" className="btn btn--ghost" onClick={() => setOwners(owners.filter((_, j) => j !== i))}>Remove owner {i + 1}</button>}
            </fieldset>
          ))}
          <button type="button" className="btn" onClick={() => setOwners([...owners, { ...blankOwner, share: 0 }])}>Add another owner</button>
          <div className="form__nav"><button type="button" className="btn btn--ghost" onClick={() => setStep(1)}>Back</button><button className="btn btn--primary">Continue to documents</button></div>
        </form>
      )}

      {step === 3 && (
        <div className="form">
          <p className="muted">A clear photo or PDF of each, up to 8 MB.</p>
          {need.map((t) => <FilePick key={t} label={DOC_LABEL[t]} file={files[t] ?? null} onPick={(f) => setFiles({ ...files, [t]: f })} />)}
          {error && <p className="error" role="alert">{error}</p>}
          <div className="form__nav">
            <button type="button" className="btn btn--ghost" onClick={() => setStep(2)}>Back</button>
            <button className="btn btn--primary" disabled={busy} onClick={submit}>{busy ? "Sending…" : "Send application"}</button>
          </div>
          {need.some((t) => !files[t]) && <p className="small muted">You can send now and add missing documents later from the link we email you.</p>}
        </div>
      )}
    </PortalShell>
  );
}

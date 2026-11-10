import { marked } from "marked";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, fileUrl, type Doc, type Hit, type Merchant } from "../api";
import { Seal, StampMark, WekilMark } from "../Seal";
import { DOC_LABEL, Empty, Serial, Status, TierMark, date, describe, time } from "../ui";
import { usePoll } from "./usePoll";

const FIELD_LABEL: Record<string, string> = {
  name: "Name", tin: "TIN", registration_no: "Registration", license_no: "Licence no.", activity: "Activity",
  address: "Address", issue_date: "Issued", expiry_date: "Expires", dob: "Date of birth", nationality: "Nationality",
  id_number: "ID number",
};

export function WorkspacePage() {
  const { id } = useParams();
  const { data: m, reload } = usePoll<Merchant>(`/api/merchants/${id}`, 4000);
  if (!m) return <p className="muted">Loading the file…</p>;
  const decided = m.status === "approved" || m.status === "rejected";
  const reviewing = m.status === "submitted" || m.status === "reviewing";
  return (
    <article className="workspace">
      <header className="ws-head">
        <Seal key={`${m.risk_tier}-${m.status}`} tier={reviewing ? null : m.risk_tier}
          stamp={decided ? { outcome: m.status, date: date(m.decided_at) } : null} animate={!decided} />
        <div className="ws-head__text">
          <p className="ws-head__crumb"><Link to="/queue">Applications</Link> / <Serial id={m.id} /></p>
          <h1>{m.name}</h1>
          <p className="ws-head__meta">
            <Status status={m.status} /> <TierMark tier={m.risk_tier} score={m.risk_score} />
            <span className="muted">{m.legal_form.replace("_", " ")}, {m.category.replace(/_/g, " ")}, ETB {m.monthly_volume_etb.toLocaleString()} a month</span>
          </p>
        </div>
      </header>

      {reviewing && <p className="working"><WekilMark /> Wekil is reviewing this application. The page updates as each check finishes.</p>}

      <div className="ws-grid">
        <div className="ws-main">
          {m.memo && (
            <section aria-labelledby="memo" className="memo">
              <h2 id="memo">Wekil's memo</h2>
              <div className="prose" dangerouslySetInnerHTML={{ __html: marked.parse(m.memo, { async: false }) as string }} />
            </section>
          )}
          <Findings m={m} />
          <Screening m={m} onChange={reload} />
          <Documents docs={m.documents.filter((d) => d.status !== "superseded")} />
          <Business m={m} />
        </div>
        <aside className="ws-side">
          <Requests m={m} />
          <Timeline m={m} />
        </aside>
      </div>
      <Decision m={m} onDone={reload} />
    </article>
  );
}

function Findings({ m }: { m: Merchant }) {
  return (
    <section aria-labelledby="findings">
      <h2 id="findings">Findings</h2>
      {m.issues.length === 0 && <Empty>{m.status === "reviewing" ? "Checking…" : "Documents agree with each other and with the application."}</Empty>}
      <ul className="findings">
        {m.issues.map((i, k) => (
          <li key={k} className={`finding finding--${i.severity}`}>
            <span className="finding__kind">{i.severity === "blocker" ? "Blocks approval" : "Note"}</span>
            <span>{i.text}</span>
            {i.doc_type && <a href={`#doc-${i.doc_type}`} className="finding__src">{DOC_LABEL[i.doc_type]}</a>}
          </li>
        ))}
      </ul>
      {m.risk_factors.length > 0 && (
        <details className="factors">
          <summary>How the risk score was built</summary>
          <ul>{m.risk_factors.map((f) => <li key={f}>{f}</li>)}</ul>
        </details>
      )}
      <Registry r={m.registry} />
    </section>
  );
}

function Registry({ r }: { r: Record<string, any> }) {
  if (!r?.source) return null;
  const ok = r.status === "match";
  return (
    <p className={`registry ${ok ? "registry--ok" : "registry--miss"}`}>
      <strong>{r.source}:</strong>{" "}
      {ok ? `registered as ${r.registered_name}${r.registry_status ? `, ${r.registry_status}` : ""}` : String(r.note ?? r.status).replace("_", " ")}
      {r.officers?.length ? `; officers: ${r.officers.join(", ")}` : ""}
    </p>
  );
}

function Screening({ m, onChange }: { m: Merchant; onChange: () => void }) {
  const [busy, setBusy] = useState<number | null>(null);
  async function decide(h: Hit, decision: "confirmed" | "dismissed") {
    setBusy(h.id);
    try { await api(`/api/hits/${h.id}`, { method: "POST", json: { decision } }); onChange(); } finally { setBusy(null); }
  }
  const names = 1 + m.owners.length;
  return (
    <section aria-labelledby="screening">
      <h2 id="screening">Sanctions screening</h2>
      {m.hits.length === 0 ? (
        <Empty>{m.status === "reviewing" ? "Screening…" : `${names} names screened against the OFAC and UN lists. No candidates.`}</Empty>
      ) : (
        <ul className="hits">
          {m.hits.map((h) => (
            <li key={h.id} className={`hit hit--${h.decision ?? h.verdict}`}>
              <div className="hit__pair">
                <div><span className="small muted">Our party</span><strong>{h.subject}</strong>
                  {m.owners.find((o) => o.name === h.subject)?.dob && <span className="small">born {m.owners.find((o) => o.name === h.subject)!.dob}</span>}</div>
                <div className="hit__sim" aria-label={`Name similarity ${h.score} out of 100`}><span>{h.score}</span>similar</div>
                <div><span className="small muted">{h.entry.source} list entry</span><strong>{h.entry.name}</strong>
                  <span className="small">{[h.entry.details.dob && `born ${h.entry.details.dob}`, h.entry.details.nationality].filter(Boolean).join(", ")}</span></div>
              </div>
              <p className="hit__verdict"><WekilMark /> {h.verdict === "likely_match" ? "Likely the same party" : "Likely not the same party"}</p>
              <ul className="hit__reasons">{h.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              {h.decision ? (
                <p className="hit__decided"><StampMark /> You {h.decision === "confirmed" ? "confirmed this match" : "dismissed this candidate"}.</p>
              ) : (
                <div className="hit__actions">
                  <button className="btn" disabled={busy === h.id} onClick={() => decide(h, "dismissed")}>Not the same, dismiss</button>
                  <button className="btn btn--danger" disabled={busy === h.id} onClick={() => decide(h, "confirmed")}>Confirm match</button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Documents({ docs }: { docs: Doc[] }) {
  return (
    <section aria-labelledby="documents">
      <h2 id="documents">Documents and what Wekil read</h2>
      {docs.length === 0 && <Empty>No documents uploaded.</Empty>}
      <div className="docs">{docs.map((d) => <DocumentRow key={d.id} d={d} />)}</div>
    </section>
  );
}

function DocumentRow({ d }: { d: Doc }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let u: string | null = null;
    fileUrl(d.id, "preview").then((x) => setUrl((u = x)));
    return () => { if (u) URL.revokeObjectURL(u); };
  }, [d.id]);
  const open = async () => window.open(await fileUrl(d.id), "_blank", "noopener");
  const fields = Object.entries(d.fields).filter(([k, v]) => FIELD_LABEL[k] && v);
  const shareholders = (d.fields.shareholders as { name: string; share_percent?: number }[] | undefined) ?? [];
  const concerns = (d.fields.concerns as string[] | undefined) ?? [];
  return (
    <div className="doc" id={`doc-${d.doc_type}`}>
      <div className="doc__page">
        {url ? <img src={url} alt={`${DOC_LABEL[d.doc_type]} as uploaded, first page`} /> : <div className="doc__ph" />}
      </div>
      <div className="doc__fields">
        <h3>{DOC_LABEL[d.doc_type] ?? d.doc_type}</h3>
        {d.status === "pending" ? <p className="muted">Waiting to be read…</p> : (
          <dl>
            {fields.map(([k, v]) => <div key={k}><dt>{FIELD_LABEL[k]}</dt><dd>{String(v)}</dd></div>)}
            {shareholders.length > 0 && <div><dt>Shareholders</dt><dd>{shareholders.map((s) => `${s.name}${s.share_percent ? ` (${s.share_percent}%)` : ""}`).join(", ")}</dd></div>}
          </dl>
        )}
        {concerns.length > 0 && <ul className="doc__concerns">{concerns.map((c) => <li key={c}>{c}</li>)}</ul>}
        <button className="linkish small" onClick={open}>Open {d.filename}</button>
      </div>
    </div>
  );
}

function Business({ m }: { m: Merchant }) {
  return (
    <section aria-labelledby="declared">
      <h2 id="declared">What the merchant declared</h2>
      <dl className="declared">
        <div><dt>Registration</dt><dd className="num">{m.registration_no || "None given"}</dd></div>
        <div><dt>TIN</dt><dd className="num">{m.tin || "None given"}</dd></div>
        <div><dt>Address</dt><dd>{m.address}</dd></div>
        <div><dt>Contact</dt><dd>{m.email}<br />{m.phone}</dd></div>
        <div><dt>Owners</dt><dd>{m.owners.map((o) => <span key={o.name} className="owner">{o.name}{o.share ? `, ${o.share}%` : ""}{o.dob ? `, born ${o.dob}` : ""}</span>)}</dd></div>
      </dl>
    </section>
  );
}

function Requests({ m }: { m: Merchant }) {
  const open = m.requests.filter((r) => r.status !== "answered");
  const cases = m.cases.filter((c) => c.status === "open");
  if (!open.length && !cases.length) return null;
  return (
    <section aria-labelledby="open" className="side-block">
      <h2 id="open">Open with the merchant</h2>
      {open.map((r) => (
        <div key={r.id} className="request">
          <p><strong>Due {date(r.due_on)}</strong>{r.reminders ? `, ${r.reminders} reminder${r.reminders > 1 ? "s" : ""} sent` : ""}{r.status === "escalated" ? ", escalated" : ""}</p>
          <ul>{r.items.map((i) => <li key={i.text}>{i.text}</li>)}</ul>
        </div>
      ))}
      {cases.map((c) => <p key={c.id} className={`case case--${c.kind}`}>{c.detail}</p>)}
    </section>
  );
}

function Timeline({ m }: { m: Merchant }) {
  return (
    <section aria-labelledby="trail" className="side-block">
      <h2 id="trail">Audit trail</h2>
      <ol className="trail">
        {[...m.events].reverse().map((e, i) => (
          <li key={i} className={`trail__item trail__item--${e.actor}`}>
            {e.actor === "analyst" ? <StampMark /> : e.actor === "merchant" ? <span className="mark mark--merchant" aria-label="Merchant" role="img" /> : <WekilMark />}
            <span>{describe(e)}</span>
            <time dateTime={e.at}>{date(e.at)}, {time(e.at)}</time>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Decision({ m, onDone }: { m: Merchant; onDone: () => void }) {
  const [mode, setMode] = useState<"" | "request" | "reject">("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (m.status === "approved" || m.status === "rejected") return null;
  const pendingHit = m.hits.some((h) => h.verdict === "likely_match" && !h.decision);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true); setError("");
    try { await fn(); setMode(""); setNote(""); onDone(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  const approve = () => run(() => api(`/api/merchants/${m.id}/decision`, { method: "POST", json: { approve: true, note } }));
  const reject = () => run(() => api(`/api/merchants/${m.id}/decision`, { method: "POST", json: { approve: false, note } }));
  const request = () => run(() => api(`/api/merchants/${m.id}/request`, { method: "POST", json: { items: note.split("\n").filter(Boolean) } }));
  const again = () => run(() => api(`/api/merchants/${m.id}/review`, { method: "POST" }));

  return (
    <footer className="decide" aria-label="Decision">
      {mode && (
        <div className="decide__note">
          <label htmlFor="note">{mode === "request" ? "What should the merchant send? One item per line." : "Reason for rejecting (sent to the merchant)"}</label>
          <textarea id="note" rows={3} value={note} onChange={(e) => setNote(e.target.value)} autoFocus />
        </div>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      <div className="decide__bar">
        {mode === "" && <>
          {m.status === "ready" && <button className="btn btn--primary" disabled={busy || pendingHit} onClick={approve}
            title={pendingHit ? "Confirm or dismiss the possible sanctions match first" : undefined}>Approve merchant</button>}
          <button className="btn" disabled={busy} onClick={() => setMode("request")}>Request documents</button>
          <button className="btn btn--ghost" disabled={busy} onClick={again}>Review again</button>
          <span className="decide__gap" />
          {m.status === "ready" && <button className="btn btn--danger-outline" disabled={busy} onClick={() => setMode("reject")}>Reject…</button>}
        </>}
        {mode === "request" && <><button className="btn btn--primary" disabled={busy || !note.trim()} onClick={request}>Email the request</button><button className="btn" onClick={() => setMode("")}>Cancel</button></>}
        {mode === "reject" && <><button className="btn btn--danger" disabled={busy} onClick={reject}>Reject and notify merchant</button><button className="btn" onClick={() => setMode("")}>Cancel</button></>}
        {pendingHit && mode === "" && <span className="small muted">Resolve the possible sanctions match before approving.</span>}
      </div>
    </footer>
  );
}

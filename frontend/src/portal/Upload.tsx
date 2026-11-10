import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { DOC_LABEL, date } from "../ui";
import { FilePick, PortalShell } from "./Portal";

interface Req { merchant: string; items: { doc_type: string | null; text: string }[]; due_on: string; status: string }

export function UploadPage() {
  const { token } = useParams();
  const [req, setReq] = useState<Req | null>(null);
  const [error, setError] = useState("");
  const [files, setFiles] = useState<{ type: string; file: File | null }[]>([]);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    api<Req>(`/api/upload/${token}`).then((r) => {
      setReq(r);
      const types = [...new Set(r.items.map((i) => i.doc_type).filter(Boolean))] as string[];
      setFiles(types.map((t) => ({ type: t, file: null })));
    }).catch((e) => setError(e.message));
  }, [token]);

  async function send() {
    setBusy(true); setError("");
    const fd = new FormData();
    const chosen = files.filter((f) => f.file);
    fd.append("doc_types", JSON.stringify(chosen.map((f) => f.type)));
    chosen.forEach((f) => fd.append("files", f.file!));
    fd.append("note", note);
    try { await api(`/api/upload/${token}`, { method: "POST", body: fd }); setSent(true); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  if (error && !req) return <PortalShell><h1>This link doesn't work</h1><p>{error}</p></PortalShell>;
  if (!req) return <PortalShell><p className="muted">Loading…</p></PortalShell>;
  if (sent || req.status !== "open") return (
    <PortalShell>
      <div className="portal__done"><h1>Thank you, we have it</h1><p>We are checking the new documents now and will email you if anything else is needed.</p></div>
    </PortalShell>
  );

  return (
    <PortalShell>
      <h1>{req.merchant}: what we still need</h1>
      <p className="muted">Please send these by <strong>{date(req.due_on)}</strong> so we can finish your review.</p>
      <ul className="needs">{req.items.map((i) => <li key={i.text}>{i.text}</li>)}</ul>
      <div className="form">
        {files.map((f, k) => (
          <FilePick key={f.type} label={DOC_LABEL[f.type] ?? f.type} file={f.file}
            onPick={(file) => setFiles(files.map((x, j) => (j === k ? { ...x, file } : x)))} />
        ))}
        {files.length === 0 && (
          <FilePick label="Supporting document" file={null} onPick={(file) => setFiles([{ type: "business_license", file }])} />
        )}
        <label>Anything to tell us? (optional)<textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)} /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn btn--primary btn--wide" disabled={busy || !files.some((f) => f.file)} onClick={send}>{busy ? "Sending…" : "Send documents"}</button>
      </div>
    </PortalShell>
  );
}

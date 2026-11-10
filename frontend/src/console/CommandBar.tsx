import { useEffect, useRef, useState } from "react";
import { api } from "../api";

interface Proposal { tool: string; args: Record<string, unknown> }
interface Reply { answer: string; proposals: Proposal[]; steps: Proposal[] }

const ACTION: Record<string, (a: Record<string, any>) => string> = {
  send_reminders: (a) => `Email a reminder to ${(a.merchant_names ?? []).join(", ")}`,
  schedule_review: (a) => `Schedule ${a.merchant_name}'s next review on ${a.review_date}`,
  request_documents: (a) => `Ask ${a.merchant_name} for: ${(a.items ?? []).join("; ")}`,
};

const EXAMPLES = ["Who has been waiting on us or on merchants for more than 3 days?", "Why is Blue Horizon Trading rated the way it is?",
  "Screen 'Ermias Ghermay' against the sanctions lists"];

export function CommandBar() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState<Reply | null>(null);
  const [done, setDone] = useState<string[] | null>(null);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); input.current?.focus(); }
      if (e.key === "Escape") { setReply(null); setDone(null); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function ask(q: string) {
    if (!q.trim()) return;
    setBusy(true); setError(""); setDone(null); setReply(null);
    try { setReply(await api<Reply>("/api/commands", { method: "POST", json: { text: q } })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function confirm() {
    if (!reply) return;
    setBusy(true);
    try {
      const r = await api<{ results: string[] }>("/api/commands/confirm", { method: "POST", json: { proposals: reply.proposals } });
      setDone(r.results); setReply({ ...reply, proposals: [] });
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  const open = busy || reply || error || done;
  return (
    <section className={`command ${open ? "command--open" : ""}`} aria-label="Ask Wekil">
      <form onSubmit={(e) => { e.preventDefault(); ask(text); }} className="command__form">
        <label htmlFor="command" className="sr-only">Ask Wekil to find, explain or do something</label>
        <input id="command" ref={input} value={text} onChange={(e) => setText(e.target.value)} autoComplete="off"
          placeholder="Ask Wekil: who is overdue, why a merchant is high risk, screen a name…" />
        <kbd className="command__key" aria-hidden="true">Ctrl K</kbd>
        <button type="submit" disabled={busy || !text.trim()}>{busy ? "Working" : "Ask"}</button>
      </form>
      {!open && (
        <div className="command__examples">
          {EXAMPLES.map((q) => <button key={q} type="button" onClick={() => { setText(q); ask(q); }}>{q}</button>)}
        </div>
      )}
      {open && (
        <div className="command__reply" aria-live="polite">
          {busy && !reply && <p className="muted">Wekil is looking it up…</p>}
          {error && <p className="error">{error}</p>}
          {reply && (
            <>
              {reply.steps.length > 0 && (
                <p className="command__steps">Checked: {[...new Set(reply.steps.map((s) => s.tool.replace(/_/g, " ")))].join(", ")}</p>
              )}
              <div className="command__answer">{reply.answer}</div>
              {reply.proposals.length > 0 && (
                <div className="plan">
                  <p className="plan__title">Wekil proposes. Nothing is sent until you confirm.</p>
                  <ol>{reply.proposals.map((p, i) => <li key={i}>{ACTION[p.tool]?.(p.args) ?? p.tool}</li>)}</ol>
                  <div className="plan__actions">
                    <button className="btn btn--primary" onClick={confirm} disabled={busy}>Confirm and send</button>
                    <button className="btn" onClick={() => setReply({ ...reply, proposals: [] })}>Discard</button>
                  </div>
                </div>
              )}
            </>
          )}
          {done && <ul className="done">{done.map((d) => <li key={d}>{d}</li>)}</ul>}
          <button className="command__close" onClick={() => { setReply(null); setDone(null); setError(""); }}>Close</button>
        </div>
      )}
    </section>
  );
}

import { Link, useSearchParams } from "react-router-dom";
import type { Card } from "../api";
import { Empty, Serial, Status, TierMark, ago, date } from "../ui";
import { usePoll } from "./usePoll";

const FILTERS = [
  { key: "", label: "All" },
  { key: "ready,needs_attention", label: "Ready for decision" },
  { key: "awaiting_merchant", label: "Waiting on merchant" },
  { key: "submitted,reviewing", label: "Being reviewed" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
];
const FORM: Record<string, string> = { sole_trader: "Sole trader", plc: "PLC", share_company: "Share company" };

export function QueuePage() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const { data } = usePoll<Card[]>(`/api/merchants?status=${status}`, 6000);
  return (
    <div>
      <header className="page-head">
        <h1>Applications</h1>
        <p className="muted">Oldest first, so nothing waits forever.</p>
      </header>
      <div className="tabs" role="tablist" aria-label="Filter by status">
        {FILTERS.map((f) => (
          <button key={f.key} role="tab" aria-selected={status === f.key} onClick={() => setParams(f.key ? { status: f.key } : {})}>{f.label}</button>
        ))}
      </div>
      <MerchantTable rows={data} />
    </div>
  );
}

export function MonitoringPage() {
  const { data } = usePoll<Card[]>("/api/merchants?status=approved", 10000);
  return (
    <div>
      <header className="page-head">
        <h1>Monitoring</h1>
        <p className="muted">Approved merchants. Wekil rescreens them against every new sanctions-list entry each morning and opens a case before anything lapses.</p>
      </header>
      <MerchantTable rows={data} monitoring />
    </div>
  );
}

function MerchantTable({ rows, monitoring }: { rows: Card[] | null; monitoring?: boolean }) {
  if (!rows) return <p className="muted">Loading…</p>;
  if (!rows.length) return <Empty>No merchants here yet. New applications arrive from the merchant portal at /apply.</Empty>;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">Merchant</th><th scope="col">Number</th><th scope="col">Status</th><th scope="col">Risk</th>
            <th scope="col">{monitoring ? "Next review" : "Received"}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((m) => (
            <tr key={m.id}>
              <td>
                <Link to={`/m/${m.id}`} className="table__name">{m.name}</Link>
                <span className="muted small">{FORM[m.legal_form] ?? m.legal_form}, {m.category.replace(/_/g, " ")}</span>
              </td>
              <td><Serial id={m.id} /></td>
              <td><Status status={m.status} />{m.open_hits > 0 && <span className="flag flag--block">Possible match</span>}</td>
              <td><TierMark tier={m.risk_tier} score={m.risk_score} /></td>
              <td className="num">{monitoring ? date(m.next_review) : ago(m.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

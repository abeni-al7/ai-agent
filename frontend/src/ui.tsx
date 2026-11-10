import type { ReactNode } from "react";
import type { Tier } from "./api";

export const DOC_LABEL: Record<string, string> = {
  business_license: "Business licence",
  tin_certificate: "TIN certificate",
  memorandum: "Memorandum of association",
  owner_id: "Owner ID",
};

export const STATUS: Record<string, { label: string; form: "solid" | "dashed" | "struck" | "open" }> = {
  submitted: { label: "Received", form: "dashed" },
  reviewing: { label: "Wekil is reviewing", form: "dashed" },
  awaiting_merchant: { label: "Waiting on merchant", form: "open" },
  ready: { label: "Ready for your decision", form: "solid" },
  needs_attention: { label: "Needs attention", form: "solid" },
  approved: { label: "Approved", form: "solid" },
  rejected: { label: "Rejected", form: "struck" },
};

export function Status({ status }: { status: string }) {
  const s = STATUS[status] ?? { label: status, form: "open" };
  return <span className={`status status--${s.form} status--${status}`}>{s.label}</span>;
}

export function TierMark({ tier, score }: { tier: Tier; score?: number | null }) {
  if (!tier) return <span className="tier tier--none">Not scored</span>;
  return (
    <span className={`tier tier--${tier}`}>
      {tier[0].toUpperCase() + tier.slice(1)} risk{score != null && <span className="tier__score"> {score}</span>}
    </span>
  );
}

/** Merchant and case numbers are set like the serial on a note. */
export function Serial({ id, prefix = "WK" }: { id: number; prefix?: string }) {
  return <span className="serial">{prefix} {String(id).padStart(6, "0")}</span>;
}

export const date = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "";
export const time = (iso: string) => new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
export const ago = (iso: string) => {
  const d = Math.round((Date.now() - new Date(iso).getTime()) / 86_400_000);
  return d <= 0 ? "today" : d === 1 ? "yesterday" : `${d} days ago`;
};

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}

/** Plain-language sentence for an audit event. */
export function describe(e: { action: string; detail: Record<string, unknown> }): string {
  const d = e.detail as Record<string, any>;
  switch (e.action) {
    case "application_received": return `Application received with ${d.documents} document${d.documents === 1 ? "" : "s"}`;
    case "review_started": return "Started the review";
    case "document_read": return `Read the ${DOC_LABEL[d.doc_type] ?? d.doc_type}${d.concerns?.length ? `, ${d.concerns.length} concern${d.concerns.length > 1 ? "s" : ""}` : ""}`;
    case "consistency_checked": return `Cross-checked documents: ${d.blockers} blocker${d.blockers === 1 ? "" : "s"}, ${d.warnings} warning${d.warnings === 1 ? "" : "s"}${d.missing?.length ? `, ${d.missing.length} missing` : ""}`;
    case "registry_checked": return `Checked ${d.source}: ${String(d.status).replace("_", " ")}`;
    case "screened": return `Screened ${d.subjects} names against OFAC and UN lists: ${d.candidates} candidate${d.candidates === 1 ? "" : "s"}, ${d.likely_matches} likely match${d.likely_matches === 1 ? "" : "es"}`;
    case "risk_scored": return `Scored risk ${d.tier} (${d.score})`;
    case "memo_drafted": return "Drafted the decision memo";
    case "info_requested": return `Requested ${d.items?.length ?? 0} item${d.items?.length === 1 ? "" : "s"}, due ${date(d.due)}${d.emailed ? " (emailed)" : ""}`;
    case "merchant_uploaded": return `Merchant uploaded ${(d.documents ?? []).map((t: string) => DOC_LABEL[t] ?? t).join(", ")}`;
    case "merchant_replied": return `Merchant replied: ${d.summary}`;
    case "reminder_sent": return `Sent reminder ${d.reminder}`;
    case "request_escalated": return `Escalated: no reply ${d.days_overdue} days after the due date`;
    case "decided": return `${d.outcome === "approved" ? "Approved" : "Rejected"}${d.note ? `: ${d.note}` : ""}`;
    case "hit_confirmed": return `Confirmed a sanctions match: ${d.subject} is ${d.entry}`;
    case "hit_dismissed": return `Dismissed a sanctions candidate: ${d.subject} is not ${d.entry}`;
    case "case_opened": return `Opened a ${String(d.kind).replace("_", " ")} case: ${d.detail}`;
    case "case_closed": return `Closed the ${String(d.kind).replace("_", " ")} case`;
    case "rescreened": return `Rescreened ${d.subject} against new entry ${d.entry}: ${d.verdict === "likely_match" ? "likely match" : "not the same"}`;
    case "review_requested": return "Asked Wekil to review again";
    case "review_scheduled": return `Scheduled the next review for ${date(d.date)}`;
    case "review_failed": return `Review stopped: ${d.error}`;
    case "routine_started": return "Started the morning routine";
    case "routine_finished": return `Finished the morning routine`;
    case "command": return `Asked Wekil: "${d.text}"`;
    default: return e.action.replace(/_/g, " ");
  }
}

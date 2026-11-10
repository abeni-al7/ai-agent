const BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export const token = {
  get: () => localStorage.getItem("wekil.token"),
  set: (t: string | null) => (t ? localStorage.setItem("wekil.token", t) : localStorage.removeItem("wekil.token")),
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T = unknown>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (token.get()) headers.Authorization = `Bearer ${token.get()}`;
  let body = init.body;
  if (init.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(init.json);
  }
  const res = await fetch(BASE + path, { ...init, body, headers: { ...headers, ...(init.headers ?? {}) } });
  if (res.status === 401 && token.get()) {
    token.set(null);
    location.assign("/login");
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new ApiError(res.status, detail.detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export async function fileUrl(documentId: number, kind: "file" | "preview" = "file"): Promise<string> {
  const res = await fetch(`${BASE}/api/documents/${documentId}/${kind}`, { headers: { Authorization: `Bearer ${token.get()}` } });
  return URL.createObjectURL(await res.blob());
}

export type Tier = "low" | "medium" | "high" | "prohibited" | null;

export interface Card {
  id: number; name: string; legal_form: string; category: string; country: string; status: string;
  risk_tier: Tier; risk_score: number | null; created_at: string; next_review: string | null;
  blockers: number; open_hits: number;
}

export interface Issue { severity: "blocker" | "warning"; text: string; doc_type: string | null; ask: boolean }
export interface Hit {
  id: number; subject: string; score: number; verdict: "likely_match" | "likely_not"; reasons: string[];
  decision: "confirmed" | "dismissed" | null;
  entry: { id: string; source: string; name: string; kind: string; details: Record<string, string | null>; aliases: string[] };
}
export interface Doc {
  id: number; doc_type: string; filename: string; mime: string; status: string;
  fields: Record<string, unknown>; expires_on: string | null; uploaded_at: string;
}
export interface Event { actor: string; action: string; detail: Record<string, unknown>; at: string; merchant_id?: number; merchant?: string }

export interface Merchant extends Card {
  registration_no: string; tin: string; email: string; phone: string; address: string; monthly_volume_etb: number;
  owners: { name: string; dob?: string; nationality?: string; share?: number }[];
  issues: Issue[]; registry: Record<string, unknown>; risk_factors: string[]; memo: string | null; decided_at: string | null;
  documents: Doc[]; hits: Hit[];
  requests: { id: number; items: { text: string }[]; due_on: string; status: string; reminders: number; created_at: string }[];
  cases: { id: number; kind: string; detail: string; due_on: string; status: string }[];
  events: Event[];
}

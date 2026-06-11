export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const CODE_KEY = "cargolens_access_code";

export function getAccessCode(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(CODE_KEY) ?? "";
}

export function saveAccessCode(code: string) {
  localStorage.setItem(CODE_KEY, code);
}

export function clearAccessCode() {
  localStorage.removeItem(CODE_KEY);
}

function authHeaders(): Record<string, string> {
  const code = getAccessCode();
  return code ? { "X-Access-Code": code } : {};
}

/** Probe the API with a code; true if accepted. */
export async function verifyAccessCode(code: string): Promise<boolean> {
  const res = await fetch(`${API_URL}/api/meta`, {
    headers: { "X-Access-Code": code },
  });
  return res.ok;
}

export interface Kpis {
  total_orders: number;
  delivered_orders: number;
  delayed_orders: number;
  on_time_rate: number;
  avg_delivery_days: number;
}

export interface QueryRow {
  value: number;
  [dim: string]: string | number;
}

export interface QueryResult {
  rows: QueryRow[];
  explain: {
    spec: Record<string, unknown>;
    sql: string;
    filters_applied: string[];
    implicit_filters: string[];
  };
  suggested_chart: "line" | "bar" | "number";
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

export const getKpis = () => get<Kpis>("/api/kpis");

export interface ToolResult {
  tool: string;
  rows: Record<string, string | number | null>[];
  explain: {
    spec: Record<string, unknown>;
    sql?: string;
    filters_applied?: string[];
    implicit_filters?: string[];
    methodology?: string;
    [key: string]: unknown;
  };
  suggested_chart: "line" | "bar" | "number" | "forecast" | "none";
}

export interface ChatResponse {
  answer: string | null;
  results: ToolResult[];
  error: string | null;
}

export async function askQuestion(question: string): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ question }),
  });
  if (res.status === 429) {
    return {
      answer: null,
      results: [],
      error: "Rate limit reached — please wait a minute and try again.",
    };
  }
  if (!res.ok) throw new Error(`/api/chat → ${res.status}`);
  return res.json();
}

export async function runQuery(spec: object): Promise<QueryResult> {
  const res = await fetch(`${API_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(spec),
  });
  if (!res.ok) throw new Error(`/api/query → ${res.status}`);
  return res.json();
}

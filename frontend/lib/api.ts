export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  const res = await fetch(`${API_URL}${path}`);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

export const getKpis = () => get<Kpis>("/api/kpis");

export interface ToolResult {
  tool: string;
  rows: QueryRow[];
  explain: QueryResult["explain"];
  suggested_chart: QueryResult["suggested_chart"];
}

export interface ChatResponse {
  answer: string | null;
  results: ToolResult[];
  error: string | null;
}

export async function askQuestion(question: string): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(spec),
  });
  if (!res.ok) throw new Error(`/api/query → ${res.status}`);
  return res.json();
}

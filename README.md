# CargoLens — AI-Powered Logistics Analytics Dashboard

**Live app:** https://frontend-production-8d15.up.railway.app
**API:** https://backend-production-4b4e.up.railway.app/api/health

> 🔑 **Test credentials:** the live app is protected by a simple access code,
> **provided separately with the submission** (not committed here — this repo
> is public). Enter it once on the unlock screen; it is remembered locally.

A full-stack analytics app over a logistics dataset (400 orders, calendar year
2025) with two interfaces:

1. **Dashboard** — five KPIs and three charts, computed deterministically.
2. **Natural-language chat** — questions are interpreted by an LLM, routed to
   validated analytical tools, computed by the same deterministic engine, and
   answered with a chart and a full "how this was computed" panel.

It supports descriptive (KPIs/charts), diagnostic (NL queries), and
predictive/prescriptive analytics (demand forecast + inventory recommendation).

---

## Setup

### Prerequisites
- Python 3.12+, Node 22+
- An Anthropic API key (for the chat; the dashboard works without it)

### Backend
```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
.venv/bin/uvicorn app.main:app --reload --port 8000
```
The SQLite database is seeded automatically from `data/mock_logistics_data.csv`
on first startup.

### Frontend
```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

### Environment variables

| Variable | Service | Purpose | Default |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | backend | LLM for the chat interface | — (chat degrades gracefully without it) |
| `ACCESS_CODE` | backend | shared reviewer access code; all `/api/*` except `/api/health` require the `X-Access-Code` header | — (unset = open, for local dev) |
| `FRONTEND_ORIGIN` | backend | CORS allowlist | `http://localhost:3000` |
| `CHAT_MODEL` | backend | Claude model id | `claude-sonnet-4-6` |
| `DAILY_CHAT_CAP` | backend | global daily LLM-call cap | `500` (live deployment: `300`) |
| `NEXT_PUBLIC_API_URL` | frontend | backend URL (baked at build time) | `http://localhost:8000` |

### Tests
```bash
cd backend
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests/ -q
```
17 tests. The 4 live LLM tests skip automatically when `ANTHROPIC_API_KEY` is
unset. Expected values in the engine/forecast tests are **recomputed
independently from the raw CSV with stdlib code**, so a shared bug between the
SQL engine and the tests can't make a wrong number pass.

---

## Architecture

```
┌──────────────┐  NL question   ┌─────────────────────────────────────────┐
│  Next.js UI  │ ──────────────▶│             FastAPI backend             │
│  dashboard   │                │                                         │
│  + chat      │◀── answer ─────│ 1. AI INTERPRETATION                    │
└──────────────┘  + chart       │    Claude (tool calling) emits a        │
                  + explain     │    QuerySpec | ForecastSpec — never SQL │
                                │ 2. VALIDATION (business logic)          │
                                │    Pydantic + Literal allow-lists;      │
                                │    off-menu input → 422 / tool error    │
                                │ 3. COMPUTATION (deterministic)          │
                                │    spec → parameterized SQL over        │
                                │    read-only SQLite                     │
                                │ 4. PRESENTATION                         │
                                │    chart type from spec shape; explain  │
                                │    payload = the validated spec itself  │
                                └─────────────────────────────────────────┘
```

### Key design decisions

- **The LLM is a router, not a source of truth.** Its only outputs are (a)
  which tool to call and (b) a typed parameter object. A Pydantic model with
  `Literal` allow-lists validates every field; deterministic Python/SQL does
  all arithmetic. The LLM never sees the database and never writes SQL.
- **One computation path for every number.** The dashboard KPIs, the chart
  endpoints, and the AI tools all call the same `run_query(spec)` engine, so
  the dashboard and chat can't disagree.
- **Explainability is the validated spec.** Because the spec *is* the query
  plan, every answer ships with: the interpreted spec, the resolved filters
  (including date windows), implicit metric rules (e.g. "rate computed over
  completed orders only"), the generated SQL, and the full underlying row
  table — rendered in a collapsible panel.
- **SQLite over Postgres** for a 400-row read-only dataset: zero deploy
  friction, seeded from CSV at startup, opened read-only for all queries.
  The schema is plain SQL — swapping to Postgres is a connection-string
  change, not a redesign.
- **Two Railway services** (FastAPI + Next.js) in one project; CORS locked to
  the exact frontend origin.

### Data flow
1. User asks a question → `POST /api/chat`.
2. Claude (`claude-sonnet-4-6`) receives the question plus a system prompt
   containing dataset metadata and hard rules; it emits a tool call.
3. The tool input is validated (`QuerySpec`/`ForecastSpec`). Invalid specs are
   returned to the model as tool errors (one retry); valid specs are compiled
   to parameterized SQL from allow-listed fragments and executed.
4. Tool results (rows only — no derived conclusions) go back to the model,
   which writes the prose answer.
5. The response carries the answer plus each tool call's rows, explain
   payload, and a backend-selected chart type the UI renders.

---

## AI Approach

**Interpretation** — the system prompt gives the model the dataset's shape
(columns, valid values, date range) and hard rules: every number must come
from a tool result; relative dates resolve against the dataset's last order
date (2025-12-30), not today; unanswerable questions get a refusal plus the
closest supported question.

**Tool selection** — two tools, described declaratively:
- `query_analytics(QuerySpec)` — metrics (`count`, `on_time_rate`,
  `delay_rate`, `avg_delivery_days`, `sum_quantity`, `sum_order_value`),
  group-bys (carrier/region/warehouse/category/city/status/client/week/month),
  filters (statuses, carriers, regions, categories, warehouses, date range),
  sort and limit.
- `forecast_demand(ForecastSpec)` — category-level monthly demand forecast
  (moving average or linear trend), horizon 1–6 months, with inventory
  recommendation and methodology.

Chart selection is **deterministic, not LLM-chosen**: time dimension → line,
categorical group-by → bar, scalar → stat card, forecast → split
historical/forecast line.

---

## Assumptions

1. **"Delayed" is a status meaning *delivered late*.** Verified in the data:
   every `delayed` row has a delivery date; only `in_transit`/`canceled` rows
   lack one. So "orders delivered late" maps to `status = delayed`.
2. **On-time delivery rate = delivered / (delivered + delayed)** — completed
   orders only. Orders still in transit are not yet "on-time or late";
   counting them would understate the rate. `exception` (11) and `canceled`
   (3) are excluded from rate denominators but included in total orders.
3. **Average delivery time** excludes the 30 rows without a delivery date.
   This exclusion is surfaced in the explainability panel on every answer
   that uses it.
4. **Relative dates anchor to the dataset's max order date (2025-12-30).**
   The data is historical; "last month" against the wall clock would always
   return empty. The resolved absolute window is shown with every answer.
5. **Demand = sum(quantity)** (units), not order count or revenue, for all
   forecasting and inventory math.
6. **Forecast granularity is product category, not SKU.** 355 distinct SKUs
   across 400 rows (~1.1 orders/SKU) is not a time series. SKU requests roll
   up to the SKU's category and the answer says so explicitly. Category gives
   8 clean 12-point monthly series — enough for the basic methods the spec
   asks for, and defensible.
7. **Inventory recommendation = forecast monthly demand + 20% safety stock.**
   A deliberate simplification (no lead times or service levels in the data);
   the formula is stated in every recommendation.

## Limitations

- Single-turn chat: each question is answered independently (no conversation
  memory).
- The query engine supports one metric and one group-by per call (the model
  may make several calls for compound questions).
- Forecast methods are intentionally basic (per spec) — no seasonality
  modeling; one year of history can't separate seasonality from noise.
- In-memory rate limiting and daily cap reset on redeploy and assume a single
  instance.
- Auth is a single shared access code (sufficient for a review demo), layered
  with abuse protection on the chat endpoint: **10 questions/minute per IP**
  and a **global cap of 300 questions/day** on the live deployment (the
  endpoint calls a paid LLM API). Exceeding either returns a friendly notice;
  the dashboard is unaffected. A real deployment would use per-user auth and
  quotas.
- No streaming: answers arrive complete (a few seconds for chat).

## Future improvements

- Conversation memory with prompt caching for follow-up questions
  ("…and by region?").
- Postgres + read replica for a production dataset; the spec→SQL compiler is
  already parameterized.
- Exponential smoothing + backtest-based method selection once more history
  exists; per-SKU forecasts if/when order density supports it.
- Query history and result caching (same validated spec → cached rows).
- Evaluation harness: a fixed suite of NL questions scored nightly against
  the deterministic engine's ground truth (the live tests are the seed).
- RAG over unstructured docs (carrier contracts, SLAs) — out of scope here
  because this dataset has no unstructured corpus to retrieve from.

---

## AI usage disclosure

This project was built with AI assistance (Claude Code with Fable 5, plus
Claude Opus for planning). The architecture, data-correctness rules, scope
decisions, and final review are mine; AI generated code under that direction,
and every numeric behavior is verified by tests whose expected values are
computed independently from the raw CSV. The app itself uses Claude
Sonnet 4.6 for question interpretation at runtime, as documented above.

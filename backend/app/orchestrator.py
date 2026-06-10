"""AI orchestration layer.

The LLM's only job: interpret the question and emit a validated tool call
(QuerySpec / ForecastSpec). It never writes SQL and never computes numbers —
every figure in an answer comes from the deterministic engine in queries.py.

Relative dates ("last month", "last 3 months") are resolved against the
dataset's max order_date (2025-12-30), not the wall clock: the system prompt
states the anchor and the validated spec carries the resolved absolute window,
which is surfaced in the explainability payload.
"""

import os

import anthropic
from pydantic import ValidationError

from .forecast import ForecastSpec, run_forecast
from .queries import QuerySpec, dataset_meta, run_query

MODEL = os.environ.get("CHAT_MODEL", "claude-sonnet-4-6")
MAX_TOOL_ROUNDS = 4

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    return _client


def _build_system_prompt() -> str:
    meta = dataset_meta()
    return f"""You are the analytics assistant for CargoLens, a logistics dashboard.

You answer questions about ONE dataset of {meta['total']} shipment orders, \
order_date from {meta['min_date']} to {meta['max_date']}.

HARD RULES
- Every number in your answer MUST come from a tool result in this conversation. \
Never compute, estimate, or recall numbers yourself.
- If the question cannot be mapped to the available tools and fields, say so \
and suggest the closest supported question. Do not guess.
- Resolve relative time expressions against the dataset's last order date \
({meta['max_date']}), NOT today's date. Examples: "last month" = 2025-12-01 to \
{meta['max_date']}; "last 3 months" = 2025-10-01 to {meta['max_date']}.

DATA NOTES
- status values: delivered, delayed, in_transit, exception, canceled.
- "delayed" means the order WAS delivered, but late. "How many orders were \
delivered late?" → count with statuses=["delayed"].
- on_time_rate and delay_rate are computed over completed orders only \
(delivered + delayed); the engine applies that filter automatically.
- avg_delivery_days automatically excludes the 30 orders without a delivery date.
- Carriers: FedEx, UPS, DHL, USPS, OnTrac, LaserShip, Royal Mail, DPD, GLS. \
Regions: US-E, US-W, US-C, EU, UK. Categories: CRAYON, STICKER, MARKER, BRUSH, \
PAINT, PENCIL, PAPER, BOOK.

ANSWER STYLE
- Be concise: lead with the number/answer, then one or two sentences of context.
- A chart is rendered automatically from your tool results — do not describe \
chart appearance or list every row; the user sees the chart and table."""


_QUERY_TOOL = {
    "name": "query_analytics",
    "description": (
        "Run a validated analytics query over the orders dataset. Returns "
        "aggregated rows. Use for counts, rates, averages, sums, breakdowns "
        "and time series. Call once per distinct question; use group_by for "
        "breakdowns ('by carrier', 'by week') and filters for subsets. "
        "delay_rate/on_time_rate with group_by='carrier' answers 'which "
        "carrier has the highest delay rate' (rows are sorted by value desc)."
    ),
    "input_schema": QuerySpec.model_json_schema(),
}

_FORECAST_TOOL = {
    "name": "forecast_demand",
    "description": (
        "Forecast future monthly demand (units = sum of quantity) and get an "
        "inventory recommendation. Use for questions about predicting demand, "
        "future sales, or how much inventory/stock to plan. Forecasts at "
        "product-category level; if the user asks about a specific SKU, pass "
        "the sku field and it is rolled up to its category (per-SKU history "
        "is too sparse — the tool explains this in its output). Returns "
        "historical + forecast series, the recommendation, and methodology — "
        "include the roll-up note, recommendation and methodology in your answer."
    ),
    "input_schema": ForecastSpec.model_json_schema(),
}


def _execute_tool(name: str, tool_input: dict) -> tuple[dict | None, str | None]:
    """Validate and run a tool call. Returns (result, error)."""
    if name == "query_analytics":
        try:
            spec = QuerySpec.model_validate(tool_input)
        except ValidationError as e:
            return None, f"Invalid query spec: {e.error_count()} error(s): {e.errors()[:3]}"
        return run_query(spec), None
    if name == "forecast_demand":
        try:
            fspec = ForecastSpec.model_validate(tool_input)
        except ValidationError as e:
            return None, f"Invalid forecast spec: {e.error_count()} error(s): {e.errors()[:3]}"
        return run_forecast(fspec), None
    return None, f"Unknown tool: {name}"


def answer_question(question: str) -> dict:
    """Full orchestration flow for one NL question.

    Returns {answer, results, error} where results carries each executed
    tool call's rows + explainability payload for the frontend.
    """
    client = _get_client()
    system = _build_system_prompt()
    messages = [{"role": "user", "content": question}]
    results = []

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            response = client.messages.create(
                model=MODEL,
                max_tokens=1000,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                tools=[_QUERY_TOOL, _FORECAST_TOOL],
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                answer = "".join(b.text for b in response.content if b.type == "text")
                return {"answer": answer, "results": results, "error": None}

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result, err = _execute_tool(block.name, block.input)
                if err:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": err,
                        "is_error": True,
                    })
                else:
                    results.append({
                        "tool": block.name,
                        "rows": result["rows"],
                        "explain": result["explain"],
                        "suggested_chart": result["suggested_chart"],
                    })
                    content = str(result["rows"])
                    if result.get("answer_notes"):
                        content += "\nNOTES: " + " | ".join(result["answer_notes"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content,
                    })
            messages.append({"role": "user", "content": tool_results})

        return {
            "answer": "I couldn't complete that within the allowed number of steps. "
                      "Try a simpler or more specific question.",
            "results": results,
            "error": None,
        }

    except anthropic.APIError:
        return {
            "answer": None,
            "results": [],
            "error": "The AI service is temporarily unavailable. "
                     "The dashboard above still works — please try the chat again shortly.",
        }

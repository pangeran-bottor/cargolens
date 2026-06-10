"""Demand forecasting tool.

Deliberately basic per the spec (moving average / linear trend). Forecasts
monthly sum(quantity) — units of demand, not order count or revenue.

Granularity is product_category (8 series of 12 monthly points) or all
categories combined. Per-SKU is NOT supported: 355 distinct SKUs across 400
rows (~1.1 orders each) is no time series at all. SKU requests roll up to
the SKU's category, and the answer says so.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .db import connect

VALID_CATEGORIES = ["BOOK", "BRUSH", "CRAYON", "MARKER", "PAINT", "PAPER", "PENCIL", "STICKER"]


class ForecastSpec(BaseModel):
    product_category: Optional[Literal[
        "BOOK", "BRUSH", "CRAYON", "MARKER", "PAINT", "PAPER", "PENCIL", "STICKER"
    ]] = Field(None, description="Omit to forecast total demand across all categories")
    sku: Optional[str] = Field(
        None, description="If the user asked about a specific SKU, pass it here; "
                          "it is rolled up to its product category")
    horizon_months: int = Field(3, ge=1, le=6)
    method: Literal["moving_average", "linear_trend"] = "moving_average"


def _monthly_series(category: Optional[str]) -> list[dict]:
    sql = "SELECT strftime('%Y-%m', order_date) AS month, SUM(quantity) AS value FROM orders"
    params: list = []
    if category:
        sql += " WHERE product_category = ?"
        params.append(category)
    sql += " GROUP BY month ORDER BY month"
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _sku_category(sku: str) -> Optional[str]:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT product_category FROM orders WHERE sku = ? LIMIT 1", (sku,)
        ).fetchone()
        return row["product_category"] if row else None
    finally:
        conn.close()


def _next_months(last_month: str, n: int) -> list[str]:
    year, month = int(last_month[:4]), int(last_month[5:7])
    out = []
    for _ in range(n):
        month += 1
        if month > 12:
            month, year = 1, year + 1
        out.append(f"{year:04d}-{month:02d}")
    return out


def run_forecast(spec: ForecastSpec) -> dict:
    category = spec.product_category
    sku_note = None
    if spec.sku:
        rolled = _sku_category(spec.sku)
        if rolled is None:
            return {
                "rows": [],
                "explain": {"spec": spec.model_dump(), "error": f"SKU '{spec.sku}' not found"},
                "suggested_chart": "none",
                "answer_notes": [f"SKU '{spec.sku}' does not exist in the dataset."],
            }
        sku_note = (
            f"SKU {spec.sku} has too little history to forecast on its own "
            f"(~1 order per SKU in this dataset), so the forecast is for its "
            f"product category, {rolled}."
        )
        category = rolled

    history = _monthly_series(category)
    values = [r["value"] for r in history]

    if spec.method == "moving_average":
        window = values[-3:]
        level = sum(window) / len(window)
        forecast_values = [round(level)] * spec.horizon_months
        methodology = (
            f"3-month moving average: the mean of the last three months "
            f"({', '.join(str(v) for v in window)}) = {level:.1f} units/month, "
            f"projected flat over the horizon. Chosen for robustness on a short "
            f"(12-point), noisy monthly series."
        )
    else:
        # ordinary least squares over month index
        n = len(values)
        xs = range(n)
        mean_x, mean_y = (n - 1) / 2, sum(values) / n
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / sum(
            (x - mean_x) ** 2 for x in xs
        )
        intercept = mean_y - slope * mean_x
        forecast_values = [
            max(0, round(intercept + slope * (n + i))) for i in range(spec.horizon_months)
        ]
        methodology = (
            f"Linear trend (ordinary least squares) over {n} months of history: "
            f"slope {slope:+.1f} units/month. Simple by design — the dataset is "
            f"one year of monthly aggregates."
        )

    future_months = _next_months(history[-1]["month"], spec.horizon_months)
    rows = [{"month": r["month"], "historical": r["value"], "forecast": None} for r in history]
    rows += [
        {"month": m, "historical": None, "forecast": v}
        for m, v in zip(future_months, forecast_values)
    ]

    # Inventory recommendation: forecast demand + 20% safety stock.
    monthly_demand = forecast_values[0]
    safety = round(monthly_demand * 0.2)
    recommendation = (
        f"Plan inventory of ~{monthly_demand + safety} units/month for "
        f"{category or 'all categories'} (forecast {monthly_demand} units + 20% "
        f"safety stock of {safety}). Formula: forecast monthly demand × 1.2."
    )

    notes = [recommendation, f"Methodology: {methodology}"]
    if sku_note:
        notes.insert(0, sku_note)

    return {
        "rows": rows,
        "explain": {
            "spec": spec.model_dump(),
            "entity": category or "all categories",
            "demand_metric": "sum(quantity) per month",
            "history_months": len(history),
            "forecast_values": dict(zip(future_months, forecast_values)),
            "methodology": methodology,
            "filters_applied": [f"product_category = {category}"] if category else [],
            "implicit_filters": ["demand = sum(quantity), aggregated monthly"],
        },
        "suggested_chart": "forecast",
        "answer_notes": notes,
    }

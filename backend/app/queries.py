"""Deterministic analytics engine.

The only way data is read: a validated QuerySpec is compiled into
parameterized SQL from allow-listed fragments. The LLM never writes SQL;
it can only produce a QuerySpec (Phase 3), and the dashboard endpoints use
the same engine — one computation path for every number shown anywhere.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .db import connect

Metric = Literal[
    "count", "on_time_rate", "delay_rate",
    "avg_delivery_days", "sum_quantity", "sum_order_value",
]
GroupBy = Literal[
    "none", "carrier", "region", "warehouse", "product_category",
    "destination_city", "status", "client_id", "week", "month",
]

# metric → SQL aggregate. on_time/delay rates are defined over COMPLETED
# orders only: delivered / (delivered + delayed). in_transit, exception and
# canceled are excluded — an order still moving is not yet on-time or late.
_METRIC_SQL = {
    "count": "COUNT(*)",
    "sum_quantity": "SUM(quantity)",
    "sum_order_value": "ROUND(SUM(order_value_usd), 2)",
    "avg_delivery_days": "ROUND(AVG(delivery_days), 2)",
    "on_time_rate": (
        "ROUND(CAST(SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS REAL)"
        " / NULLIF(SUM(CASE WHEN status IN ('delivered','delayed') THEN 1 ELSE 0 END), 0), 4)"
    ),
    "delay_rate": (
        "ROUND(CAST(SUM(CASE WHEN status = 'delayed' THEN 1 ELSE 0 END) AS REAL)"
        " / NULLIF(SUM(CASE WHEN status IN ('delivered','delayed') THEN 1 ELSE 0 END), 0), 4)"
    ),
}

# implicit WHERE clauses a metric needs to be correct, surfaced to the user
# in the explainability payload
_METRIC_IMPLICIT = {
    "avg_delivery_days": (
        "delivery_days IS NOT NULL",
        "excludes 30 orders without a delivery date (in_transit/canceled)",
    ),
    "on_time_rate": (
        "status IN ('delivered','delayed')",
        "rate computed over completed orders only",
    ),
    "delay_rate": (
        "status IN ('delivered','delayed')",
        "rate computed over completed orders only",
    ),
}

_GROUP_SQL = {
    "carrier": "carrier",
    "region": "region",
    "warehouse": "warehouse",
    "product_category": "product_category",
    "destination_city": "destination_city",
    "status": "status",
    "client_id": "client_id",
    # ISO-style week starting Monday, expressed as the week's start date
    "week": "date(order_date, 'weekday 0', '-6 days')",
    "month": "strftime('%Y-%m', order_date)",
}


class QueryFilters(BaseModel):
    statuses: Optional[list[Literal["delivered", "delayed", "in_transit", "exception", "canceled"]]] = None
    carriers: Optional[list[str]] = None
    regions: Optional[list[str]] = None
    product_categories: Optional[list[str]] = None
    warehouses: Optional[list[str]] = None
    date_from: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_to: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class QuerySpec(BaseModel):
    metric: Metric
    group_by: GroupBy = "none"
    filters: QueryFilters = Field(default_factory=QueryFilters)
    sort: Literal["asc", "desc", "none"] = "none"
    limit: Optional[int] = Field(None, ge=1, le=100)


def suggested_chart(spec: QuerySpec) -> str:
    if spec.group_by in ("week", "month"):
        return "line"
    if spec.group_by == "none":
        return "number"
    return "bar"


def run_query(spec: QuerySpec) -> dict:
    where, params, applied = [], [], []

    f = spec.filters
    for column, values in [
        ("status", f.statuses), ("carrier", f.carriers), ("region", f.regions),
        ("product_category", f.product_categories), ("warehouse", f.warehouses),
    ]:
        if values:
            where.append(f"{column} IN ({','.join('?' * len(values))})")
            params.extend(values)
            applied.append(f"{column} in {values}")
    if f.date_from:
        where.append("order_date >= ?")
        params.append(f.date_from)
        applied.append(f"order_date >= {f.date_from}")
    if f.date_to:
        where.append("order_date <= ?")
        params.append(f.date_to)
        applied.append(f"order_date <= {f.date_to}")

    implicit = _METRIC_IMPLICIT.get(spec.metric)
    if implicit:
        where.append(implicit[0])

    sql = f"SELECT {_METRIC_SQL[spec.metric]} AS value"
    if spec.group_by != "none":
        sql = f"SELECT {_GROUP_SQL[spec.group_by]} AS {spec.group_by}, {_METRIC_SQL[spec.metric]} AS value"
    sql += " FROM orders"
    if where:
        sql += " WHERE " + " AND ".join(where)
    if spec.group_by != "none":
        sql += f" GROUP BY {_GROUP_SQL[spec.group_by]}"
        # time series sort chronologically; categorical default by value desc
        if spec.group_by in ("week", "month"):
            sql += f" ORDER BY {spec.group_by} ASC"
        elif spec.sort != "none":
            sql += f" ORDER BY value {'ASC' if spec.sort == 'asc' else 'DESC'}"
        else:
            sql += " ORDER BY value DESC"
    if spec.limit:
        sql += f" LIMIT {spec.limit}"

    conn = connect()
    try:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()

    return {
        "rows": rows,
        "explain": {
            "spec": spec.model_dump(),
            "sql": sql,
            "filters_applied": applied,
            "implicit_filters": [implicit[1]] if implicit else [],
        },
        "suggested_chart": suggested_chart(spec),
    }


def dataset_meta() -> dict:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT MIN(order_date) AS min_date, MAX(order_date) AS max_date, COUNT(*) AS total FROM orders"
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def kpis() -> dict:
    """The five required dashboard KPIs, all via the same engine."""
    def value(metric: Metric, statuses: Optional[list] = None):
        spec = QuerySpec(metric=metric, filters=QueryFilters(statuses=statuses))
        return run_query(spec)["rows"][0]["value"]

    return {
        "total_orders": value("count"),
        "delivered_orders": value("count", ["delivered"]),
        "delayed_orders": value("count", ["delayed"]),
        "on_time_rate": value("on_time_rate"),
        "avg_delivery_days": value("avg_delivery_days"),
    }

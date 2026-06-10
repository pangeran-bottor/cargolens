"""Engine correctness tests.

Expected values are recomputed here directly from the raw CSV with stdlib
code — an independent computation path from the SQL engine — so a shared
bug can't make a wrong number pass.
"""

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import pytest

from app.queries import QueryFilters, QuerySpec, kpis, run_query
from app.seed import DATA_CSV, seed


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    seed()


@pytest.fixture(scope="session")
def raw():
    with open(DATA_CSV, newline="") as f:
        return list(csv.DictReader(f))


def test_kpis_match_csv(raw):
    completed = [r for r in raw if r["status"] in ("delivered", "delayed")]
    delivered = [r for r in raw if r["status"] == "delivered"]
    with_dd = [r for r in raw if r["delivery_date"].strip()]
    expected_avg = sum(
        (date.fromisoformat(r["delivery_date"]) - date.fromisoformat(r["order_date"])).days
        for r in with_dd
    ) / len(with_dd)

    k = kpis()
    assert k["total_orders"] == len(raw)
    assert k["delivered_orders"] == len(delivered)
    assert k["delayed_orders"] == sum(1 for r in raw if r["status"] == "delayed")
    assert k["on_time_rate"] == round(len(delivered) / len(completed), 4)
    assert k["avg_delivery_days"] == round(expected_avg, 2)


def test_count_by_carrier(raw):
    expected = Counter(r["carrier"] for r in raw)
    res = run_query(QuerySpec(metric="count", group_by="carrier"))
    got = {r["carrier"]: r["value"] for r in res["rows"]}
    assert got == dict(expected)


def test_delay_rate_by_carrier(raw):
    by_carrier = defaultdict(lambda: [0, 0])  # [delayed, completed]
    for r in raw:
        if r["status"] in ("delivered", "delayed"):
            by_carrier[r["carrier"]][1] += 1
            if r["status"] == "delayed":
                by_carrier[r["carrier"]][0] += 1
    expected = {c: round(d / t, 4) for c, (d, t) in by_carrier.items()}

    res = run_query(QuerySpec(metric="delay_rate", group_by="carrier"))
    got = {r["carrier"]: r["value"] for r in res["rows"]}
    assert got == expected
    # categorical default sort is value DESC → first row is the answer to
    # "which carrier has the highest delay rate?"
    top = max(expected, key=expected.get)
    assert res["rows"][0]["carrier"] == top


def test_date_window_filter(raw):
    # spec example resolved against dataset max date 2025-12-30:
    # "delayed orders ... last 3 months" → 2025-10-01..2025-12-30 (see Phase 3)
    expected = sum(
        1 for r in raw
        if r["status"] == "delayed" and "2025-10-01" <= r["order_date"] <= "2025-12-30"
    )
    res = run_query(QuerySpec(
        metric="count",
        filters=QueryFilters(statuses=["delayed"], date_from="2025-10-01", date_to="2025-12-30"),
    ))
    assert res["rows"][0]["value"] == expected


def test_weekly_grouping_covers_all_rows(raw):
    res = run_query(QuerySpec(metric="count", group_by="week"))
    assert sum(r["value"] for r in res["rows"]) == len(raw)
    # week keys are the week's Monday, chronological
    weeks = [r["week"] for r in res["rows"]]
    assert weeks == sorted(weeks)
    assert all(date.fromisoformat(w).weekday() == 0 for w in weeks)


def test_sum_quantity_by_category(raw):
    expected = defaultdict(int)
    for r in raw:
        expected[r["product_category"]] += int(r["quantity"])
    res = run_query(QuerySpec(metric="sum_quantity", group_by="product_category"))
    got = {r["product_category"]: r["value"] for r in res["rows"]}
    assert got == dict(expected)


def test_explainability_payload_present():
    res = run_query(QuerySpec(metric="avg_delivery_days"))
    assert "sql" in res["explain"]
    assert res["explain"]["implicit_filters"], "implicit exclusion must be surfaced"
    assert res["suggested_chart"] == "number"

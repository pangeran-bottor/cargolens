"""Forecast correctness tests — expectations recomputed from the raw CSV."""

import csv
from collections import defaultdict

import pytest

from app.forecast import ForecastSpec, run_forecast
from app.seed import DATA_CSV, seed


@pytest.fixture(scope="module", autouse=True)
def seeded_db():
    seed()


@pytest.fixture(scope="module")
def monthly_by_category():
    series = defaultdict(lambda: defaultdict(int))
    with open(DATA_CSV, newline="") as f:
        for r in csv.DictReader(f):
            series[r["product_category"]][r["order_date"][:7]] += int(r["quantity"])
    return series


def test_moving_average_matches_hand_computation(monthly_by_category):
    months = sorted(monthly_by_category["CRAYON"])
    last3 = [monthly_by_category["CRAYON"][m] for m in months[-3:]]
    expected = round(sum(last3) / 3)

    res = run_forecast(ForecastSpec(product_category="CRAYON", horizon_months=3))
    forecast_rows = [r for r in res["rows"] if r["forecast"] is not None]
    assert len(forecast_rows) == 3
    assert all(r["forecast"] == expected for r in forecast_rows)
    assert forecast_rows[0]["month"] == "2026-01"
    assert res["suggested_chart"] == "forecast"


def test_history_matches_csv(monthly_by_category):
    res = run_forecast(ForecastSpec(product_category="PAPER"))
    hist = {r["month"]: r["historical"] for r in res["rows"] if r["historical"] is not None}
    assert hist == dict(monthly_by_category["PAPER"])
    assert len(hist) == 12


def test_linear_trend_is_finite_and_nonnegative():
    res = run_forecast(ForecastSpec(method="linear_trend", horizon_months=4))
    forecast_rows = [r for r in res["rows"] if r["forecast"] is not None]
    assert len(forecast_rows) == 4
    assert all(r["forecast"] >= 0 for r in forecast_rows)
    assert "slope" in res["explain"]["methodology"]


def test_sku_rolls_up_to_category_with_visible_note(monthly_by_category):
    # grab a real SKU from the CSV
    with open(DATA_CSV, newline="") as f:
        row = next(csv.DictReader(f))
    res = run_forecast(ForecastSpec(sku=row["sku"]))
    assert res["explain"]["entity"] == row["product_category"]
    # the roll-up explanation must be in the answer notes shown to the user
    assert any(row["sku"] in n and row["product_category"] in n for n in res["answer_notes"])


def test_unknown_sku_returns_clear_error():
    res = run_forecast(ForecastSpec(sku="DOES-NOT-EXIST"))
    assert res["rows"] == []
    assert "not exist" in res["answer_notes"][0] or "not found" in str(res["explain"])


def test_inventory_recommendation_present():
    res = run_forecast(ForecastSpec(product_category="BOOK"))
    rec = res["answer_notes"][0]
    assert "safety stock" in rec and "units" in rec

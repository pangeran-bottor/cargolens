"""Live orchestration tests against the real Anthropic API.

Run the spec's three example questions end-to-end and assert the answers
contain the values the deterministic engine computes. Skipped automatically
when ANTHROPIC_API_KEY is not set (CI without secrets, reviewers).

Cost: ~6 small Sonnet calls per run.
"""

import os

import pytest

from app.orchestrator import answer_question
from app.queries import QueryFilters, QuerySpec, run_query
from app.seed import seed

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set"
)


@pytest.fixture(scope="module", autouse=True)
def seeded_db():
    seed()


def test_delayed_orders_by_week_last_3_months():
    res = answer_question("Show delayed orders by week for the last 3 months")
    assert res["error"] is None
    assert res["results"], "expected at least one tool call"
    explain = res["results"][0]["explain"]
    spec = explain["spec"]
    # must be a delayed-status weekly count anchored to the dataset, not today
    assert spec["filters"]["statuses"] == ["delayed"]
    assert spec["group_by"] == "week"
    assert spec["filters"]["date_from"] >= "2025-09-25"
    assert res["results"][0]["suggested_chart"] == "line"


def test_highest_delay_rate_carrier():
    # ground truth from the deterministic engine
    truth = run_query(QuerySpec(metric="delay_rate", group_by="carrier"))
    top_carrier = truth["rows"][0]["carrier"]

    res = answer_question("Which carrier has the highest delay rate?")
    assert res["error"] is None
    assert res["results"]
    assert top_carrier in res["answer"]


def test_orders_delivered_late_last_month():
    truth = run_query(QuerySpec(
        metric="count",
        filters=QueryFilters(statuses=["delayed"], date_from="2025-12-01", date_to="2025-12-31"),
    ))
    expected = truth["rows"][0]["value"]

    res = answer_question("How many orders were delivered late last month?")
    assert res["error"] is None
    assert res["results"]
    assert str(expected) in res["answer"]


def test_unanswerable_question_refuses_gracefully():
    res = answer_question("What is the CEO's email address?")
    assert res["error"] is None
    # must not hallucinate an answer; should explain it can't answer from the data
    assert res["answer"]

import pandas as pd

from database.stock_master_reader import get_active_stocks
from service.screening_service import (
    format_reason,
    get_large_cap_stocks,
    get_prime_stocks,
    get_today_candidates,
)


def test_get_large_cap_stocks_returns_core30_and_large70_only():
    stocks = get_large_cap_stocks()

    assert len(stocks) > 0
    assert set(stocks["size_class"].unique()).issubset(
        {"TOPIX Core30", "TOPIX Large70"}
    )


def test_get_prime_stocks_returns_prime_market_only():
    stocks = get_prime_stocks()

    assert len(stocks) > 0
    assert set(stocks["market"].unique()) == {"プライム（内国株式）"}


def test_get_today_candidates_runs_on_a_small_universe():
    stocks = get_active_stocks().head(3)

    candidates = get_today_candidates(direction="long", stocks=stocks)

    assert isinstance(candidates, list)

    for candidate in candidates:
        assert candidate["is_entry_candidate"] is True
        assert "code" in candidate
        assert "company_name" in candidate


def test_candidates_are_sorted_by_score_descending():
    stocks = get_active_stocks().head(10)

    candidates = get_today_candidates(direction="long", stocks=stocks)

    scores = [c["score"]["total_score"] for c in candidates]

    assert scores == sorted(scores, reverse=True)


def test_format_reason_pattern_a():
    candidate = {"pattern": "A", "bounce_number": 1}

    assert format_reason(candidate) == "支持線/抵抗線付近の半分シグナル（反発1回目）"


def test_format_reason_pattern_b():
    candidate = {"pattern": "B", "bounce_number": 2}

    assert format_reason(candidate) == "20日線付近の半分シグナル（反発2回目）"

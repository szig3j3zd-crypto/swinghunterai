import pandas as pd

from backtest.simulator import run_backtest, simulate_trade


def _df(rows):

    """
    rows: [(high, low, close), ...] のリストからDataFrameを作る
    """

    highs = [row[0] for row in rows]
    lows = [row[1] for row in rows]
    closes = [row[2] for row in rows]

    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=len(rows), freq="D"),
        "high": highs,
        "low": lows,
        "close": closes,
    })


def test_take_profit_hit_before_stop_loss():
    df = _df([
        (100, 100, 100),  # entry day
        (105, 95, 100),   # 何もヒットしない
        (125, 115, 120),  # 利確ライン120にヒット
    ])

    result = simulate_trade(
        df, entry_index=0, direction="long",
        stop_loss_price=90, take_profit_price=120, max_holding_days=10,
    )

    assert result["exit_reason"] == "take_profit"
    assert result["exit_price"] == 120
    assert result["exit_index"] == 2
    assert result["days_held"] == 2
    assert result["return_pct"] == 0.2


def test_stop_loss_hit():
    df = _df([
        (100, 100, 100),  # entry day
        (100, 85, 90),    # 損切ライン90にヒット
    ])

    result = simulate_trade(
        df, entry_index=0, direction="long",
        stop_loss_price=90, take_profit_price=120, max_holding_days=10,
    )

    assert result["exit_reason"] == "stop_loss"
    assert result["exit_price"] == 90
    assert result["days_held"] == 1
    assert round(result["return_pct"], 4) == -0.1


def test_stop_loss_wins_when_both_hit_same_day():
    df = _df([
        (100, 100, 100),  # entry day
        (125, 85, 100),   # 高値125(利確条件)・安値85(損切条件)両方満たす
    ])

    result = simulate_trade(
        df, entry_index=0, direction="long",
        stop_loss_price=90, take_profit_price=120, max_holding_days=10,
    )

    assert result["exit_reason"] == "stop_loss"


def test_timeout_when_neither_hit_within_holding_period():
    df = _df([
        (100, 100, 100),
        (105, 95, 102),
        (105, 95, 103),
        (105, 95, 104),
    ])

    result = simulate_trade(
        df, entry_index=0, direction="long",
        stop_loss_price=90, take_profit_price=120, max_holding_days=3,
    )

    assert result["exit_reason"] == "timeout"
    assert result["exit_index"] == 3
    assert result["exit_price"] == 104
    assert result["days_held"] == 3


def test_data_ended_before_holding_period_or_exit_condition():
    df = _df([
        (100, 100, 100),
        (105, 95, 102),
    ])

    result = simulate_trade(
        df, entry_index=0, direction="long",
        stop_loss_price=90, take_profit_price=120, max_holding_days=10,
    )

    assert result["exit_reason"] == "data_ended"
    assert result["exit_index"] == 1


def _golden_cross_df():

    """
    2営業日目に完全ゴールデンクロスが発生するDataFrame（run_backtest用）。
    株価はconfig既定の価格フィルタ(1000〜5000円)内に収める
    """

    length = 4
    close = [1800.0, 2000.0, 2010.0, 2020.0]

    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=length, freq="D"),
        "open": close,
        "high": [c + 10 for c in close],
        "low": [c - 10 for c in close],
        "close": close,
        "volume": [600_000] * length,
        "volume_ratio": [2.5] * length,
        "sma5": [1800, 2000, 2010, 2020],
        "sma20": [1840, 1900, 1920, 1940],
        "sma60": [1400, 1420, 1440, 1460],
    })


def test_run_backtest_uses_the_given_modules():
    df = _golden_cross_df()

    trades = run_backtest(
        df, direction="long", min_history=1,
        modules=["ma_order", "perfect_golden_cross"],
    )

    assert len(trades) == 1
    assert trades[0]["modules"] == ["ma_order", "perfect_golden_cross"]


def test_run_backtest_finds_nothing_when_modules_dont_match():
    df = _golden_cross_df()

    trades = run_backtest(df, direction="long", min_history=1, modules=["bounce"])

    assert trades == []


def test_short_direction_stop_and_target_are_mirrored():
    df = _df([
        (100, 100, 100),  # entry day
        (95, 75, 80),     # 安値75で利確ライン80にヒット
    ])

    result = simulate_trade(
        df, entry_index=0, direction="short",
        stop_loss_price=110, take_profit_price=80, max_holding_days=10,
    )

    assert result["exit_reason"] == "take_profit"
    assert result["exit_price"] == 80
    assert round(result["return_pct"], 4) == 0.2

import pandas as pd

from backtest.simulator import simulate_trade


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

import pandas as pd
import pytest

from rules.entry_rule import evaluate_entry

# テスト用の合成株価（数十〜数百円台）はconfig.MIN_PRICE/MAX_PRICEの
# デフォルト範囲（1000〜5000円）外のため、価格フィルタを検証する目的の
# テスト以外では明示的に無効化する
NO_PRICE_FILTER = {"min_price": 0, "max_price": float("inf")}


def _base_df(sma5, sma20, sma60=None, close=None):
    length = len(sma5)
    close = close if close is not None else list(sma20)

    data = {
        "date": pd.date_range("2026-01-01", periods=length, freq="D"),
        "open": close,
        "high": [c + 1 for c in close],
        "low": [c - 1 for c in close],
        "close": close,
        "volume": [600_000] * length,
        "volume_ratio": [2.5] * length,
        "sma5": sma5,
        "sma20": sma20,
    }

    if sma60 is not None:
        data["sma60"] = sma60

    return pd.DataFrame(data)


def test_ma_order_and_perfect_golden_cross_combo_is_candidate():
    df = _base_df(
        sma5=[90, 100],
        sma20=[92, 95],
        sma60=[70, 71],
        close=[90.0, 100.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order", "perfect_golden_cross"],
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is True
    assert result["modules"] == ["ma_order", "perfect_golden_cross"]
    assert result["bounce_number"] is None


def test_combination_and_fails_when_one_module_is_false():
    # ma_orderは満たすが、直近日にゴールデンクロスは発生していない
    df = _base_df(
        sma5=[90, 91],
        sma20=[80, 81],
        sma60=[70, 70.5],
        close=[90.0, 91.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order", "perfect_golden_cross"],
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "no_signal_today"


def test_two_line_mode_skips_sma60_filter():
    # sma60は並び順を崩しているが、two_lineモードでは60日線を見ないため候補になる
    df = _base_df(
        sma5=[10, 15],
        sma20=[8, 12],
        sma60=[20, 20],
        close=[10.0, 15.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order"], ma_mode="two_line",
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is True


def test_ma_order_full_mode_rejects_when_below_sma60():
    df = _base_df(
        sma5=[10, 15],
        sma20=[8, 12],
        sma60=[20, 20.1],
        close=[10.0, 15.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["ma_order"], ma_mode="full",
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "not_in_trend"


def test_bounce_module_alone_returns_watch_candidate():
    # MA20を少し下回った日（回復前）は監視銘柄として扱う
    df = _base_df(
        sma5=[110, 107, 104, 101.5, 102.0],
        sma20=[100.0, 100.4, 100.8, 101.2, 102.2],
    )

    result = evaluate_entry(df, direction="long", modules=["bounce"], **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is False
    assert result["is_watch_candidate"] is True


def test_bounce_module_alone_promotes_to_candidate_on_recovery_day():
    df = _base_df(
        sma5=[110, 107, 104, 101.5, 102.0, 103.0],
        sma20=[100.0, 100.4, 100.8, 101.2, 102.2, 102.6],
    )

    result = evaluate_entry(df, direction="long", modules=["bounce"], **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is True
    assert result["is_watch_candidate"] is False
    assert result["bounce_number"] == 1


def test_bounce_module_alone_returns_watch_candidate_for_short():
    # ショート版: MA5がMA20を少し上回った日（回復前）は監視銘柄として扱う
    df = _base_df(
        sma5=[90, 93, 96, 98.5, 98.0],
        sma20=[100.0, 99.6, 99.2, 98.8, 97.8],
    )

    result = evaluate_entry(df, direction="short", modules=["bounce"], **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is False
    assert result["is_watch_candidate"] is True
    assert result["reason"] == "bounce_above_ma20_watch"


def test_half_signal_module_alone_is_candidate():
    df = _base_df(
        sma5=[100, 100],
        sma20=[90, 90],
        close=[95.0, 105.0],
    )
    df["open"] = [95.0, 105.0]

    result = evaluate_entry(df, direction="long", modules=["half_signal"], **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is True


def test_parallel_rise_module_alone_is_candidate():
    df = _base_df(
        sma5=[9.0, 9.8, 10.6, 11.0, 11.5],
        sma20=[10.0, 10.2, 10.5, 10.8, 11.1],
        close=[9.0, 9.8, 10.6, 11.0, 11.5],
    )

    result = evaluate_entry(df, direction="long", modules=["parallel_rise"], **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is True


def test_skipped_when_volume_too_low():
    df = _base_df(
        sma5=[90, 100],
        sma20=[92, 95],
        sma60=[70, 71],
        close=[90.0, 100.0],
    )
    df.loc[df.index[-1], "volume"] = 100

    result = evaluate_entry(df, direction="long", modules=["ma_order", "perfect_golden_cross"])

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "volume_too_low"


def test_short_perfect_dead_cross_is_candidate():
    df = _base_df(
        sma5=[110, 100],
        sma20=[108, 105],
        sma60=[120, 118],
        close=[110.0, 100.0],
    )

    result = evaluate_entry(
        df, direction="short", modules=["ma_order", "perfect_golden_cross"],
        **NO_PRICE_FILTER,
    )

    assert result["is_entry_candidate"] is True


def test_golden_cross_module_fires_even_when_ma20_is_declining():
    # 完全ゴールデンクロスと違い、MA20が下降中のクロスも候補にする
    df = _base_df(
        sma5=[90, 96],
        sma20=[100, 95],
        close=[90.0, 96.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["golden_cross"], **NO_PRICE_FILTER
    )

    assert result["is_entry_candidate"] is True


def test_perfect_golden_cross_does_not_fire_when_ma20_is_declining():
    # 同じデータでも、完全ゴールデンクロス（MA20上向き必須）は候補にならない
    df = _base_df(
        sma5=[90, 96],
        sma20=[100, 95],
        close=[90.0, 96.0],
    )

    result = evaluate_entry(
        df, direction="long", modules=["perfect_golden_cross"], **NO_PRICE_FILTER
    )

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "no_signal_today"


def test_golden_cross_module_short_fires_even_when_ma20_is_rising():
    df = _base_df(
        sma5=[110, 94],
        sma20=[100, 105],
        close=[110.0, 94.0],
    )

    result = evaluate_entry(
        df, direction="short", modules=["golden_cross"], **NO_PRICE_FILTER
    )

    assert result["is_entry_candidate"] is True


def test_empty_modules_raises():
    df = _base_df(sma5=[100], sma20=[90])

    with pytest.raises(ValueError):
        evaluate_entry(df, direction="long", modules=[], **NO_PRICE_FILTER)


def test_unknown_module_raises():
    df = _base_df(sma5=[100], sma20=[90])

    with pytest.raises(ValueError):
        evaluate_entry(df, direction="long", modules=["not_a_real_module"], **NO_PRICE_FILTER)

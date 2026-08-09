import pandas as pd

from rules.entry_rule import evaluate_entry

# テスト用の合成株価（数十〜数百円台）はconfig.MIN_PRICE/MAX_PRICEの
# デフォルト範囲（1000〜5000円）外のため、価格フィルタを検証する目的の
# テスト以外では明示的に無効化する
NO_PRICE_FILTER = {"min_price": 0, "max_price": float("inf")}


def _build_long_trend_df(length, spike_positions):

    """
    上昇トレンド（5>20>60、全て右肩上がり）を満たすDataFrameを作る。
    spike_positionsで指定した行だけ実体中央値が5日線を上抜けるようにする。
    """

    sma5 = [50 + 3 * i for i in range(length)]
    sma20 = [40 + 2 * i for i in range(length)]
    sma60 = [30 + i for i in range(length)]

    close = [float(sma20[i]) for i in range(length)]

    for pos in spike_positions:
        close[pos] = sma5[pos] + 5

    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=length, freq="D"),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": [600_000] * length,
        "volume_ratio": [2.5] * length,
        "sma5": sma5,
        "sma20": sma20,
        "sma60": sma60,
    })


def _build_short_trend_df(length, spike_positions):

    """
    下降トレンド（60>20>5、全て右肩下がり）を満たすDataFrameを作る。
    spike_positionsで指定した行だけ実体中央値が5日線を下抜けるようにする。
    """

    sma5 = [150 - 3 * i for i in range(length)]
    sma20 = [160 - 2 * i for i in range(length)]
    sma60 = [170 - i for i in range(length)]

    close = [float(sma20[i]) for i in range(length)]

    for pos in spike_positions:
        close[pos] = sma5[pos] - 5

    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=length, freq="D"),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": [600_000] * length,
        "volume_ratio": [2.5] * length,
        "sma5": sma5,
        "sma20": sma20,
        "sma60": sma60,
    })


def _build_golden_cross_df(direction):

    """
    5日線・20日線のクロス（パターンB）が直近日にちょうど発生し、
    かつ直近日がトレンド条件（並び順・全MA上向き/下向き）を満たすDataFrameを作る。
    """

    if direction == "long":
        sma5 = [90, 100]
        sma20 = [92, 95]
        sma60 = [80, 82]
        close = [90.0, 100.0]
    else:
        sma5 = [110, 100]
        sma20 = [108, 105]
        sma60 = [120, 118]
        close = [110.0, 100.0]

    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=2, freq="D"),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "volume": [600_000] * 2,
        "volume_ratio": [2.5] * 2,
        "sma5": sma5,
        "sma20": sma20,
        "sma60": sma60,
    })


def test_first_bounce_is_entry_candidate():
    df = _build_golden_cross_df("long")

    result = evaluate_entry(df, direction="long", **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is True
    assert result["pattern"] == "B"
    assert result["bounce_number"] == 1
    assert result["score"]["ma_score"] == 40  # 1発目
    assert result["score"]["volume_score"] == 40  # volume_ratio=2.5


def test_second_bounce_is_entry_candidate():
    # パターンB（5-20日線ゴールデンクロス）はクロスの度にトレンド期間が
    # リセットされるため、複数回の反発はパターンA（支持線付近）で検証する
    df = _build_long_trend_df(16, spike_positions=[3, 15])
    support_lines = [{"price": 1, "valid_since_date": df["date"].iloc[0]}]

    result = evaluate_entry(
        df, direction="long", support_lines=support_lines, **NO_PRICE_FILTER
    )

    assert result["is_entry_candidate"] is True
    assert result["pattern"] == "A"
    assert result["bounce_number"] == 2
    assert result["score"]["ma_score"] == 20  # 2発目


def test_third_bounce_exceeds_limit():
    df = _build_long_trend_df(28, spike_positions=[3, 15, 27])
    support_lines = [{"price": 1, "valid_since_date": df["date"].iloc[0]}]

    result = evaluate_entry(
        df, direction="long", support_lines=support_lines, **NO_PRICE_FILTER
    )

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "bounce_limit_exceeded"


def test_skipped_when_not_in_trend():
    df = _build_long_trend_df(4, spike_positions=[3])
    df.loc[df.index[-1], "sma5"] = 10  # 直近日で並び順が崩れる

    result = evaluate_entry(df, direction="long", **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "not_in_trend"


def test_skipped_when_no_half_signal_today():
    df = _build_long_trend_df(5, spike_positions=[])

    result = evaluate_entry(df, direction="long", **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "no_half_signal_today"


def test_skipped_when_volume_too_low():
    df = _build_long_trend_df(4, spike_positions=[3])
    df.loc[df.index[-1], "volume"] = 100

    result = evaluate_entry(df, direction="long")

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "volume_too_low"


def test_short_first_bounce_is_entry_candidate():
    df = _build_golden_cross_df("short")

    result = evaluate_entry(df, direction="short", **NO_PRICE_FILTER)

    assert result["is_entry_candidate"] is True
    assert result["pattern"] == "B"
    assert result["bounce_number"] == 1



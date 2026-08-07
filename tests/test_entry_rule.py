import pandas as pd

from rules.entry_rule import evaluate_entry


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


def test_first_bounce_is_entry_candidate():
    df = _build_long_trend_df(4, spike_positions=[3])

    result = evaluate_entry(df, direction="long")

    assert result["is_entry_candidate"] is True
    assert result["pattern"] == "B"
    assert result["bounce_number"] == 1
    assert result["score"]["ma_score"] == 40  # 1発目
    assert result["score"]["volume_score"] == 40  # volume_ratio=2.5


def test_second_bounce_is_entry_candidate():
    df = _build_long_trend_df(16, spike_positions=[3, 15])

    result = evaluate_entry(df, direction="long")

    assert result["is_entry_candidate"] is True
    assert result["bounce_number"] == 2
    assert result["score"]["ma_score"] == 20  # 2発目


def test_third_bounce_exceeds_limit():
    df = _build_long_trend_df(28, spike_positions=[3, 15, 27])

    result = evaluate_entry(df, direction="long")

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "bounce_limit_exceeded"


def test_skipped_when_not_in_trend():
    df = _build_long_trend_df(4, spike_positions=[3])
    df.loc[df.index[-1], "sma5"] = 10  # 直近日で並び順が崩れる

    result = evaluate_entry(df, direction="long")

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "not_in_trend"


def test_skipped_when_no_half_signal_today():
    df = _build_long_trend_df(5, spike_positions=[])

    result = evaluate_entry(df, direction="long")

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "no_half_signal_today"


def test_skipped_when_volume_too_low():
    df = _build_long_trend_df(4, spike_positions=[3])
    df.loc[df.index[-1], "volume"] = 100

    result = evaluate_entry(df, direction="long")

    assert result["is_entry_candidate"] is False
    assert result["reason"] == "volume_too_low"


def test_short_first_bounce_is_entry_candidate():
    df = _build_short_trend_df(4, spike_positions=[3])

    result = evaluate_entry(df, direction="short")

    assert result["is_entry_candidate"] is True
    assert result["pattern"] == "B"
    assert result["bounce_number"] == 1



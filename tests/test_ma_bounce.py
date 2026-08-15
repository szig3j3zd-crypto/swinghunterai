import pandas as pd

from analysis.ma_bounce import detect_bounce


def _df(sma5, sma20, sma100=None, close=None):
    length = len(sma5)
    close = close if close is not None else list(sma5)

    if sma100 is None:
        # デフォルトはcloseより十分低く、単調増加（MA100上昇トレンド条件を
        # 常に満たす）のダミー値。MA100の条件だけを検証したいテストでは上書きする
        sma100 = [50 + i for i in range(length)]

    return pd.DataFrame({"sma5": sma5, "sma20": sma20, "sma100": sma100, "close": close})


def test_case1_no_undershoot_reversal_is_candidate():
    # sma5がsma20を下回らずに反発するケース（3営業日以上の下落継続後に反転）
    df = _df(
        sma5=[110, 107, 104, 101.5, 103.0],
        sma20=[100.0, 100.4, 100.8, 101.2, 102.2],
    )

    result = detect_bounce(df, direction="long")

    assert list(result["bounce_candidate"]) == [False, False, False, False, True]
    # 監視銘柄はMA100上昇トレンド＋MA5-MA20接近（1%以内）で判定するため、
    # 接近し始めたindex3以降（反転日index4も含む）はすべて監視銘柄になる
    assert list(result["bounce_watch"]) == [False, False, False, True, True]


def test_case2_undershoot_recovers_within_window():
    # sma5がsma20を少し下回ってから、翌営業日に回復するケース
    df = _df(
        sma5=[110, 107, 104, 101.5, 102.0, 103.0],
        sma20=[100.0, 100.4, 100.8, 101.2, 102.2, 102.6],
    )

    result = detect_bounce(df, direction="long")

    assert list(result["bounce_candidate"]) == [False, False, False, False, False, True]
    assert list(result["bounce_watch"]) == [False, False, False, True, True, True]


def test_case2_undershoot_without_recovery_stays_watch_only():
    # sma5がsma20を下回った後、乖離が広がってしまい反発不成立になるケース
    df = _df(
        sma5=[110, 107, 104, 101.5, 102.0, 95.0],
        sma20=[100.0, 100.4, 100.8, 101.2, 102.2, 102.6],
    )

    result = detect_bounce(df, direction="long")

    assert list(result["bounce_candidate"]) == [False, False, False, False, False, False]
    # 最終日は乖離が7%超に広がるため、MA100上昇トレンド中でも監視銘柄からは外れる
    assert list(result["bounce_watch"]) == [False, False, False, True, True, False]


def test_short_case1_no_overshoot_reversal_is_candidate():
    # ショート版: sma5がsma20を上回らずに反発する（下落トレンドへの反転）
    df = _df(
        sma5=[90, 93, 96, 98.5, 97.0],
        sma20=[100.0, 99.6, 99.2, 98.8, 97.8],
        sma100=[150, 149, 148, 147, 146],
    )

    result = detect_bounce(df, direction="short")

    assert list(result["bounce_candidate"]) == [False, False, False, False, True]
    assert list(result["bounce_watch"]) == [False, False, False, True, True]


def test_short_case2_overshoot_recovers_within_window():
    # ショート版: sma5がsma20を少し上回ってから、翌営業日に回復(下回る)するケース
    df = _df(
        sma5=[90, 93, 96, 98.5, 98.0, 97.0],
        sma20=[100.0, 99.6, 99.2, 98.8, 97.8, 97.4],
        sma100=[150, 149, 148, 147, 146, 145],
    )

    result = detect_bounce(df, direction="short")

    assert list(result["bounce_candidate"]) == [False, False, False, False, False, True]
    assert list(result["bounce_watch"]) == [False, False, False, True, True, True]


def test_no_trigger_when_precondition_not_met():
    # 下落継続が2営業日しかないため、候補（反転イベント）の前提条件を満たさない
    df = _df(
        sma5=[110, 107, 104, 106.0],
        sma20=[100.0, 100.4, 100.8, 101.2],
    )

    result = detect_bounce(df, direction="long")

    assert not result["bounce_candidate"].any()
    # 乖離率も最終日まで1%を超えたままのため監視銘柄にもならない
    assert not result["bounce_watch"].any()


def test_watch_ignores_decline_day_count_and_reversal_timing():
    # 監視銘柄は「反発の反転イベント」の前提条件（下落3営業日以上など）を問わない。
    # 下落が1日しかなくても、MA100上昇トレンド中でMA5・MA20が近ければ監視銘柄になる
    df = _df(
        sma5=[100.0, 99.0],
        sma20=[95.0, 98.8],
    )

    result = detect_bounce(df, direction="long")

    assert list(result["bounce_candidate"]) == [False, False]
    assert list(result["bounce_watch"]) == [False, True]


def test_watch_false_when_ma100_is_flat_or_declining():
    # MA5・MA20は接近しているが、MA100が上昇トレンドでない（横ばい）場合は
    # 監視銘柄にならない
    df = _df(
        sma5=[100.0, 99.0],
        sma20=[95.0, 98.8],
        sma100=[80.0, 80.0],
    )

    result = detect_bounce(df, direction="long")

    assert list(result["bounce_watch"]) == [False, False]


def test_watch_false_when_price_below_ma100():
    # MA100自体は上向きでも、終値がMA100を下回っていれば
    # 「MA100上昇トレンド中」とはみなさず監視銘柄にしない
    df = _df(
        sma5=[100.0, 99.0],
        sma20=[95.0, 98.8],
        sma100=[80.0, 200.0],
    )

    result = detect_bounce(df, direction="long")

    assert list(result["bounce_watch"]) == [False, False]


def test_watch_false_when_gap_too_wide():
    # MA100上昇トレンド中でも、MA5とMA20の乖離が1%を超えていれば監視銘柄にしない
    df = _df(
        sma5=[100.0, 110.0],
        sma20=[95.0, 95.0],
    )

    result = detect_bounce(df, direction="long")

    assert list(result["bounce_watch"]) == [False, False]


def test_short_watch_true_when_ma100_downtrend_and_gap_small():
    # ショート版: MA100が下降トレンドで終値がMA100を下回っていればMA100条件を満たす
    df = _df(
        sma5=[90.0, 99.0],
        sma20=[95.0, 99.2],
        sma100=[120.0, 110.0],
    )

    result = detect_bounce(df, direction="short")

    assert list(result["bounce_watch"]) == [False, True]

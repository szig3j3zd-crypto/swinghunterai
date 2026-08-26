import pandas as pd

from analysis.ma_cross_watch import detect_ma_cross_watch, detect_ma_order_watch


def _df(sma60, sma100):
    length = len(sma60)

    return pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=length, freq="D"),
        "sma60": sma60,
        "sma100": sma100,
    })


def _order_df(**columns):
    length = len(next(iter(columns.values())))
    data = {"date": pd.date_range("2026-01-01", periods=length, freq="D")}
    data.update(columns)

    return pd.DataFrame(data)


def test_long_before_cross_within_proximity_is_watch():
    # sma100は単調増加（上昇トレンド）、sma60はsma100の0.5%下を推移（接近中）
    sma100 = [100, 101, 102, 103, 104]
    sma60 = [99.5, 100.5, 101.5, 102.5, 103.5]

    result = detect_ma_cross_watch(_df(sma60, sma100), direction="long")

    assert bool(result["cross_watch"].iloc[-1]) is True
    assert bool(result["before_cross"].iloc[-1]) is True
    assert bool(result["after_cross"].iloc[-1]) is False


def test_long_far_below_is_not_watch():
    # sma60がsma100から大きく（10%以上）乖離しているため接近中とはみなさない
    sma100 = [100, 101, 102, 103, 104]
    sma60 = [80, 81, 82, 83, 84]

    result = detect_ma_cross_watch(_df(sma60, sma100), direction="long")

    assert bool(result["cross_watch"].iloc[-1]) is False


def test_long_after_cross_within_watch_days_is_watch():
    sma100 = [100, 101, 102, 103, 104, 105, 106]
    # day3でsma60がsma100を下から上に突き抜け、以降も1%以内を維持する
    sma60 = [99.5, 100.3, 101.2, 103.5, 104.3, 105.2, 106.4]

    result = detect_ma_cross_watch(
        _df(sma60, sma100), direction="long", watch_days=3,
    )

    assert bool(result["cross_watch"].iloc[-1]) is True
    assert bool(result["after_cross"].iloc[-1]) is True
    assert bool(result["before_cross"].iloc[-1]) is False


def test_long_after_cross_beyond_proximity_is_not_watch():
    # クロス後に乖離が1%を超えて広がった場合は監視対象から外れる
    # （day3でクロス、day6には乖離が約1.9%まで広がっている）
    sma100 = [100, 101, 102, 103, 104, 105, 106]
    sma60 = [98, 99, 101, 104, 105, 106, 108]

    result = detect_ma_cross_watch(
        _df(sma60, sma100), direction="long", watch_days=20,
    )

    assert bool(result["cross_watch"].iloc[-1]) is False


def test_long_after_cross_beyond_watch_days_is_not_watch():
    sma100 = [100, 101, 102, 103, 104, 105, 106]
    sma60 = [98, 99, 101, 104, 105, 106, 108]

    result = detect_ma_cross_watch(
        _df(sma60, sma100), direction="long", watch_days=2,
    )

    # クロス（day3）から3営業日経過（day6）しており、watch_days=2を超えるため対象外
    assert bool(result["cross_watch"].iloc[-1]) is False


def test_long_reverts_below_after_cross_is_not_watch():
    sma100 = [100, 101, 102, 103, 104, 105]
    # day3でクロスするが、day5に再びsma100を下回る
    sma60 = [98, 99, 101, 104, 105, 100]

    result = detect_ma_cross_watch(
        _df(sma60, sma100), direction="long", watch_days=10,
    )

    assert bool(result["cross_watch"].iloc[-1]) is False


def test_flat_or_down_ma100_is_not_watch_even_if_close():
    # sma100が横ばい・下降だと、接近していても前提条件（上昇トレンド）を満たさない
    sma100 = [100, 100, 100, 100, 100]
    sma60 = [99.5, 99.5, 99.5, 99.5, 99.5]

    result = detect_ma_cross_watch(_df(sma60, sma100), direction="long")

    assert bool(result["cross_watch"].iloc[-1]) is False


def test_short_before_cross_within_proximity_is_watch():
    # sma100は単調減少（下降トレンド）、sma60はsma100の0.5%上を推移（接近中）
    sma100 = [104, 103, 102, 101, 100]
    sma60 = [104.5, 103.5, 102.5, 101.5, 100.5]

    result = detect_ma_cross_watch(_df(sma60, sma100), direction="short")

    assert bool(result["cross_watch"].iloc[-1]) is True
    assert bool(result["before_cross"].iloc[-1]) is True


def test_precondition_columns_none_by_default_does_not_require_sma5_sma20():
    # precondition_columnsを渡さなければ、sma5・sma20列が無くても
    # （＝MA60/100接近ウォッチとして）これまで通り判定できる
    sma100 = [100, 101, 102, 103, 104]
    sma60 = [99.5, 100.5, 101.5, 102.5, 103.5]

    result = detect_ma_cross_watch(_df(sma60, sma100), direction="long")

    assert bool(result["cross_watch"].iloc[-1]) is True


def test_precondition_columns_blocks_when_violated():
    # 実際に報告された不具合の再現: MA60はMA100に接近していても、MA20が
    # MA60を下回っている（並び順としてはショート寄り）銘柄は対象外にする
    sma100 = [100, 101, 102, 103, 104]
    sma60 = [99.5, 100.5, 101.5, 102.5, 103.5]
    sma20 = [90, 90, 90, 90, 90]
    sma5 = [95, 95, 95, 95, 95]
    df = _order_df(sma5=sma5, sma20=sma20, sma60=sma60, sma100=sma100)

    result = detect_ma_cross_watch(
        df, direction="long", precondition_columns=[("sma5", "sma20"), ("sma20", "sma60")],
    )

    assert bool(result["cross_watch"].iloc[-1]) is False


def test_precondition_columns_allows_when_satisfied():
    sma100 = [100, 101, 102, 103, 104]
    sma60 = [99.5, 100.5, 101.5, 102.5, 103.5]
    sma20 = [110, 110, 110, 110, 110]
    sma5 = [120, 120, 120, 120, 120]
    df = _order_df(sma5=sma5, sma20=sma20, sma60=sma60, sma100=sma100)

    result = detect_ma_cross_watch(
        df, direction="long", precondition_columns=[("sma5", "sma20"), ("sma20", "sma60")],
    )

    assert bool(result["cross_watch"].iloc[-1]) is True


# 並び順ウォッチはクロス前（接近中）を対象にせず、クロス後も乖離率1%以内で
# あることを要求するため、テストデータは「監視ペアが下から上にクロスし、
# 以降も1%以内を維持している」パターンを使う（day3でshortがlongを上抜け、
# day6まで1%以内を維持）
_ORDER_WATCH_LONG_COL = [100, 101, 102, 103, 104, 105, 106]
_ORDER_WATCH_SHORT_COL = [99.5, 100.3, 101.2, 103.5, 104.3, 105.2, 106.4]


def test_order_watch_full_mode_uses_sma20_sma60_pair():
    # "full"バリエーション（5>20>60）は並び順の中で最後に揃う1本、MA20とMA60を監視する
    # （前提条件のMA5>MA20も満たす）
    sma60 = _ORDER_WATCH_LONG_COL
    sma20 = _ORDER_WATCH_SHORT_COL
    sma5 = [120] * 7
    # detect_ma_order_watchはORDER_WATCH_COLUMNS・ORDER_WATCH_PRECONDITION_COLUMNSの
    # 列しか参照しないため、sma100は使われない値で埋めておく
    df = _order_df(sma5=sma5, sma20=sma20, sma60=sma60, sma100=[0] * 7)

    result = detect_ma_order_watch(df, direction="long", ma_mode="full")

    assert bool(result["cross_watch"].iloc[-1]) is True
    assert bool(result["after_cross"].iloc[-1]) is True
    assert bool(result["before_cross"].iloc[-1]) is False


def test_order_watch_full_mode_before_cross_is_not_watch():
    # クロス前（接近中）は並び順ウォッチの対象にしない（MA20がMA60を
    # まだ下回ったまま＝並び順としては未完成のため）
    sma60 = [100, 101, 102, 103, 104]
    sma20 = [99.5, 100.5, 101.5, 102.5, 103.5]
    sma5 = [120] * 5
    df = _order_df(sma5=sma5, sma20=sma20, sma60=sma60, sma100=[0] * 5)

    result = detect_ma_order_watch(df, direction="long", ma_mode="full")

    assert bool(result["cross_watch"].iloc[-1]) is False


def test_order_watch_full_mode_precondition_blocks_when_ma5_below_ma20():
    # 実際に報告された不具合の再現: MA20とMA60がクロス済みでも、MA5がMA20を
    # 下回ったまま（並び順としてはショート寄り）の銘柄は監視対象にしない
    sma60 = _ORDER_WATCH_LONG_COL
    sma20 = _ORDER_WATCH_SHORT_COL
    sma5 = [90] * 7
    df = _order_df(sma5=sma5, sma20=sma20, sma60=sma60, sma100=[0] * 7)

    result = detect_ma_order_watch(df, direction="long", ma_mode="full")

    assert bool(result["cross_watch"].iloc[-1]) is False


def test_order_watch_full_100_mode_uses_sma20_sma100_pair():
    sma100 = _ORDER_WATCH_LONG_COL
    sma20 = _ORDER_WATCH_SHORT_COL
    sma5 = [120] * 7
    df = _order_df(sma5=sma5, sma20=sma20, sma100=sma100, sma60=[0] * 7)

    result = detect_ma_order_watch(df, direction="long", ma_mode="full_100")

    assert bool(result["cross_watch"].iloc[-1]) is True
    assert bool(result["after_cross"].iloc[-1]) is True


def test_order_watch_full_100_mode_precondition_blocks_when_ma5_below_ma20():
    # 実際に報告された不具合の再現: MA20とMA100がクロス済みでも、MA5がMA20を
    # 下回ったままの銘柄はロングの並び順ウォッチとしては不適切
    sma100 = _ORDER_WATCH_LONG_COL
    sma20 = _ORDER_WATCH_SHORT_COL
    sma5 = [90] * 7
    df = _order_df(sma5=sma5, sma20=sma20, sma100=sma100, sma60=[0] * 7)

    result = detect_ma_order_watch(df, direction="long", ma_mode="full_100")

    assert bool(result["cross_watch"].iloc[-1]) is False


def test_order_watch_pullback_100_mode_uses_sma5_sma100_pair():
    sma100 = _ORDER_WATCH_LONG_COL
    sma5 = _ORDER_WATCH_SHORT_COL
    sma20 = [120] * 7
    df = _order_df(sma5=sma5, sma20=sma20, sma100=sma100, sma60=[0] * 7)

    result = detect_ma_order_watch(df, direction="long", ma_mode="pullback_100")

    assert bool(result["cross_watch"].iloc[-1]) is True


def test_order_watch_pullback_100_mode_precondition_blocks_when_ma20_below_ma5():
    sma100 = _ORDER_WATCH_LONG_COL
    sma5 = _ORDER_WATCH_SHORT_COL
    sma20 = [90] * 7
    df = _order_df(sma5=sma5, sma20=sma20, sma100=sma100, sma60=[0] * 7)

    result = detect_ma_order_watch(df, direction="long", ma_mode="pullback_100")

    assert bool(result["cross_watch"].iloc[-1]) is False


def test_order_watch_two_line_mode_uses_sma5_sma20_pair():
    sma20 = _ORDER_WATCH_LONG_COL
    sma5 = _ORDER_WATCH_SHORT_COL
    df = _order_df(sma5=sma5, sma20=sma20, sma60=[0] * 7, sma100=[0] * 7)

    result = detect_ma_order_watch(df, direction="long", ma_mode="two_line")

    assert bool(result["cross_watch"].iloc[-1]) is True


def test_order_watch_unknown_ma_mode_raises():
    df = _order_df(sma5=[100], sma20=[90], sma60=[80], sma100=[70])

    try:
        detect_ma_order_watch(df, direction="long", ma_mode="not_a_real_mode")
        assert False, "expected ValueError"
    except ValueError:
        pass

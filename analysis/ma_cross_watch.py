import pandas as pd

from analysis.ma_cross import detect_dead_cross, detect_golden_cross
from analysis.ma_trend import get_ma_slope_series
from config.config import MA_CROSS_WATCH_DAYS, MA_CROSS_WATCH_PROXIMITY_PCT

# MA60/100接近ウォッチ（entry_signal_spec.md 14章）の前提条件: 監視ペア
# （MA60・MA100）より短期側のMA5・MA20が、既に正しい向きで並んでいること
# （ロングなら5>20>60）を別途要求する。これが無いと、MA5・MA20が大きく
# 下にある（実質下降中の）銘柄まで、MA60がMA100に接近しているというだけで
# 監視対象に入ってしまう（2026-08-23、実例をもとに追加）
MA_CROSS_WATCH_PRECONDITION_COLUMNS = [("sma5", "sma20"), ("sma20", "sma60")]

# 並び順ウォッチ（entry_signal_spec.md 15章）: 並び順のバリエーション（ma_mode）
# ごとに「並び順の中で最後に揃う1本」を監視対象のMAペアとする
ORDER_WATCH_COLUMNS = {
    "full": ("sma20", "sma60"),
    "full_100": ("sma20", "sma100"),
    "pullback_100": ("sma5", "sma100"),
    "two_line": ("sma5", "sma20"),
}

# 並び順ウォッチの前提条件: ORDER_WATCH_COLUMNSの監視ペアだけでは並び順の
# 「残り」の関係（例: full_100モードのMA5とMA20の関係）を見ていないため、
# 監視ペアより短期側の並びが既に正しい向きで揃っていることを別途要求する。
# 例えばfull_100モード（5>20>100）でMA20とMA100の接近だけを見ると、MA5が
# まだMA20を下回ったまま（並び順としてはショート寄り）の銘柄も監視対象に
# 含まれてしまうため、"MA5 > MA20"（ロング）を前提条件として追加する。
# two_lineモードは監視ペア自体が並び順の全体（5>20）のため追加条件は無い
ORDER_WATCH_PRECONDITION_COLUMNS = {
    "full": [("sma5", "sma20")],
    "full_100": [("sma5", "sma20")],
    "pullback_100": [("sma20", "sma5")],
    "two_line": [],
}


def detect_ma_cross_watch(df, direction, short_col="sma60", long_col="sma100",
                           precondition_columns=None,
                           proximity_pct=None, watch_days=None, slope_lookback=1):

    """
    MA接近ウォッチ判定（監視専用）

    entry_signal_spec.md 14章（MA60/100接近ウォッチ、short_col/long_col省略時の
    デフォルト）・15章（並び順ウォッチ、ORDER_WATCH_COLUMNS経由でshort_col/long_col
    を指定）に対応する。short_colがlong_colへ接近し、下から上へ突き抜けていく過程
    （ロングの場合）を監視銘柄として拾う。反発モジュール（analysis/ma_bounce.py）とは
    判定ロジックが別物で、対応するエントリー候補判定は持たない（watch-only）

    Parameters
    ----------
    df
        short_col, long_col, precondition_columnsで指定した列を持つ株価DataFrame
        （日付順ソート済み）

    direction
        "long" または "short"

    short_col, long_col
        監視するMAペアの列名。省略時は14章のMA60/100接近ウォッチ（"sma60"・"sma100"）

    precondition_columns
        監視ペア（short_col, long_col）より短期側に追加で要求する順序条件の
        リスト。[(col_a, col_b), ...] の形で、ロングならcol_a > col_bを、
        ショートならcol_a < col_bをすべて満たすことを要求する
        （監視ペア自体の接近・クロス判定とは独立に、常に現在の値で判定する。
        傾きは問わない）。Noneまたは空リストなら追加条件無し

    proximity_pct
        short_colとlong_colの接近しきい値（乖離率）。クロス前（接近中）・クロス後
        （確認期間）の両方で、常にこの範囲内であることを要求する（2026-08-23、
        クロス後は乖離率を問わない旧仕様から変更。クロス後に乖離が広がっても
        監視対象に残り続けてしまう不具合の修正）。Noneならconfig.MA_CROSS_WATCH_PROXIMITY_PCTを使う

    watch_days
        クロス後に監視を継続する営業日数。Noneならconfig.MA_CROSS_WATCH_DAYSを使う

    Returns
    -------
    result
        cross_watch（監視対象かどうか）・before_cross（クロス前の接近中かどうか）・
        after_cross（クロス後の確認期間中かどうか）の3列を持つDataFrame。
        いずれもlong_colが上昇トレンド（ロング）または下降トレンド（ショート）で
        あることと、precondition_columnsの条件（指定時）を前提条件に含む
    """

    if proximity_pct is None:
        proximity_pct = MA_CROSS_WATCH_PROXIMITY_PCT

    if watch_days is None:
        watch_days = MA_CROSS_WATCH_DAYS

    df = df.reset_index(drop=True)
    short = df[short_col]
    long_ = df[long_col]

    slope_long = get_ma_slope_series(long_, lookback=slope_lookback)

    if direction == "long":
        trend_ok = slope_long == "up"
        approaching = short < long_
        cross = detect_golden_cross(df, short_col, long_col)
        crossed_side_ok = short > long_
    elif direction == "short":
        trend_ok = slope_long == "down"
        approaching = short > long_
        cross = detect_dead_cross(df, short_col, long_col)
        crossed_side_ok = short < long_
    else:
        raise ValueError("direction must be 'long' or 'short'")

    diff_pct = (short - long_).abs() / long_
    within_proximity = diff_pct <= proximity_pct

    before_cross = approaching & within_proximity

    # クロス発生日の行位置を前方補完し、直近クロスからの経過営業日数を求める
    positions = pd.Series(range(len(df)), index=df.index)
    last_cross_position = positions.where(cross).ffill()
    days_since_cross = positions - last_cross_position

    after_cross = (
        last_cross_position.notna()
        & (days_since_cross <= watch_days)
        & crossed_side_ok
        & within_proximity
    )

    before_cross = trend_ok & before_cross
    after_cross = trend_ok & after_cross

    if precondition_columns:
        precondition_ok = pd.Series(True, index=df.index)

        for col_a, col_b in precondition_columns:
            if direction == "long":
                precondition_ok &= df[col_a] > df[col_b]
            else:
                precondition_ok &= df[col_a] < df[col_b]

        before_cross = before_cross & precondition_ok
        after_cross = after_cross & precondition_ok

    return pd.DataFrame({
        "cross_watch": before_cross | after_cross,
        "before_cross": before_cross,
        "after_cross": after_cross,
    })


def detect_ma_order_watch(df, direction, ma_mode, proximity_pct=None, watch_days=None,
                           slope_lookback=1):

    """
    並び順ウォッチ判定（監視専用、entry_signal_spec.md 15章）

    「並び順」モジュールが選択している並び順のバリエーション（ma_mode）ごとに、
    ORDER_WATCH_COLUMNSで定義した「並び順の中で最後に揃う1本」のMAペアを
    detect_ma_cross_watch()と同じロジックで監視する。しきい値（乖離率・監視継続
    日数）は14章のMA60/100接近ウォッチと共通のconfig値を使う。

    14章のMA60/100接近ウォッチと異なり、クロス前（接近中。監視ペアがまだ
    逆向き）は対象にしない。並び順ウォッチは「並び順を構成するMAが指定した
    向きに揃っていること」自体が目的（ロングなら監視ペアの短期側が長期側より
    上）のため、まだ逆向きの状態を含めると並び順の体をなさない銘柄まで
    監視対象に入ってしまう。クロス後（監視ペアが正しい向きに揃った後の
    確認期間中）のみを対象にする。ORDER_WATCH_PRECONDITION_COLUMNSで定義した
    前提条件（監視ペアより短期側のMAも既に正しい向きで並んでいること）も
    合わせて満たす日だけを対象にする

    Parameters
    ----------
    df
        ORDER_WATCH_COLUMNS[ma_mode]・ORDER_WATCH_PRECONDITION_COLUMNS[ma_mode]の
        列を持つ株価DataFrame（日付順ソート済み）

    direction
        "long" または "short"

    ma_mode
        "full"・"full_100"・"pullback_100"・"two_line"のいずれか
        （並び順モジュールの"並び順のバリエーション"と同じ値）

    Returns
    -------
    result
        detect_ma_cross_watch()と同じ列構成のDataFrame。before_crossは常にFalseで、
        cross_watchはafter_cross（かつ前提条件を満たす）とのみ一致する
    """

    if ma_mode not in ORDER_WATCH_COLUMNS:
        raise ValueError(f"unknown ma_mode: {ma_mode}")

    short_col, long_col = ORDER_WATCH_COLUMNS[ma_mode]

    result = detect_ma_cross_watch(
        df, direction, short_col=short_col, long_col=long_col,
        precondition_columns=ORDER_WATCH_PRECONDITION_COLUMNS[ma_mode],
        proximity_pct=proximity_pct, watch_days=watch_days, slope_lookback=slope_lookback,
    )

    # クロス前（接近中）は並び順ウォッチの対象にしない（before_cross参照）
    result["before_cross"] = pd.Series(False, index=result.index)
    result["cross_watch"] = result["after_cross"]

    return result

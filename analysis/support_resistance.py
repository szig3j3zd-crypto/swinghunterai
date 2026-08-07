import pandas as pd

from analysis.price_zones import cluster_price_points
from analysis.swing_points import detect_swing_highs, detect_swing_lows
from config.config import (
    SR_BREAKOUT_HOLD_DAYS,
    SR_BREAKOUT_PCT,
    SR_DEVIATION_RESET_PCT,
    SR_INACTIVITY_RESET_DAYS,
    SR_MIN_DURATION_DAYS,
    SR_MIN_TOUCH_COUNT,
    SUPPORT_RESISTANCE_LOOKBACK,
    SWING_POINT_WINDOW,
    ZONE_CLUSTER_THRESHOLD,
)


def detect_resistance_lines(df, timeframe="daily"):

    """
    抵抗線を検出する

    Parameters
    ----------
    df
        date, high, low, close 列を持つ株価DataFrame（単一銘柄）

    timeframe
        "daily" | "weekly" | "monthly"

    Returns
    -------
    lines
        採用条件・リセット条件を満たした有効な抵抗線のリスト
    """

    return _detect_lines(df, line_type="resistance", timeframe=timeframe)


def detect_support_lines(df, timeframe="daily"):

    """
    支持線を検出する

    Parameters
    ----------
    df
        date, high, low, close 列を持つ株価DataFrame（単一銘柄）

    timeframe
        "daily" | "weekly" | "monthly"

    Returns
    -------
    lines
        採用条件・リセット条件を満たした有効な支持線のリスト
    """

    return _detect_lines(df, line_type="support", timeframe=timeframe)


def _detect_lines(df, line_type, timeframe):

    """
    支持線・抵抗線の検出共通処理

    docs/specifications/support_resistance_spec.md 2〜7章に対応する。
    """

    df = _prepare_dates(df)

    lookback_rows = SUPPORT_RESISTANCE_LOOKBACK[timeframe]
    df = df.tail(lookback_rows).reset_index(drop=True)

    if line_type == "resistance":
        points = detect_swing_highs(df, window=SWING_POINT_WINDOW)
    else:
        points = detect_swing_lows(df, window=SWING_POINT_WINDOW)

    zones = cluster_price_points(points, threshold=ZONE_CLUSTER_THRESHOLD)

    min_duration_days = SR_MIN_DURATION_DAYS[timeframe]
    latest_date = df["date"].max()

    lines = []

    for zone in zones:

        if zone["touch_count"] < SR_MIN_TOUCH_COUNT:
            continue

        duration_days = (
            zone["last_touch_date"] - zone["first_touch_date"]
        ).days

        if duration_days < min_duration_days:
            continue

        if _is_broken(df, zone["price"], line_type):
            continue

        if _is_deviated(df, zone["price"]):
            continue

        days_since_last_touch = (
            latest_date - zone["last_touch_date"]
        ).days

        if days_since_last_touch > SR_INACTIVITY_RESET_DAYS:
            continue

        # 有効化日 = ラインが採用条件（タッチ回数）を満たした時点のタッチ日
        valid_since_date = zone["touch_dates"][SR_MIN_TOUCH_COUNT - 1]

        lines.append({
            "type": line_type,
            "price": zone["price"],
            "touch_count": zone["touch_count"],
            "first_touch_date": zone["first_touch_date"],
            "last_touch_date": zone["last_touch_date"],
            "valid_since_date": valid_since_date,
        })

    return lines


def _prepare_dates(df):

    """
    日付統一（他インジケーターモジュールと同じ前処理）
    """

    df = df.copy()

    df["date"] = pd.to_datetime(
        df["date"],
        format="mixed",
        utc=True
    )

    df["date"] = df["date"].dt.tz_localize(None)

    df = df.sort_values("date").reset_index(drop=True)

    return df


def _is_broken(df, price, line_type):

    """
    正式ブレイク判定

    終値がライン±SR_BREAKOUT_PCTを超えて
    SR_BREAKOUT_HOLD_DAYS営業日連続で維持した実績があれば、
    ライン終了（=このラインはもう有効ではない）とみなす。
    """

    if line_type == "resistance":
        threshold_price = price * (1 + SR_BREAKOUT_PCT)
        beyond = df["close"] > threshold_price
    else:
        threshold_price = price * (1 - SR_BREAKOUT_PCT)
        beyond = df["close"] < threshold_price

    consecutive_days = beyond.rolling(window=SR_BREAKOUT_HOLD_DAYS).sum()

    return bool((consecutive_days >= SR_BREAKOUT_HOLD_DAYS).any())


def nearest_line_below(lines, price):

    """
    指定価格より下にあるラインのうち、最も近いものを返す

    Parameters
    ----------
    lines
        detect_support_lines / detect_resistance_lines の戻り値

    price
        基準価格

    Returns
    -------
    line
        最も近いライン（dict）。該当なしならNone
    """

    candidates = [line for line in lines if line["price"] < price]

    if not candidates:
        return None

    return max(candidates, key=lambda line: line["price"])


def nearest_line_above(lines, price):

    """
    指定価格より上にあるラインのうち、最も近いものを返す

    Parameters
    ----------
    lines
        detect_support_lines / detect_resistance_lines の戻り値

    price
        基準価格

    Returns
    -------
    line
        最も近いライン（dict）。該当なしならNone
    """

    candidates = [line for line in lines if line["price"] > price]

    if not candidates:
        return None

    return min(candidates, key=lambda line: line["price"])


def _is_deviated(df, price):

    """
    価格乖離によるリセット判定

    直近終値がラインからSR_DEVIATION_RESET_PCT以上離れていれば
    現在の売買判断には無関係とみなす。
    """

    latest_close = df["close"].iloc[-1]

    return abs(latest_close - price) / price > SR_DEVIATION_RESET_PCT

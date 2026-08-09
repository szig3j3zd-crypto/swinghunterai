import pandas as pd

from analysis.half_signal import detect_half_signal
from analysis.ma_trend import (
    get_current_trend_period,
    is_long_trend_series,
    is_short_trend_series,
)
from analysis.support_resistance import nearest_line_above, nearest_line_below
from config.config import MAX_ENTRY_BOUNCES
from rules.bounce_count import get_bounce_number
from rules.exit_rule import (
    calculate_risk_reward_ratio,
    get_stop_loss_price,
    get_take_profit_price,
)
from rules.screening_filters import passes_price_filter, passes_volume_filter
from scoring.entry_score import calculate_total_score


def evaluate_entry(df, direction, support_lines=None, resistance_lines=None,
                    bounce_merge_within=None, min_volume=None, min_price=None,
                    max_price=None):

    """
    直近日がエントリー候補かどうかを判定する

    entry_signal_spec.md 2,4,5,6章、support_resistance_spec.md 8章の
    判定を統合したRule Engineの本体。

    Parameters
    ----------
    df
        date, open, close, volume, volume_ratio, sma5, sma20, sma60 列を持つ
        株価DataFrame（単一銘柄、日付順ソート済み）

    direction
        "long" または "short"

    support_lines
        detect_support_lines() の戻り値（ロング判定時に使用）

    resistance_lines
        detect_resistance_lines() の戻り値（ショート判定時に使用）

    bounce_merge_within
        近接した反発をまとめる間隔（行数ベース）。Noneならconfig.BOUNCE_MERGE_WITHIN_DAYSを使う。
        日足は営業日、週足は週、月足は月を1行として数えるため、時間足に応じて指定する

    min_volume, min_price, max_price
        出来高・株価フィルタの上書き値。Noneならconfig既定値を使う

    Returns
    -------
    result
        is_entry_candidate（bool）と、Falseの場合はreason（見送り理由）、
        Trueの場合はpattern・bounce_numberを持つdict
    """

    current_price = df["close"].iloc[-1]
    current_volume = df["volume"].iloc[-1]

    if not passes_volume_filter(current_volume, min_volume=min_volume):
        return _skip("volume_too_low", current_price, direction)

    if not passes_price_filter(current_price, min_price=min_price, max_price=max_price):
        return _skip("price_out_of_range", current_price, direction)

    if direction == "long":
        trend = is_long_trend_series(df)
    elif direction == "short":
        trend = is_short_trend_series(df)
    else:
        raise ValueError("direction must be 'long' or 'short'")

    if not bool(trend.iloc[-1]):
        return _skip("not_in_trend", current_price, direction)

    if direction == "long":
        line = nearest_line_below(support_lines or [], current_price)
        support_price = line["price"] if line else None
        resistance_price = None
    else:
        line = nearest_line_above(resistance_lines or [], current_price)
        support_price = None
        resistance_price = line["price"] if line else None

    signal = detect_half_signal(
        df,
        direction=direction,
        support_price=support_price,
        resistance_price=resistance_price,
    )

    if not bool(signal["half_signal"].iloc[-1]):
        return _skip("no_half_signal_today", current_price, direction)

    pattern_today = signal["pattern"].iloc[-1]

    sma60_today = df["sma60"].iloc[-1]

    if direction == "long" and not (current_price > sma60_today):
        return _skip("below_sma60", current_price, direction)

    if direction == "short" and not (current_price < sma60_today):
        return _skip("above_sma60", current_price, direction)

    if pattern_today == "A":
        if line is None:
            return _skip("pattern_a_without_valid_line", current_price, direction)
        start_date = line["valid_since_date"]
    else:
        start_date = get_current_trend_period(df, direction=direction)

        if start_date is None:
            return _skip("trend_period_not_found", current_price, direction)

    pattern_signal = signal["pattern"] == pattern_today
    bounce_number = get_bounce_number(
        df, pattern_signal, start_date=start_date,
        merge_within_days=bounce_merge_within,
    )
    today_bounce = bounce_number.iloc[-1]

    if pd.isna(today_bounce) or today_bounce > MAX_ENTRY_BOUNCES:
        return _skip("bounce_limit_exceeded", current_price, direction)

    stop_loss_price = get_stop_loss_price(df, current_price, direction)
    take_profit_price = get_take_profit_price(df, current_price, direction)
    risk_reward_ratio = calculate_risk_reward_ratio(
        current_price, stop_loss_price, take_profit_price, direction
    )

    volume_ratio = df["volume_ratio"].iloc[-1]
    score = calculate_total_score(int(today_bounce), volume_ratio, risk_reward_ratio)

    return {
        "is_entry_candidate": True,
        "direction": direction,
        "pattern": pattern_today,
        "bounce_number": int(today_bounce),
        "price": current_price,
        "stop_loss_price": stop_loss_price,
        "take_profit_price": take_profit_price,
        "risk_reward_ratio": risk_reward_ratio,
        "score": score,
    }


def _skip(reason, price=None, direction=None):

    """
    見送り結果の組み立て

    price・directionは、候補ではない銘柄でも現在の株価を参照できるよう
    （個別銘柄検索から売買銘柄/監視銘柄に登録する用途など）持たせておく
    """

    return {
        "is_entry_candidate": False,
        "reason": reason,
        "price": price,
        "direction": direction,
    }

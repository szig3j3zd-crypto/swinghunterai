import pandas as pd

from analysis.half_signal import detect_half_signal
from analysis.ma_bounce import detect_bounce
from analysis.ma_cross import detect_perfect_dead_cross, detect_perfect_golden_cross
from analysis.ma_trend import (
    get_current_trend_period,
    is_long_trend_series,
    is_short_trend_series,
)
from analysis.parallel_rise import detect_parallel_rise
from config.config import MAX_ENTRY_BOUNCES
from rules.bounce_count import get_bounce_number
from rules.exit_rule import (
    calculate_risk_reward_ratio,
    get_stop_loss_price,
    get_take_profit_price,
)
from rules.screening_filters import passes_price_filter, passes_volume_filter
from scoring.entry_score import calculate_total_score

EVENT_MODULES = ("perfect_golden_cross", "bounce", "parallel_rise", "half_signal")
VALID_MODULES = ("ma_order",) + EVENT_MODULES


def evaluate_entry(df, direction, modules, ma_mode="full", bounce_merge_within=None,
                    min_volume=None, min_price=None, max_price=None):

    """
    直近日がエントリー候補（または監視銘柄）かどうかを判定する

    entry_signal_spec.md 2〜8章の判定を統合したRule Engineの本体。
    モジュール化改訂（2026-08）により、利用者が選択したモジュールを
    すべてAND結合して判定する。

    Parameters
    ----------
    df
        date, open, close, volume, volume_ratio, sma5, sma20
        （ma_mode="full"ならさらにsma60）列を持つ株価DataFrame
        （単一銘柄、日付順ソート済み）

    direction
        "long" または "short"

    modules
        使用するモジュール名のリスト（1つ以上必須）。
        "ma_order"（並び順・状態型）、"perfect_golden_cross"（完全ゴールデンクロス）、
        "bounce"（反発）、"parallel_rise"（並走上昇）、"half_signal"（半分シグナル）
        から選択する

    ma_mode
        "ma_order"選択時の並び順バリエーション。"full"（5>20>60、デフォルト）
        または "two_line"（5>20のみ）。"two_line"の場合、60日線フィルタも解除する

    bounce_merge_within
        近接した反発をまとめる間隔（行数ベース）。Noneならconfig.BOUNCE_MERGE_WITHIN_DAYSを使う

    min_volume, min_price, max_price
        出来高・株価フィルタの上書き値。Noneならconfig既定値を使う

    Returns
    -------
    result
        is_entry_candidate（bool）・is_watch_candidate（bool）を持つdict。
        is_entry_candidateがFalseの場合はreason（見送り理由）、
        Trueの場合はbounce_number・stop_loss_price・take_profit_price・
        risk_reward_ratio・scoreを持つ
    """

    if not modules:
        raise ValueError("modules must contain at least one module name")

    invalid_modules = set(modules) - set(VALID_MODULES)

    if invalid_modules:
        raise ValueError(f"unknown modules: {sorted(invalid_modules)}")

    if direction not in ("long", "short"):
        raise ValueError("direction must be 'long' or 'short'")

    current_price = df["close"].iloc[-1]
    current_volume = df["volume"].iloc[-1]

    if not passes_volume_filter(current_volume, min_volume=min_volume):
        return _skip("volume_too_low", current_price, direction)

    if not passes_price_filter(current_price, min_price=min_price, max_price=max_price):
        return _skip("price_out_of_range", current_price, direction)

    state_ok = pd.Series(True, index=df.index)

    if "ma_order" in modules:
        if direction == "long":
            state_ok &= is_long_trend_series(df, ma_mode=ma_mode)
        else:
            state_ok &= is_short_trend_series(df, ma_mode=ma_mode)

        if not bool(state_ok.iloc[-1]):
            return _skip("not_in_trend", current_price, direction)

        if ma_mode == "full":
            sma60_today = df["sma60"].iloc[-1]

            if direction == "long" and not (current_price > sma60_today):
                return _skip("below_sma60", current_price, direction)

            if direction == "short" and not (current_price < sma60_today):
                return _skip("above_sma60", current_price, direction)

    event_series = {}
    watch_series = None

    if "perfect_golden_cross" in modules:
        if direction == "long":
            event_series["perfect_golden_cross"] = detect_perfect_golden_cross(df)
        else:
            event_series["perfect_golden_cross"] = detect_perfect_dead_cross(df)

    if "parallel_rise" in modules:
        event_series["parallel_rise"] = detect_parallel_rise(df, direction=direction)

    if "half_signal" in modules:
        event_series["half_signal"] = detect_half_signal(df, direction=direction)["half_signal"]

    if "bounce" in modules:
        bounce_result = detect_bounce(df, direction=direction)
        event_series["bounce"] = bounce_result["bounce_candidate"]
        watch_series = bounce_result["bounce_watch"]

    if event_series:
        combined_candidate = pd.Series(True, index=df.index)

        for series in event_series.values():
            combined_candidate &= series.reindex(df.index).fillna(False)
    else:
        # イベント型モジュールを選択していない場合（並び順のみ選択等）は、
        # 状態条件を満たしている当日をそのまま候補日とする
        combined_candidate = state_ok

    if not bool(combined_candidate.iloc[-1]):
        if watch_series is not None and bool(watch_series.iloc[-1]):
            return _watch(current_price, direction)

        return _skip("no_signal_today", current_price, direction)

    bounce_number = None

    if "bounce" in modules:
        # 反発モジュールはMA5・MA20の関係のみに依存するため（5章参照）、
        # カウント起点となるトレンド期間もma_orderモジュールの選択とは独立に
        # 2本版（5>20）の定義で判定する
        start_date = get_current_trend_period(df, direction=direction, ma_mode="two_line")

        if start_date is None:
            return _skip("trend_period_not_found", current_price, direction)

        bounce_count = get_bounce_number(
            df, event_series["bounce"], start_date=start_date,
            merge_within_days=bounce_merge_within,
        )
        today_bounce = bounce_count.iloc[-1]

        if pd.isna(today_bounce) or today_bounce > MAX_ENTRY_BOUNCES:
            return _skip("bounce_limit_exceeded", current_price, direction)

        bounce_number = int(today_bounce)

    stop_loss_price = get_stop_loss_price(df, current_price, direction)
    take_profit_price = get_take_profit_price(df, current_price, direction)
    risk_reward_ratio = calculate_risk_reward_ratio(
        current_price, stop_loss_price, take_profit_price, direction
    )

    volume_ratio = df["volume_ratio"].iloc[-1]
    score = calculate_total_score(bounce_number, volume_ratio, risk_reward_ratio)

    return {
        "is_entry_candidate": True,
        "is_watch_candidate": False,
        "direction": direction,
        "modules": list(modules),
        "bounce_number": bounce_number,
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
        "is_watch_candidate": False,
        "reason": reason,
        "price": price,
        "direction": direction,
    }


def _watch(price, direction):

    """
    監視銘柄結果の組み立て

    反発モジュールでMA20を下回っている（ショートなら上回っている）間の日を示す。
    エントリー候補にはならないが、entry_signal_spec.md 5章の方針により
    見送りとは別扱いにする
    """

    reason = "bounce_below_ma20_watch" if direction == "long" else "bounce_above_ma20_watch"

    return {
        "is_entry_candidate": False,
        "is_watch_candidate": True,
        "reason": reason,
        "price": price,
        "direction": direction,
    }

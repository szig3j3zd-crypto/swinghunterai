from analysis.swing_points import detect_swing_highs, detect_swing_lows
from config.config import SWING_POINT_WINDOW


def get_previous_swing_high(df, window=None):

    """
    直近のスイングハイ（前回高値）を取得する
    """

    if window is None:
        window = SWING_POINT_WINDOW

    points = detect_swing_highs(df, window=window)

    if points.empty:
        return None

    return points.iloc[-1]["price"]


def get_previous_swing_low(df, window=None):

    """
    直近のスイングロー（前回底値）を取得する
    """

    if window is None:
        window = SWING_POINT_WINDOW

    points = detect_swing_lows(df, window=window)

    if points.empty:
        return None

    return points.iloc[-1]["price"]


def get_round_level_above(price):

    """
    指定価格より上にある直近の節目（キリのいい価格）を取得する
    """

    step = _round_step(price)

    level = (int(price // step) + 1) * step

    while level <= price:
        level += step

    return level


def get_round_level_below(price):

    """
    指定価格より下にある直近の節目（キリのいい価格）を取得する
    """

    step = _round_step(price)

    level = int(price // step) * step

    while level >= price:
        level -= step

    return level


def _round_step(price):

    """
    株価水準に応じた節目の刻み幅
    """

    if price < 1000:
        return 100

    if price < 10000:
        return 500

    return 1000


def get_take_profit_price(df, entry_price, direction):

    """
    利確価格を取得する

    前回高値（安値）と節目のうち、エントリー価格から遠い方を採用する
    （損切とは逆に、利確は目標に余裕を持たせる）。

    ※ ショートのみ目標を近め（狭め）にする案をバックテストしたが、
    勝率は改善したものの平均リターンが悪化したため、ロングと同じ
    「遠い方」に戻した（exit_rule_spec.md参照）。

    Parameters
    ----------
    df
        date, high, low 列を持つ株価DataFrame（単一銘柄）

    entry_price
        エントリー価格

    direction
        "long" または "short"

    Returns
    -------
    price
        利確価格。候補が無ければNone
    """

    if direction == "long":
        swing_target = get_previous_swing_high(df)
        round_target = get_round_level_above(entry_price)

        candidates = [
            price for price in (swing_target, round_target)
            if price is not None and price > entry_price
        ]

        return max(candidates) if candidates else None

    if direction == "short":
        swing_target = get_previous_swing_low(df)
        round_target = get_round_level_below(entry_price)

        candidates = [
            price for price in (swing_target, round_target)
            if price is not None and price < entry_price
        ]

        return min(candidates) if candidates else None

    raise ValueError("direction must be 'long' or 'short'")


def get_stop_loss_price(df, entry_price, direction):

    """
    損切価格を取得する

    前回底値（高値）と当日の20日線のうち、エントリー価格に近い方
    （よりタイトな方）を採用する。

    Parameters
    ----------
    df
        date, high, low, sma20 列を持つ株価DataFrame（単一銘柄）

    entry_price
        エントリー価格

    direction
        "long" または "short"

    Returns
    -------
    price
        損切価格。候補が無ければNone
    """

    sma20_price = df["sma20"].iloc[-1]

    if direction == "long":
        swing_target = get_previous_swing_low(df)

        candidates = [
            price for price in (swing_target, sma20_price)
            if price is not None and price < entry_price
        ]

        return max(candidates) if candidates else None

    if direction == "short":
        swing_target = get_previous_swing_high(df)

        candidates = [
            price for price in (swing_target, sma20_price)
            if price is not None and price > entry_price
        ]

        return min(candidates) if candidates else None

    raise ValueError("direction must be 'long' or 'short'")


def calculate_risk_reward_ratio(entry_price, stop_loss_price, take_profit_price, direction):

    """
    リスクリワード比（利確幅 ÷ 損切幅）を計算する

    参考情報として計算するのみで、候補の絞り込みには使わない。

    Returns
    -------
    ratio
        リスクリワード比。損切/利確価格が無い、または損切幅が0以下ならNone
    """

    if stop_loss_price is None or take_profit_price is None:
        return None

    if direction == "long":
        risk = entry_price - stop_loss_price
        reward = take_profit_price - entry_price
    elif direction == "short":
        risk = stop_loss_price - entry_price
        reward = entry_price - take_profit_price
    else:
        raise ValueError("direction must be 'long' or 'short'")

    if risk <= 0:
        return None

    return reward / risk

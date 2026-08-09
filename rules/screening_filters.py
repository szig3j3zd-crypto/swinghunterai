from config.config import (
    MAX_MARKET_CAP,
    MAX_PRICE,
    MIN_MARKET_CAP,
    MIN_PRICE,
    MIN_VOLUME,
)


def passes_volume_filter(volume, min_volume=None):

    """
    出来高フィルタ

    Parameters
    ----------
    volume
        直近の出来高

    min_volume
        Noneならconfig.MIN_VOLUMEを使う。さらにNoneならフィルタなし
    """

    if min_volume is None:
        min_volume = MIN_VOLUME

    if min_volume is None:
        return True

    return volume >= min_volume


def passes_price_filter(price, min_price=None, max_price=None):

    """
    株価フィルタ

    Parameters
    ----------
    price
        直近の株価

    min_price, max_price
        Noneならconfig.MIN_PRICE / MAX_PRICEを使う。さらにNoneならフィルタなし
    """

    if min_price is None:
        min_price = MIN_PRICE

    if max_price is None:
        max_price = MAX_PRICE

    if min_price is not None and price < min_price:
        return False

    if max_price is not None and price > max_price:
        return False

    return True


def _resolve_market_cap_bounds(min_market_cap, max_market_cap):

    """
    時価総額フィルタの下限・上限を確定する

    Noneならconfig既定値にフォールバックし、下限0以下・上限が無限大の場合は
    「フィルタなし」として扱う（UI側で「0で無効」と揃えるため）
    """

    if min_market_cap is None:
        min_market_cap = MIN_MARKET_CAP

    if max_market_cap is None:
        max_market_cap = MAX_MARKET_CAP

    if min_market_cap is not None and min_market_cap <= 0:
        min_market_cap = None

    if max_market_cap is not None and max_market_cap == float("inf"):
        max_market_cap = None

    return min_market_cap, max_market_cap


def market_cap_filter_is_active(min_market_cap=None, max_market_cap=None):

    """
    時価総額フィルタが実質的に有効かどうか

    無効なら、呼び出し側は時価総額の取得（外部API呼び出し）自体を省略できる
    """

    min_market_cap, max_market_cap = _resolve_market_cap_bounds(
        min_market_cap, max_market_cap
    )

    return not (min_market_cap is None and max_market_cap is None)


def passes_market_cap_filter(market_cap, min_market_cap=None, max_market_cap=None):

    """
    時価総額フィルタ

    Parameters
    ----------
    market_cap
        時価総額（円）。取得できなかった場合はNoneを渡す

    min_market_cap, max_market_cap
        Noneならconfig.MIN_MARKET_CAP / MAX_MARKET_CAPを使う。さらにNoneならフィルタなし
    """

    min_market_cap, max_market_cap = _resolve_market_cap_bounds(
        min_market_cap, max_market_cap
    )

    if min_market_cap is None and max_market_cap is None:
        return True

    if market_cap is None:
        return False

    if min_market_cap is not None and market_cap < min_market_cap:
        return False

    if max_market_cap is not None and market_cap > max_market_cap:
        return False

    return True

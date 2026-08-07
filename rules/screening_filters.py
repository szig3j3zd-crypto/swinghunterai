from config.config import MAX_PRICE, MIN_PRICE, MIN_VOLUME


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

def cluster_price_points(points, threshold):

    """
    価格ポイントを帯（ゾーン）へクラスタリングする

    価格でソートし、帯の平均値との差がthreshold以内なら
    同じ帯へ追加していく逐次クラスタリング方式。

    Parameters
    ----------
    points
        date, price 列を持つDataFrame

    threshold
        帯として統合する価格差の許容割合（例: 0.02 なら2%）

    Returns
    -------
    zones
        帯ごとの情報（price, touch_count, first_touch_date, last_touch_date,
        touch_dates）を持つdictのリスト
    """

    sorted_points = points.sort_values("price").reset_index(drop=True)

    zones = []
    current_prices = []
    current_dates = []

    for _, point in sorted_points.iterrows():

        if not current_prices:
            current_prices.append(point["price"])
            current_dates.append(point["date"])
            continue

        zone_price = sum(current_prices) / len(current_prices)

        if abs(point["price"] - zone_price) / zone_price <= threshold:
            current_prices.append(point["price"])
            current_dates.append(point["date"])
        else:
            zones.append(_build_zone(current_prices, current_dates))
            current_prices = [point["price"]]
            current_dates = [point["date"]]

    if current_prices:
        zones.append(_build_zone(current_prices, current_dates))

    return zones


def _build_zone(prices, dates):

    """
    帯情報の組み立て
    """

    sorted_dates = sorted(dates)

    return {
        "price": sum(prices) / len(prices),
        "touch_count": len(prices),
        "first_touch_date": sorted_dates[0],
        "last_touch_date": sorted_dates[-1],
        "touch_dates": sorted_dates,
    }

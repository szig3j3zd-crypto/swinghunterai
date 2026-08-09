def calculate_pnl(trade):

    """
    トレード1件の損益（円）を計算する

    Parameters
    ----------
    trade
        direction（"long" | "short"）, entry_price, exit_price, quantity を
        持つdict。exit_priceがNoneなら未決済

    Returns
    -------
    pnl
        損益（円）。未決済（exit_price=None）ならNone
    """

    if trade["exit_price"] is None:
        return None

    if trade["direction"] == "long":
        diff = trade["exit_price"] - trade["entry_price"]
    else:
        diff = trade["entry_price"] - trade["exit_price"]

    return diff * trade["quantity"]


def total_pnl(trades):

    """
    複数トレードの損益合計（円）

    未決済トレード（損益None）は集計対象外
    """

    return sum(
        pnl
        for pnl in (calculate_pnl(trade) for trade in trades)
        if pnl is not None
    )


def group_by_year_and_month(trades):

    """
    トレードを年→月でグルーピングし、それぞれの損益合計も付与する

    Parameters
    ----------
    trades
        trade_date（"YYYY-MM-DD"）を持つトレードのリスト

    Returns
    -------
    groups
        [(year, year_pnl, [(month, month_pnl, [trade, ...]), ...]), ...]
        年・月とも降順（新しい順）に並んだリスト
    """

    by_year_month = {}

    for trade in trades:
        year, month = _year_month(trade["trade_date"])
        by_year_month.setdefault(year, {}).setdefault(month, []).append(trade)

    groups = []

    for year in sorted(by_year_month.keys(), reverse=True):

        month_groups = []
        year_pnl = 0.0

        for month in sorted(by_year_month[year].keys(), reverse=True):
            month_trades = by_year_month[year][month]
            month_pnl = total_pnl(month_trades)
            year_pnl += month_pnl
            month_groups.append((month, month_pnl, month_trades))

        groups.append((year, year_pnl, month_groups))

    return groups


def _year_month(trade_date):

    """
    "YYYY-MM-DD" 形式の日付文字列から (year, month) を取り出す
    """

    year_str, month_str, _ = trade_date.split("-")

    return int(year_str), int(month_str)

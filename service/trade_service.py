from config.config import CAPITAL_GAINS_TAX_RATE


def calculate_pnl(trade):

    """
    トレード1件の税引前（グロス）損益（円）を計算する

    課税は個別トレードごとではなく、暦年で損益通算した合計額に対して
    行う（`_net_after_tax_pnl`、`total_pnl`、`group_by_year_and_month`の
    年間損益で使用。2026-08-28改訂。以前はここで個別トレードごとに課税
    していたが、特定口座の損益通算の実務に合わせて合計額課税方式に変更）

    Parameters
    ----------
    trade
        direction（"long" | "short"）, entry_price, exit_price, quantity を
        持つdict。exit_priceがNoneなら未決済

    Returns
    -------
    pnl
        税引前損益（円）。未決済（exit_price=None）ならNone
    """

    if trade["exit_price"] is None:
        return None

    if trade["direction"] == "long":
        diff = trade["exit_price"] - trade["entry_price"]
    else:
        diff = trade["entry_price"] - trade["exit_price"]

    return diff * trade["quantity"]


def _net_after_tax_pnl(trades):

    """
    複数トレードの合算後の税引後損益（円）を計算する

    特定口座のトレード（is_nisa=False）は損益を合算してから、合計が
    プラスの場合のみ譲渡益課税（`CAPITAL_GAINS_TAX_RATE`、20.315%）を
    1回だけ適用する（個別トレードごとに課税しない。合計がマイナスなら
    非課税、税還付も計算しない）。NISA口座のトレード（is_nisa=True）は
    常に非課税で、損益をそのまま合算に含める（NISAの損失は特定口座の
    利益と損益通算できないため、taxableの合算には含めない）

    未決済トレード（損益None）は集計対象外
    """

    taxable_gross = 0.0
    nisa_gross = 0.0

    for trade in trades:
        pnl = calculate_pnl(trade)

        if pnl is None:
            continue

        if trade.get("is_nisa"):
            nisa_gross += pnl
        else:
            taxable_gross += pnl

    taxable_after_tax = (
        taxable_gross * (1 - CAPITAL_GAINS_TAX_RATE)
        if taxable_gross > 0 else taxable_gross
    )

    return taxable_after_tax + nisa_gross


def total_pnl(trades):

    """
    複数トレードの税引後損益合計（円）

    暦年（trade_dateの年）ごとに損益通算してから課税し（`_net_after_tax_pnl`）、
    各年の税引後の額を合算する。年をまたいだ損益通算は行わない（特定口座の
    損益通算は年内のみで、翌年へ繰り越すには申告分離課税の手続きが別途
    必要なため）。未決済トレード（損益None）は集計対象外
    """

    by_year = {}

    for trade in trades:
        if trade["exit_price"] is None:
            continue

        year, _ = _year_month(trade["trade_date"])
        by_year.setdefault(year, []).append(trade)

    return sum(_net_after_tax_pnl(year_trades) for year_trades in by_year.values())


def group_by_year_and_month(trades):

    """
    トレードを年→月でグルーピングし、それぞれの損益合計も付与する

    月間損益は参考値として、その月の税引前（グロス）損益の単純合計を返す
    （課税は暦年単位でのみ行うため、月単位では損益通算・課税をしない）。
    年間損益は、その年の決算済みトレードを損益通算してから課税した
    税引後の額（`_net_after_tax_pnl`。2026-08-28改訂。以前は月間損益を
    そのまま合算していたが、個別トレードごとの課税をやめたことに伴い、
    年単位で1回だけ課税する方式に変更）

    Parameters
    ----------
    trades
        trade_date（"YYYY-MM-DD"）を持つトレードのリスト

    Returns
    -------
    groups
        [(year, year_pnl, [(month, month_pnl, [trade, ...]), ...]), ...]
        年・月とも降順（新しい順）に並んだリスト。year_pnlは税引後、
        month_pnlは税引前（グロス）
    """

    by_year_month = {}

    for trade in trades:
        year, month = _year_month(trade["trade_date"])
        by_year_month.setdefault(year, {}).setdefault(month, []).append(trade)

    groups = []

    for year in sorted(by_year_month.keys(), reverse=True):

        month_groups = []
        year_trades = []

        for month in sorted(by_year_month[year].keys(), reverse=True):
            month_trades = by_year_month[year][month]
            month_pnl = sum(calculate_pnl(trade) for trade in month_trades)
            month_groups.append((month, month_pnl, month_trades))
            year_trades.extend(month_trades)

        year_pnl = _net_after_tax_pnl(year_trades)

        groups.append((year, year_pnl, month_groups))

    return groups


def _year_month(trade_date):

    """
    "YYYY-MM-DD" 形式の日付文字列から (year, month) を取り出す
    """

    year_str, month_str, _ = trade_date.split("-")

    return int(year_str), int(month_str)

from config.config import MAX_HOLDING_DAYS


def get_holding_days(df, entry_date):

    """
    エントリー日から直近日までの経過営業日数を取得する

    行数の差で数える（1行=1営業日）ため、休場日を挟んでも正しく数えられる。

    Parameters
    ----------
    df
        date 列を持つ株価DataFrame（日付順ソート済み）

    entry_date
        エントリー日

    Returns
    -------
    holding_days
        経過営業日数。entry_dateがdf内に見つからなければNone
    """

    df = df.reset_index(drop=True)

    matches = df.index[df["date"] == entry_date]

    if len(matches) == 0:
        return None

    entry_position = matches[0]
    latest_position = len(df) - 1

    return latest_position - entry_position


def evaluate_holding(df, entry_date, max_holding_days=None):

    """
    保有継続の見直し判定（時間切れ警告）

    利確・損切のどちらにも達しないまま保有期間が長期化している場合に
    「見直し候補」として警告する。強制決済はせず、実際の決済判断は委ねる。

    Parameters
    ----------
    df
        date 列を持つ株価DataFrame（日付順ソート済み）

    entry_date
        エントリー日

    max_holding_days
        Noneならconfig.MAX_HOLDING_DAYSを使う

    Returns
    -------
    result
        holding_days（経過営業日数）とneeds_review（見直し候補かどうか）を持つdict
    """

    if max_holding_days is None:
        max_holding_days = MAX_HOLDING_DAYS

    holding_days = get_holding_days(df, entry_date)

    if holding_days is None:
        return {"holding_days": None, "needs_review": False}

    return {
        "holding_days": int(holding_days),
        "needs_review": bool(holding_days >= max_holding_days),
    }

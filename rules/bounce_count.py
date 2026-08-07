import pandas as pd

from config.config import BOUNCE_MERGE_WITHIN_DAYS, MAX_ENTRY_BOUNCES


def get_bounce_number(df, signal, start_date, merge_within_days=None):

    """
    半分シグナル発生日を反発としてグループ化し、何回目の反発かを付与する

    docs/specifications/entry_signal_spec.md 6章の
    「反発1・2発目のみを候補とする」に対応する。

    近接する発生日（merge_within_days営業日以内、行数ベース）は
    同一の反発としてまとめる。世代管理（ラインのブレイクによる
    タッチ履歴の分割）は行わない（Ver2.0スコープ外）。

    Parameters
    ----------
    df
        date 列を持つ株価DataFrame（日付順ソート済み）

    signal
        半分シグナル発生日を示すbooleanのSeries（dfと行が対応）

    start_date
        カウント対象の開始日（ラインの有効化日、またはトレンド開始日）

    merge_within_days
        何営業日以内なら同一の反発としてまとめるか

    Returns
    -------
    bounce_number
        各日について、何回目の反発グループに属するかを持つSeries
        （signal=Falseの日、start_date未満の日はNaN）
    """

    if merge_within_days is None:
        merge_within_days = BOUNCE_MERGE_WITHIN_DAYS

    df = df.reset_index(drop=True)
    signal = signal.reset_index(drop=True)

    target = signal & (df["date"] >= start_date)
    event_positions = df.index[target].tolist()

    bounce_number = pd.Series(index=df.index, dtype="float64")

    if not event_positions:
        return bounce_number

    groups = [[event_positions[0]]]

    for position in event_positions[1:]:
        if position - groups[-1][-1] <= merge_within_days:
            groups[-1].append(position)
        else:
            groups.append([position])

    for group_index, group in enumerate(groups, start=1):
        for position in group:
            bounce_number.iloc[position] = group_index

    return bounce_number


def is_entry_candidate(bounce_number, max_bounces=None):

    """
    反発回数がエントリー候補の上限以内かどうかを判定する

    Parameters
    ----------
    bounce_number
        get_bounce_number() の戻り値

    max_bounces
        エントリー候補として扱う反発回数の上限

    Returns
    -------
    result
        各日がエントリー候補かどうかを示すbooleanのSeries
    """

    if max_bounces is None:
        max_bounces = MAX_ENTRY_BOUNCES

    return bounce_number.notna() & (bounce_number <= max_bounces)

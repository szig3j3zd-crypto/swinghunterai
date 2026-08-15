from config.config import MAX_HOLDING_DAYS
from rules.entry_rule import evaluate_entry

DEFAULT_MODULES = ("ma_order", "perfect_golden_cross")


def find_historical_signals(df, direction, min_history=100, timeframe="daily",
                             modules=None, ma_mode="full", bounce_merge_within=None):

    """
    過去データを1本ずつ遡って、その時点までの情報だけでエントリー候補に
    なっていた足を探す（先読みを避けるため、各時点の判定はそこまでの
    データのみで行う）。

    Parameters
    ----------
    df
        date, open, high, low, close, volume, volume_ratio,
        sma5, sma20, sma60 列を持つ株価DataFrame（単一銘柄、日付順ソート済み）。
        日足・週足・月足など、timeframeに応じた足のDataFrameを渡す

    direction
        "long" または "short"

    min_history
        判定を開始する最低行数（指標が安定するまでの助走期間）

    timeframe
        "daily" | "weekly" | "monthly"

    modules
        使用するモジュール名のリスト。Noneならconfig既定値
        （並び順＋完全ゴールデンクロス）を使う

    ma_mode
        "ma_order"選択時の並び順バリエーション。"full"（デフォルト）、"two_line"、
        "full_100"のいずれか

    bounce_merge_within
        近接した反発をまとめる間隔（行数ベース）。Noneならconfig既定値を使う

    Returns
    -------
    signals
        エントリー候補になった足ごとの結果（entry_index, entry_date,
        evaluate_entryの戻り値）のリスト
    """

    if modules is None:
        modules = DEFAULT_MODULES

    signals = []

    for i in range(min_history, len(df)):

        window_df = df.iloc[:i + 1]

        result = evaluate_entry(
            window_df,
            direction,
            modules=modules,
            ma_mode=ma_mode,
            bounce_merge_within=bounce_merge_within,
        )

        if result["is_entry_candidate"]:
            signals.append({
                "entry_index": i,
                "entry_date": df["date"].iloc[i],
                **result,
            })

    return signals


def simulate_trade(df, entry_index, direction, stop_loss_price, take_profit_price,
                    max_holding_days=None):

    """
    エントリー翌日以降を1日ずつ進め、損切・利確・時間切れのいずれかで
    決済されるまでをシミュレートする。

    同じ日に損切・利確の両方の条件を満たした場合は、保守的に
    損切が先に発生したものとして扱う。

    Parameters
    ----------
    df
        date, high, low, close 列を持つ株価DataFrame（単一銘柄）

    entry_index
        エントリー日の行番号（dfの位置インデックス）

    direction
        "long" または "short"

    stop_loss_price, take_profit_price
        損切価格・利確価格（Noneの場合はその条件を評価しない）

    max_holding_days
        Noneならconfig.MAX_HOLDING_DAYSを使う

    Returns
    -------
    result
        exit_index, exit_date, exit_price, exit_reason
        （"stop_loss" | "take_profit" | "timeout" | "data_ended"）、
        days_held, return_pct を持つdict
    """

    if max_holding_days is None:
        max_holding_days = MAX_HOLDING_DAYS

    entry_price = df["close"].iloc[entry_index]

    for offset in range(1, max_holding_days + 1):

        idx = entry_index + offset

        if idx >= len(df):
            return _build_result(
                df, entry_index, entry_price, idx - 1, offset - 1,
                direction, "data_ended"
            )

        row = df.iloc[idx]

        if direction == "long":
            if stop_loss_price is not None and row["low"] <= stop_loss_price:
                return _build_result(
                    df, entry_index, entry_price, idx, offset,
                    direction, "stop_loss", exit_price=stop_loss_price
                )

            if take_profit_price is not None and row["high"] >= take_profit_price:
                return _build_result(
                    df, entry_index, entry_price, idx, offset,
                    direction, "take_profit", exit_price=take_profit_price
                )

        else:
            if stop_loss_price is not None and row["high"] >= stop_loss_price:
                return _build_result(
                    df, entry_index, entry_price, idx, offset,
                    direction, "stop_loss", exit_price=stop_loss_price
                )

            if take_profit_price is not None and row["low"] <= take_profit_price:
                return _build_result(
                    df, entry_index, entry_price, idx, offset,
                    direction, "take_profit", exit_price=take_profit_price
                )

    idx = entry_index + max_holding_days

    return _build_result(
        df, entry_index, entry_price, idx, max_holding_days,
        direction, "timeout"
    )


def run_backtest(df, direction, min_history=100, max_holding_days=None,
                  timeframe="daily", modules=None, ma_mode="full",
                  bounce_merge_within=None):

    """
    銘柄1件分のシグナル抽出とトレードシミュレーションをまとめて実行する

    Parameters
    ----------
    timeframe
        "daily" | "weekly" | "monthly"

    modules
        使用するモジュール名のリスト。Noneならconfig既定値
        （並び順＋完全ゴールデンクロス）を使う

    ma_mode
        "ma_order"選択時の並び順バリエーション。"full"（デフォルト）、"two_line"、
        "full_100"のいずれか

    bounce_merge_within
        近接した反発をまとめる間隔（行数ベース）。Noneならconfig既定値を使う

    Returns
    -------
    trades
        find_historical_signals()とsimulate_trade()の結果を統合した
        トレード結果のリスト
    """

    signals = find_historical_signals(
        df, direction, min_history=min_history, timeframe=timeframe,
        modules=modules, ma_mode=ma_mode, bounce_merge_within=bounce_merge_within,
    )

    trades = []

    for signal in signals:

        trade_result = simulate_trade(
            df,
            entry_index=signal["entry_index"],
            direction=direction,
            stop_loss_price=signal["stop_loss_price"],
            take_profit_price=signal["take_profit_price"],
            max_holding_days=max_holding_days,
        )

        trades.append({
            **signal,
            **trade_result,
        })

    return trades


def _build_result(df, entry_index, entry_price, exit_index, days_held,
                   direction, exit_reason, exit_price=None):

    """
    トレード結果の組み立て
    """

    if exit_price is None:
        exit_price = df["close"].iloc[exit_index]

    if direction == "long":
        return_pct = (exit_price - entry_price) / entry_price
    else:
        return_pct = (entry_price - exit_price) / entry_price

    return {
        "exit_index": exit_index,
        "exit_date": df["date"].iloc[exit_index],
        "exit_price": exit_price,
        "exit_reason": exit_reason,
        "days_held": days_held,
        "return_pct": return_pct,
    }

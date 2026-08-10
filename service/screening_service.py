from concurrent.futures import ThreadPoolExecutor

from config.config import LARGE_CAP_MARKET_CAP_THRESHOLD
from data.market_cap_reader import get_market_cap
from database.stock_master_reader import get_active_stocks
from database.stock_price_reader import get_stock_data
from indicators.moving_average import calculate_moving_average
from indicators.resample import resample_to_weekly
from indicators.volume import calculate_volume_indicators
from rules.entry_rule import evaluate_entry
from rules.screening_filters import market_cap_filter_is_active, passes_market_cap_filter

MARKET_CAP_FETCH_WORKERS = 8

# モジュール未指定時のデフォルト（並び順3本版＋完全ゴールデンクロス）
DEFAULT_MODULES = ("ma_order", "perfect_golden_cross")

MODULE_LABELS = {
    "ma_order": "並び順",
    "perfect_golden_cross": "完全ゴールデンクロス",
    "bounce": "反発",
    "parallel_rise": "並走上昇",
    "half_signal": "半分シグナル",
}

# ショート方向では表裏の関係になるモジュールのみ、表示ラベルを上書きする
# （並び順・反発・半分シグナルは同じ言葉のままで方向だけ逆になるため上書き不要）
MODULE_LABELS_SHORT_OVERRIDE = {
    "perfect_golden_cross": "完全デッドクロス",
    "parallel_rise": "並走下降",
}


def _module_label(name, direction):

    """
    候補理由表示用のモジュール名。ショート方向では完全ゴールデンクロス→
    完全デッドクロス、並走上昇→並走下降のように表示だけ変える
    （判定ロジック自体はentry_signal_spec.md記載の通りモジュール名は共通）
    """

    if direction == "short" and name in MODULE_LABELS_SHORT_OVERRIDE:
        return MODULE_LABELS_SHORT_OVERRIDE[name]

    return MODULE_LABELS.get(name, name)


def get_large_cap_stocks():

    """
    大型株（時価総額がLARGE_CAP_MARKET_CAP_THRESHOLD以上）の銘柄一覧を取得する

    IRBANKの銘柄一覧にTOPIX Core30/Large70の規模区分が無いため、
    stock_master.market_cap（IRBANKの/screeningから取得）で代替する
    """

    stocks = get_active_stocks()

    return stocks[stocks["market_cap"] >= LARGE_CAP_MARKET_CAP_THRESHOLD]


def get_nikkei225_stocks():

    """
    日経225採用銘柄の一覧を取得する
    """

    stocks = get_active_stocks()

    return stocks[stocks["nikkei225"] == 1]


def get_jpx400_stocks():

    """
    JPX日経400採用銘柄の一覧を取得する
    """

    stocks = get_active_stocks()

    return stocks[stocks["jpx400"] == 1]


def get_prime_stocks():

    """
    東証プライム（内国株式）の銘柄一覧を取得する
    """

    stocks = get_active_stocks()

    return stocks[stocks["market"] == "プライム（内国株式）"]


def get_today_candidates(direction="long", stocks=None, min_history=100,
                          timeframe="daily", modules=None, ma_mode="full",
                          min_volume=None, min_price=None,
                          max_price=None, min_market_cap=None, max_market_cap=None):

    """
    今日の売買候補を抽出する

    Parameters
    ----------
    direction
        "long" または "short"

    stocks
        対象銘柄のDataFrame（code, company_name, ticker列を含む）。
        Noneなら東証プライム銘柄を対象にする

    min_history
        指標が安定するまでの最低必要行数。これに満たない銘柄はスキップする

    timeframe
        "daily" または "weekly"。判定に使う足（日足 or 週足リサンプル）の選択に使う

    modules
        使用するモジュール名のリスト。Noneならconfig既定値
        （DEFAULT_MODULES = 並び順＋完全ゴールデンクロス）を使う。
        entry_signal_spec.mdの各モジュール定義を参照

    ma_mode
        "ma_order"選択時の並び順バリエーション。"full"（デフォルト）または"two_line"

    min_volume, min_price, max_price
        出来高・株価フィルタの上書き値。Noneならconfig既定値を使う

    min_market_cap, max_market_cap
        時価総額フィルタの上書き値（円）。Noneならconfig既定値を使う。
        DBに時価総額を保存していないため、他の条件を通過した候補にのみ
        Yahoo Financeへライブ問い合わせして絞り込む（全銘柄には適用しない）

    Returns
    -------
    candidates
        スコア降順に並んだ候補のリスト（dict）。
        code, company_name と evaluate_entry() の戻り値を含む
    """

    if stocks is None:
        stocks = get_prime_stocks()

    if modules is None:
        modules = DEFAULT_MODULES

    candidates = []
    ticker_by_code = {}

    for _, stock in stocks.iterrows():

        code = stock["code"]
        company_name = stock["company_name"]
        ticker_by_code[code] = stock["ticker"]

        try:
            result = _evaluate_stock(
                code, direction, timeframe, min_history, modules, ma_mode,
                min_volume, min_price, max_price,
            )

            if result["is_entry_candidate"]:
                candidates.append({
                    "code": code,
                    "company_name": company_name,
                    "timeframe": timeframe,
                    **result,
                })

        except Exception:
            continue

    candidates = _filter_by_market_cap(
        candidates, ticker_by_code, min_market_cap, max_market_cap
    )

    candidates.sort(key=lambda c: c["score"]["total_score"], reverse=True)

    return candidates


def get_today_watchlist(direction="long", stocks=None, min_history=100,
                         timeframe="daily", modules=None, ma_mode="full",
                         min_volume=None, min_price=None, max_price=None):

    """
    今日の監視銘柄（反発モジュールでMA20を下回っている最中の銘柄）を抽出する

    entry_signal_spec.md 5章の反発モジュールでのみ発生する。
    "bounce"モジュールを含まないmodulesを指定した場合は常に空リストを返す
    """

    if stocks is None:
        stocks = get_prime_stocks()

    if modules is None:
        modules = DEFAULT_MODULES

    watchlist = []

    for _, stock in stocks.iterrows():

        code = stock["code"]
        company_name = stock["company_name"]

        try:
            result = _evaluate_stock(
                code, direction, timeframe, min_history, modules, ma_mode,
                min_volume, min_price, max_price,
            )

            if result.get("is_watch_candidate"):
                watchlist.append({
                    "code": code,
                    "company_name": company_name,
                    "timeframe": timeframe,
                    **result,
                })

        except Exception:
            continue

    return watchlist


def get_stock_chart_data(code, timeframe="daily"):

    """
    チャート表示用の株価・移動平均・出来高データを取得する

    Parameters
    ----------
    code
        銘柄コード

    timeframe
        "daily" または "weekly"

    Returns
    -------
    df
        date, open, high, low, close, volume, sma5, sma20, sma60 列を持つ
        DataFrame（日付順ソート済み）
    """

    df = get_stock_data(code)

    if timeframe == "weekly":
        df = resample_to_weekly(df)

    df = calculate_moving_average(df)
    df = calculate_volume_indicators(df)

    return df


def evaluate_single_stock(code, direction="long", timeframe="daily", min_history=100,
                           modules=None, ma_mode="full",
                           min_volume=None, min_price=None, max_price=None):

    """
    個別銘柄1件を直接評価する（銘柄検索機能用）

    get_today_candidates()と違い、is_entry_candidateがFalseの場合も
    見送り理由（reason）を含めてそのまま返す

    Parameters
    ----------
    code
        銘柄コード

    その他
        get_today_candidates()と同じ

    Returns
    -------
    result
        code, company_name と evaluate_entry() の戻り値を持つdict。
        銘柄が見つからない、または評価に必要なデータが不足している場合は
        error キーにメッセージを持つdict
    """

    if modules is None:
        modules = DEFAULT_MODULES

    stocks = get_active_stocks()
    matched = stocks[stocks["code"] == code]

    if matched.empty:
        return {"code": code, "error": "銘柄が見つかりません"}

    company_name = matched.iloc[0]["company_name"]

    try:
        result = _evaluate_stock(
            code, direction, timeframe, min_history, modules, ma_mode,
            min_volume, min_price, max_price,
        )
    except Exception:
        return {
            "code": code,
            "company_name": company_name,
            "error": "株価データが不足しているため評価できません",
        }

    return {
        "code": code,
        "company_name": company_name,
        "timeframe": timeframe,
        **result,
    }


def _evaluate_stock(code, direction, timeframe, min_history, modules, ma_mode,
                     min_volume, min_price, max_price):

    """
    銘柄1件分のデータ取得〜エントリー判定をまとめて実行する

    get_today_candidates()とevaluate_single_stock()の共通処理
    """

    df = get_stock_data(code)

    if timeframe == "weekly":
        df = resample_to_weekly(df)

    if len(df) < min_history:
        raise ValueError("insufficient_history")

    df = calculate_moving_average(df)
    df = calculate_volume_indicators(df)

    return evaluate_entry(
        df,
        direction,
        modules=modules,
        ma_mode=ma_mode,
        min_volume=min_volume,
        min_price=min_price,
        max_price=max_price,
    )


def _filter_by_market_cap(candidates, ticker_by_code, min_market_cap, max_market_cap):

    """
    候補（他の条件を通過済み）にのみ時価総額フィルタを適用する

    候補数は通常数十件程度のため、Yahoo Financeへの問い合わせを
    スレッドプールで並列実行して待ち時間を抑える
    """

    if not candidates:
        return candidates

    if not market_cap_filter_is_active(min_market_cap, max_market_cap):
        return candidates

    codes = [candidate["code"] for candidate in candidates]

    with ThreadPoolExecutor(max_workers=MARKET_CAP_FETCH_WORKERS) as executor:
        market_caps = list(
            executor.map(lambda code: get_market_cap(ticker_by_code[code]), codes)
        )

    return [
        candidate
        for candidate, market_cap in zip(candidates, market_caps)
        if passes_market_cap_filter(market_cap, min_market_cap, max_market_cap)
    ]


def format_reason(candidate):

    """
    候補になった判定理由を日本語の短い説明文にする

    選択したモジュール名を「＋」で連結する。反発モジュールを含む場合は
    反発回数（何発目か）を付記する
    """

    direction = candidate.get("direction")
    labels = [_module_label(name, direction) for name in candidate.get("modules", [])]
    reason = "＋".join(labels) if labels else "候補条件"

    if candidate.get("bounce_number") is not None:
        reason += f"（反発{candidate['bounce_number']}回目）"

    return reason

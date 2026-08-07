from analysis.support_resistance import detect_resistance_lines, detect_support_lines
from database.stock_master_reader import get_active_stocks
from database.stock_price_reader import get_stock_data
from indicators.moving_average import calculate_moving_average
from indicators.volume import calculate_volume_indicators
from rules.entry_rule import evaluate_entry


def get_large_cap_stocks():

    """
    大型株（TOPIX Core30 + Large70）の銘柄一覧を取得する
    """

    stocks = get_active_stocks()

    return stocks[stocks["size_class"].isin(["TOPIX Core30", "TOPIX Large70"])]


def get_prime_stocks():

    """
    東証プライム（内国株式）の銘柄一覧を取得する
    """

    stocks = get_active_stocks()

    return stocks[stocks["market"] == "プライム（内国株式）"]


def get_today_candidates(direction="long", stocks=None, min_history=100):

    """
    今日の売買候補を抽出する

    Parameters
    ----------
    direction
        "long" または "short"

    stocks
        対象銘柄のDataFrame（code, company_name列を含む）。
        Noneなら東証プライム銘柄を対象にする

    min_history
        指標が安定するまでの最低必要行数。これに満たない銘柄はスキップする

    Returns
    -------
    candidates
        スコア降順に並んだ候補のリスト（dict）。
        code, company_name と evaluate_entry() の戻り値を含む
    """

    if stocks is None:
        stocks = get_prime_stocks()

    candidates = []

    for _, stock in stocks.iterrows():

        code = stock["code"]
        company_name = stock["company_name"]

        try:
            df = get_stock_data(code)

            if len(df) < min_history:
                continue

            df = calculate_moving_average(df)
            df = calculate_volume_indicators(df)

            if direction == "long":
                support_lines = detect_support_lines(df, timeframe="daily")
                resistance_lines = None
            else:
                support_lines = None
                resistance_lines = detect_resistance_lines(df, timeframe="daily")

            result = evaluate_entry(
                df,
                direction,
                support_lines=support_lines,
                resistance_lines=resistance_lines,
            )

            if result["is_entry_candidate"]:
                candidates.append({
                    "code": code,
                    "company_name": company_name,
                    **result,
                })

        except Exception:
            continue

    candidates.sort(key=lambda c: c["score"]["total_score"], reverse=True)

    return candidates


def format_reason(candidate):

    """
    候補になった判定理由を日本語の短い説明文にする
    """

    pattern_label = "支持線/抵抗線付近" if candidate["pattern"] == "A" else "20日線付近"

    return f"{pattern_label}の半分シグナル（反発{candidate['bounce_number']}回目）"

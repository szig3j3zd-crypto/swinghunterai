from pathlib import Path

import pandas as pd

from database.stock_master_repository import update_classification

NIKKEI225_PATH = "data/stock_data/master/nikkei225.csv"


def main():
    """
    JPX公式CSVから銘柄マスタを更新
    """

    print("=" * 40)
    print("銘柄マスタ更新開始")
    print("=" * 40)

    # 東証上場銘柄一覧
    prime_df = pd.read_csv(
        "data/stock_data/master/prime.csv",
        encoding="cp932"
    )

    # JPX400一覧
    jpx400_df = pd.read_csv(
        "data/stock_data/master/jpx400.csv",
        encoding="cp932"
    )

    print(f"東証上場銘柄読込 : {len(prime_df)}件")
    print()

    # 日経225一覧（任意。無ければ全銘柄nikkei225=0のまま更新する）
    # ヘッダー無し・1列（コードのみ）のCSVを想定
    if Path(NIKKEI225_PATH).exists():

        nikkei225_df = pd.read_csv(
            NIKKEI225_PATH,
            encoding="cp932",
            header=None
        )

        nikkei225_codes = set(
            nikkei225_df[0].astype(str).str.strip()
        )

        print(f"日経225読込 : {len(nikkei225_codes)}件")

    else:

        nikkei225_codes = set()

        print(
            f"日経225一覧が見つかりません（{NIKKEI225_PATH}）。"
            "nikkei225は全銘柄0のまま更新します"
        )

    print()

    # ==========================
    # 市場区分件数
    # ==========================

    market_count = (
        prime_df["市場・商品区分"]
        .value_counts()
    )

    prime_count = market_count.get(
        "プライム（内国株式）",
        0
    )

    standard_count = market_count.get(
        "スタンダード（内国株式）",
        0
    )

    growth_count = market_count.get(
        "グロース（内国株式）",
        0
    )

    other_count = (
        len(prime_df)
        - prime_count
        - standard_count
        - growth_count
    )

    print("市場区分")

    print(
        f"  プライム      : {prime_count}件"
    )

    print(
        f"  スタンダード : {standard_count}件"
    )

    print(
        f"  グロース     : {growth_count}件"
    )

    print(
        f"  その他       : {other_count}件"
    )

    print()

    print(
        f"JPX400読込 : {len(jpx400_df)}件"
    )

    print()

    # ==========================
    # JPX400判定
    # ==========================

    jpx400_codes = set(
        jpx400_df["コード"].astype(str)
    )

    stocks = []

    for _, row in prime_df.iterrows():

        code = str(
            row["コード"]
        )

        ticker = f"{code}.T"

        company_name = row["銘柄名"]

        market = row["市場・商品区分"]

        size_class = row["規模区分"]

        jpx400 = (
            1
            if code in jpx400_codes
            else 0
        )

        nikkei225 = (
            1
            if code in nikkei225_codes
            else 0
        )

        stocks.append(
            (
                code,
                ticker,
                company_name,
                market,
                jpx400,
                nikkei225,
                size_class
            )
        )

    print("更新開始...")
    print()

    update_classification(
        stocks
    )

    print(
        f"更新完了 : {len(stocks)}件"
    )

    print("=" * 40)
    print("銘柄マスタ更新完了")
    print("=" * 40)


if __name__ == "__main__":
    main()
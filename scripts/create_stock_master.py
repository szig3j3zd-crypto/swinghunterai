import sys
from pathlib import Path

# python scripts/xxx.py で直接実行した場合、sys.path[0]はscripts/自身になり
# プロジェクトルートが見えないため、絶対importが解決できるよう明示的に追加する
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.provider_manager import ProviderManager

from database.stock_master_repository import (
    create_table,
    delete_all,
    add_stocks,
)


def main():

    print("=" * 40)
    print("銘柄マスター作成開始")
    print("=" * 40)

    manager = ProviderManager()

    provider, df = manager.get_stock_list()

    if df.empty:

        print("銘柄一覧取得失敗")

        return

    print(f"取得件数 : {len(df)}")

    create_table()

    delete_all()

    stock_list = []

    for _, row in df.iterrows():

        code = str(row["Code"])[:4]

        ticker = f"{code}.T"

        company_name = row["CoName"]

        market = row["MktNm"]

        jpx400 = 0

        nikkei225 = 0

        size_class = row["ScaleCat"]

        market_cap = (
            row["MarketCap"]
            if "MarketCap" in df.columns
            else None
        )

        stock_list.append(
            (
                code,
                ticker,
                company_name,
                market,
                jpx400,
                nikkei225,
                size_class,
                market_cap,
            )
        )

    add_stocks(stock_list)

    print()
    print("=" * 40)
    print("保存完了")
    print(f"保存件数 : {len(stock_list)}")
    print("=" * 40)


if __name__ == "__main__":
    main()
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

    df, provider = manager.get_stock_list()

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

        stock_list.append(
            (
                code,
                ticker,
                company_name,
                market,
                jpx400,
                nikkei225,
                size_class,
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
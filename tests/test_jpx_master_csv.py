import pandas as pd


def test_prime_master_csv_has_expected_columns():
    df = pd.read_csv(
        "data/stock_data/master/prime.csv",
        encoding="cp932",
    )

    for column in ["コード", "銘柄名", "市場・商品区分", "規模区分"]:
        assert column in df.columns

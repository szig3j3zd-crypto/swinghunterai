import pandas as pd


def load_stock_data(file_path):
    """
    CSVから株価データを読み込む
    """

    data = pd.read_csv(
        file_path,
        encoding="utf-8-sig"
    )

    return data
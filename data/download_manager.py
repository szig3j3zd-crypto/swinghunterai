from data.provider_manager import ProviderManager


class DownloadManager:

    def __init__(self):

        self.provider_manager = ProviderManager()

    def download(
        self,
        ticker,
        latest_date=None,
        period="1y"
    ):
        """
        Providerから株価データを取得する。

        Parameters
        ----------
        ticker : str
            ティッカー

        latest_date : str | None
            保存済み最新日付
            None の場合は period を利用して取得する

        period : str
            初回取得期間
            例:
                "1y"
                "3y"
                "5y"
                "max"
        """

        return self.provider_manager.get_stock_data(
            ticker=ticker,
            latest_date=latest_date,
            period=period
        )
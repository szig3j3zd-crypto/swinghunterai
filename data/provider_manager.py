import pandas as pd

from data.providers.yahoo_provider import YahooProvider
from data.providers.jquants_provider import JQuantsProvider
from data.providers.irbank_provider import IRBankProvider


class ProviderManager:
    """
    データ取得Provider管理クラス
    """

    def __init__(self):

        # 株価取得: IRBANKは1日の取得容量が小さく全銘柄更新に耐えないため使わない
        self.price_providers = [
            YahooProvider(),
            JQuantsProvider(),
        ]

        # 銘柄一覧・企業情報取得: IRBANKを優先する
        self.list_providers = [
            IRBankProvider(),
            JQuantsProvider(),
            YahooProvider(),
        ]

    def get_stock_data(
        self,
        ticker,
        latest_date=None,
        period="1y"
    ):
        """
        株価取得

        Providerが例外を送出した場合のみ次のProviderへフォールバックする。
        空のDataFrame（「新しいデータなし＝既に最新」という正常な結果）は
        フォールバックせずそのまま確定として返す（2026-09-13改訂。以前は
        空のDataFrameも"取得失敗"扱いにしてフォールバックしていたため、
        既に最新の銘柄1つ1つに対して常に次のProvider（J-Quants）へも
        無駄な問い合わせが発生し、全銘柄更新が不必要に遅くなっていた）
        """

        for provider in self.price_providers:

            if not provider.is_available():
                continue

            print(f"Provider : {provider.name}")

            try:

                data = provider.get_stock_data(
                    ticker=ticker,
                    latest_date=latest_date,
                    period=period
                )

                return provider.name, data

            except Exception as e:

                print(e)
                print("取得失敗")

        return None, pd.DataFrame()

    def get_stock_list(self):
        """
        銘柄一覧取得
        """

        for provider in self.list_providers:

            if not provider.is_available():
                continue

            print(f"Provider : {provider.name}")

            try:

                data = provider.get_stock_list()

                if data is not None and not data.empty:

                    return provider.name, data

                print("取得失敗")

            except Exception as e:

                print(e)
                print("取得失敗")

        return None, pd.DataFrame()
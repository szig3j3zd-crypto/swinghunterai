from data.provider_manager import ProviderManager


_manager = ProviderManager()


def get_stock_data(
    ticker,
    latest_date=None
):

    return _manager.get_stock_data(
        ticker,
        latest_date
    )
import pandas as pd

from data.provider_manager import ProviderManager
from data.providers.irbank_provider import IRBankProvider
from data.providers.yahoo_provider import YahooProvider
from data.providers.jquants_provider import JQuantsProvider


class _FakeProvider:
    """
    ProviderManager.get_stock_data()のフォールバック挙動だけを検証する
    ための最小限のダミーProvider。resultを返すか、errorがあれば
    get_stock_data()でそれを送出する
    """

    def __init__(self, name, available=True, result=None, error=None):
        self._name = name
        self._available = available
        self._result = result
        self._error = error
        self.called = False

    @property
    def name(self):
        return self._name

    def is_available(self):
        return self._available

    def get_stock_data(self, ticker, latest_date=None, period="1y"):
        self.called = True

        if self._error is not None:
            raise self._error

        return self._result


def test_yahoo_is_tried_before_jquants_for_prices():
    manager = ProviderManager()

    assert len(manager.price_providers) == 2
    assert isinstance(manager.price_providers[0], YahooProvider)
    assert isinstance(manager.price_providers[1], JQuantsProvider)


def test_price_provider_names():
    manager = ProviderManager()

    names = [provider.name for provider in manager.price_providers]

    assert names == ["Yahoo", "J-Quants"]


def test_irbank_is_tried_before_jquants_and_yahoo_for_lists():
    manager = ProviderManager()

    assert len(manager.list_providers) == 3
    assert isinstance(manager.list_providers[0], IRBankProvider)
    assert isinstance(manager.list_providers[1], JQuantsProvider)
    assert isinstance(manager.list_providers[2], YahooProvider)


def test_list_provider_names():
    manager = ProviderManager()

    names = [provider.name for provider in manager.list_providers]

    assert names == ["IRBANK", "J-Quants", "Yahoo"]


def test_get_stock_data_does_not_fall_back_when_first_provider_returns_no_new_data():
    """
    2026-09-13修正: 最初のProviderが「新しいデータなし（既に最新）」と
    正常に判定した場合、それは取得失敗ではないため、次のProviderへは
    フォールバックしない。以前はこの区別が無く、既に最新の銘柄1つ1つに
    対して常に次のProviderへも無駄な問い合わせが発生し、全銘柄更新が
    不必要に遅くなっていた
    """

    manager = ProviderManager()
    first = _FakeProvider("First", result=pd.DataFrame())
    second = _FakeProvider("Second", result=pd.DataFrame({"Close": [100]}))
    manager.price_providers = [first, second]

    provider_name, data = manager.get_stock_data("7203.T")

    assert provider_name == "First"
    assert data.empty
    assert second.called is False


def test_get_stock_data_falls_back_when_first_provider_raises():
    manager = ProviderManager()
    first = _FakeProvider("First", error=RuntimeError("boom"))
    second_data = pd.DataFrame({"Close": [100]})
    second = _FakeProvider("Second", result=second_data)
    manager.price_providers = [first, second]

    provider_name, data = manager.get_stock_data("7203.T")

    assert provider_name == "Second"
    assert data is second_data


def test_get_stock_data_returns_none_when_all_providers_raise():
    manager = ProviderManager()
    manager.price_providers = [
        _FakeProvider("First", error=RuntimeError("boom")),
        _FakeProvider("Second", error=RuntimeError("boom")),
    ]

    provider_name, data = manager.get_stock_data("7203.T")

    assert provider_name is None
    assert data.empty


def test_get_stock_data_skips_unavailable_providers():
    manager = ProviderManager()
    unavailable = _FakeProvider("Unavailable", available=False)
    second_data = pd.DataFrame({"Close": [100]})
    second = _FakeProvider("Second", result=second_data)
    manager.price_providers = [unavailable, second]

    provider_name, data = manager.get_stock_data("7203.T")

    assert provider_name == "Second"
    assert unavailable.called is False

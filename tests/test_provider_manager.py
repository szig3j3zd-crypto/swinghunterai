from data.provider_manager import ProviderManager
from data.providers.irbank_provider import IRBankProvider
from data.providers.yahoo_provider import YahooProvider
from data.providers.jquants_provider import JQuantsProvider


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

from data.provider_manager import ProviderManager
from data.providers.yahoo_provider import YahooProvider
from data.providers.jquants_provider import JQuantsProvider


def test_yahoo_is_tried_before_jquants():
    manager = ProviderManager()

    assert len(manager.providers) == 2
    assert isinstance(manager.providers[0], YahooProvider)
    assert isinstance(manager.providers[1], JQuantsProvider)


def test_provider_names():
    manager = ProviderManager()

    names = [provider.name for provider in manager.providers]

    assert names == ["Yahoo", "J-Quants"]

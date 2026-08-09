from data.provider_manager import ProviderManager
from data.providers.irbank_provider import IRBankProvider
from data.providers.yahoo_provider import YahooProvider
from data.providers.jquants_provider import JQuantsProvider


def test_irbank_is_tried_before_jquants_and_yahoo():
    manager = ProviderManager()

    assert len(manager.providers) == 3
    assert isinstance(manager.providers[0], IRBankProvider)
    assert isinstance(manager.providers[1], JQuantsProvider)
    assert isinstance(manager.providers[2], YahooProvider)


def test_provider_names():
    manager = ProviderManager()

    names = [provider.name for provider in manager.providers]

    assert names == ["IRBANK", "J-Quants", "Yahoo"]

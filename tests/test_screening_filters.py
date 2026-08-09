from rules.screening_filters import (
    market_cap_filter_is_active,
    passes_market_cap_filter,
    passes_price_filter,
    passes_volume_filter,
)


def test_passes_volume_filter_true_when_above_minimum():
    assert passes_volume_filter(600_000, min_volume=500_000) is True


def test_passes_volume_filter_false_when_below_minimum():
    assert passes_volume_filter(100_000, min_volume=500_000) is False


def test_passes_volume_filter_falls_back_to_config_default():
    # min_volume=Noneはconfig.MIN_VOLUME（デフォルト50万株）にフォールバックする
    assert passes_volume_filter(1, min_volume=None) is False
    assert passes_volume_filter(600_000, min_volume=None) is True


def test_passes_price_filter_true_when_within_range():
    assert passes_price_filter(1000, min_price=500, max_price=2000) is True


def test_passes_price_filter_false_when_below_minimum():
    assert passes_price_filter(100, min_price=500, max_price=2000) is False


def test_passes_price_filter_false_when_above_maximum():
    assert passes_price_filter(3000, min_price=500, max_price=2000) is False


def test_passes_price_filter_falls_back_to_config_default():
    # min_price/max_price=Noneはconfig.MIN_PRICE/MAX_PRICE
    # （デフォルト1000〜5000円）にフォールバックする
    assert passes_price_filter(1, min_price=None, max_price=None) is False
    assert passes_price_filter(3000, min_price=None, max_price=None) is True


def test_passes_price_filter_true_when_explicitly_disabled():
    # min_price=0, max_price=infはUI側の「0で無効」規約に対応する
    assert passes_price_filter(1, min_price=0, max_price=float("inf")) is True


def test_passes_market_cap_filter_true_when_above_minimum():
    assert passes_market_cap_filter(
        600_000_000_000, min_market_cap=500_000_000_000
    ) is True


def test_passes_market_cap_filter_false_when_below_minimum():
    assert passes_market_cap_filter(
        100_000_000_000, min_market_cap=500_000_000_000
    ) is False


def test_passes_market_cap_filter_false_when_fetch_failed_and_filter_active():
    # market_cap取得失敗（None）時、フィルタが有効なら安全側（除外）に倒す
    assert passes_market_cap_filter(None, min_market_cap=500_000_000_000) is False


def test_passes_market_cap_filter_zero_min_disables_filter():
    # min_market_cap=0は「フィルタなし」を意味する（UI側の「0で無効」規約）。
    # 取得失敗（None）でも除外しない
    assert passes_market_cap_filter(None, min_market_cap=0) is True
    assert passes_market_cap_filter(1, min_market_cap=0) is True


def test_market_cap_filter_is_active():
    assert market_cap_filter_is_active(min_market_cap=500_000_000_000) is True
    assert market_cap_filter_is_active(min_market_cap=0, max_market_cap=None) is False
    assert market_cap_filter_is_active(min_market_cap=None, max_market_cap=None) is True  # config既定値

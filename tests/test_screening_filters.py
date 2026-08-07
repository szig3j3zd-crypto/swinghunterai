from rules.screening_filters import passes_price_filter, passes_volume_filter


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


def test_passes_price_filter_true_when_no_range_set():
    assert passes_price_filter(1, min_price=None, max_price=None) is True

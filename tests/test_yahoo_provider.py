from unittest.mock import MagicMock, patch

import pandas as pd

from data.providers.yahoo_provider import YahooProvider


def test_get_stock_data_returns_empty_dataframe_when_no_new_rows():
    """
    Yahoo自身への問い合わせが成功し、単に新しい行が無かった（既に最新）
    場合は空のDataFrameを返す（例外は送出しない）
    """

    provider = YahooProvider()
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()

    with patch("data.providers.yahoo_provider.yf.Ticker", return_value=mock_ticker):
        result = provider.get_stock_data("7203.T", latest_date="2026-01-01")

    assert result.empty


def test_get_stock_data_raises_after_exhausting_retries():
    """
    2026-09-13追加: 全リトライが通信失敗で尽きた場合は例外を送出する。
    以前は空のDataFrameを返しており、ProviderManagerが「新しいデータなし」
    と区別できず、本当の取得失敗のたびに無駄なJ-Quantsフォールバックが
    発生していた
    """

    provider = YahooProvider()
    mock_ticker = MagicMock()
    mock_ticker.history.side_effect = RuntimeError("boom")

    with patch("data.providers.yahoo_provider.yf.Ticker", return_value=mock_ticker), \
            patch("data.providers.yahoo_provider.time.sleep"):
        try:
            provider.get_stock_data("7203.T", retry=2)
        except RuntimeError as e:
            assert str(e) == "boom"
        else:
            raise AssertionError("expected RuntimeError to be raised")


def test_get_stock_data_succeeds_after_transient_failure():
    """
    リトライ途中で成功すれば、例外を送出せず正常にデータを返す
    """

    provider = YahooProvider()
    mock_ticker = MagicMock()
    success_df = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [110.0],
            "Low": [90.0],
            "Close": [105.0],
            "Volume": [1000],
        },
        index=pd.DatetimeIndex(["2026-01-02"], name="Date"),
    )
    mock_ticker.history.side_effect = [RuntimeError("boom"), success_df]

    with patch("data.providers.yahoo_provider.yf.Ticker", return_value=mock_ticker), \
            patch("data.providers.yahoo_provider.time.sleep"):
        result = provider.get_stock_data("7203.T", retry=3)

    assert not result.empty
    assert list(result.columns) == ["Date", "Open", "High", "Low", "Close", "Volume"]

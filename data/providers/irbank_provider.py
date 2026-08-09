import time
from datetime import datetime, timedelta

import pandas as pd
import requests

from config.settings import IRBANK_API_KEY, IRBANK_BASE_URL
from data.providers.base_provider import BaseProvider

PERIOD_DAYS = {
    "1y": 365,
    "3y": 365 * 3,
    "5y": 365 * 5,
    "10y": 365 * 10,
}

# IRBANKの市場区分（英語）→ 既存DB・J-Quantsに揃えた表記
MARKET_LABEL_MAP = {
    "Prime": "プライム（内国株式）",
    "Standard": "スタンダード（内国株式）",
    "Growth": "グロース（内国株式）",
}


class IRBankProvider(BaseProvider):
    """
    IRBANK Provider
    """

    @property
    def name(self):
        return "IRBANK"

    def is_available(self):
        """
        APIキーが設定されていれば利用可能
        """
        return IRBANK_API_KEY != ""

    def _headers(self):

        return {
            "Authorization": f"Bearer {IRBANK_API_KEY}"
        }

    def _get(self, path, params, retry=3):
        """
        GETリクエスト（リトライ付き）

        失敗時（全リトライ消化）はNoneを返す
        """

        for attempt in range(retry):

            try:

                response = requests.get(
                    f"{IRBANK_BASE_URL}{path}",
                    headers=self._headers(),
                    params=params,
                    timeout=10
                )

                response.raise_for_status()

                return response.json()

            except Exception as e:

                print(
                    f"IRBANK {path} 通信失敗 "
                    f"({attempt + 1}/{retry})"
                )

                print(e)

                time.sleep(2)

        return None

    def _get_paginated(self, path, params, list_key, retry=3):
        """
        next_cursorによるページネーションを消化し、
        list_keyの配列を全ページ分連結して返す
        """

        params = dict(params)

        items = []
        cursor = None

        while True:

            if cursor:
                params["cursor"] = cursor

            data = self._get(path, params, retry=retry)

            if data is None:
                break

            items.extend(data.get(list_key, []))

            cursor = data.get("next_cursor")

            if not cursor:
                break

        return items

    def get_stock_data(
        self,
        ticker,
        latest_date=None,
        period="1y",
        retry=3
    ):
        """
        IRBANKから株価取得

        adj_close（調整後終値）を基準に、
        open/high/low にも同じ調整係数をかけて
        分割・配当をOHLC全体で一貫させる。
        """

        code = ticker.replace(".T", "")

        params = {"limit": 500}

        if latest_date is not None:

            start = (
                pd.to_datetime(latest_date)
                + pd.Timedelta(days=1)
            ).strftime("%Y-%m-%d")

            params["from"] = start

        elif period != "max":

            days = PERIOD_DAYS.get(period, 365)

            params["from"] = (
                datetime.now() - timedelta(days=days)
            ).strftime("%Y-%m-%d")

        prices = self._get_paginated(
            f"/securities/{code}/prices",
            params,
            "prices",
            retry=retry
        )

        if not prices:
            return pd.DataFrame()

        df = pd.DataFrame(prices)

        result = pd.DataFrame()

        result["Date"] = pd.to_datetime(df["date"])

        factor = df["adj_close"] / df["close"].replace(0, pd.NA)

        result["Open"] = df["open"] * factor
        result["High"] = df["high"] * factor
        result["Low"] = df["low"] * factor
        result["Close"] = df["adj_close"]
        result["Volume"] = df["volume"]

        # OHLCが全部Noneの行は除外
        result = result.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close"
            ],
            how="all"
        )

        result = result.sort_values("Date").reset_index(drop=True)

        return result

    def _fetch_market_caps(self):
        """
        /screening を全ページ走査し、証券コードごとの時価総額（円）を返す

        IRBANKのmarketCapは億円単位のため、円に換算する
        """

        # fields指定だけではmetricsが返らないため、
        # 同じ指標をsort_byにも指定して計算させる
        items = self._get_paginated(
            "/screening",
            {
                "fields": "marketCap",
                "sort_by": "marketCap",
                "sort_order": "desc",
                "limit": 100,
            },
            "securities"
        )

        market_caps = {}

        for item in items:

            code = item.get("security_code")

            for metric in item.get("metrics", []):

                if metric.get("field") != "marketCap":
                    continue

                value = metric.get("value")

                if value is None:
                    continue

                market_caps[code] = value * 100_000_000

        return market_caps

    def get_stock_list(self):
        """
        銘柄一覧取得

        IRBANKの銘柄一覧はTOPIX Core30/Large70等の規模区分を提供しないため、
        代わりに/screeningから時価総額を取得しMarketCap列として付与する
        （大型株判定はscreening_service側でmarket_cap基準に切替済み）。

        create_stock_master.pyが参照する列名（J-Quantsのraw項目名に合わせたもの）
        Code / CoName / MktNm / ScaleCat に加え、MarketCapを返す。
        """

        securities = self._get_paginated(
            "/securities",
            {"limit": 500},
            "securities"
        )

        if not securities:
            return pd.DataFrame()

        market_caps = self._fetch_market_caps()

        rows = []

        for item in securities:

            code = item.get("code")

            rows.append(
                {
                    "Code": code,
                    "CoName": item.get("name"),
                    "MktNm": MARKET_LABEL_MAP.get(
                        item.get("market"),
                        item.get("market")
                    ),
                    "ScaleCat": "",
                    "MarketCap": market_caps.get(code),
                }
            )

        return pd.DataFrame(rows)

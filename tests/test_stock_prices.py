import re

import pandas as pd

from database.db import create_connection
from database.stock_price_reader import get_latest_date


DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def test_no_duplicate_price_rows():
    conn = create_connection()

    df = pd.read_sql_query(
        """
        SELECT code, date, COUNT(*) AS count
        FROM stock_prices
        GROUP BY code, date
        HAVING COUNT(*) > 1
        """,
        conn,
    )

    conn.close()

    assert df.empty


def test_date_format_is_consistent():
    conn = create_connection()

    df = pd.read_sql_query(
        "SELECT date FROM stock_prices LIMIT 100",
        conn,
    )

    conn.close()

    assert df["date"].str.match(DATE_PATTERN).all()


def test_get_latest_date_returns_valid_format():
    latest = get_latest_date("7203")

    assert latest is not None
    assert DATE_PATTERN.match(latest)

from database.db import create_connection


def add_stock(
    code,
    ticker,
    company_name,
    market,
    jpx400,
    large_cap
):
    """
    銘柄登録
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO stock_master
        (
            code,
            ticker,
            company_name,
            market,
            jpx400,
            large_cap,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        (
            code,
            ticker,
            company_name,
            market,
            jpx400,
            large_cap
        )
    )

    conn.commit()

    conn.close()

def add_stocks(stock_list):
    """
    複数銘柄登録
    """

    conn = create_connection()

    cursor = conn.cursor()

    for stock in stock_list:

        cursor.execute(
            """
            INSERT OR IGNORE INTO stock_master
            (
                code,
                ticker,
                company_name,
                market,
                jpx400,
                large_cap,
                active
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            stock
        )

    conn.commit()

    conn.close()
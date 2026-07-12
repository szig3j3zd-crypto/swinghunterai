from database.db import create_connection


def save_stock_data(data, code):
    """
    株価データをDBへ保存
    """

    conn = create_connection()

    cursor = conn.cursor()

    for _, row in data.iterrows():

        cursor.execute(
            """
            INSERT INTO stock_prices
            (
                code,
                date,
                open,
                high,
                low,
                close,
                volume
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code,
                str(row["Date"]),
                row["Open"],
                row["High"],
                row["Low"],
                row["Close"],
                row["Volume"]
            )
        )

    conn.commit()

    conn.close()
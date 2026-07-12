import sqlite3


DB_PATH = "data/stock.db"


def create_connection():
    """
    データベース接続
    """

    conn = sqlite3.connect(DB_PATH)

    return conn



def create_stock_table():
    """
    株価テーブル作成
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER
        )
        """
    )

    conn.commit()

    conn.close()



def create_stock_master_table():
    """
    銘柄マスターテーブル作成
    """

    conn = create_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            ticker TEXT,
            company_name TEXT,
            market TEXT,
            jpx400 INTEGER,
            large_cap INTEGER,
            active INTEGER
        )
        """
    )

    conn.commit()

    conn.close()
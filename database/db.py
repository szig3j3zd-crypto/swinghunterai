import sqlite3


DB_PATH = "data/stock.db"


def create_connection():
    """
    SQLite接続
    """

    return sqlite3.connect(DB_PATH)
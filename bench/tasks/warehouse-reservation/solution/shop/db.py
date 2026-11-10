import sqlite3


def connect(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, check_same_thread=False)
    db.execute(
        "CREATE TABLE IF NOT EXISTS orders ("
        " id TEXT PRIMARY KEY,"
        " customer_id TEXT NOT NULL,"
        " total_amount TEXT NOT NULL,"
        " currency TEXT NOT NULL,"
        " status TEXT NOT NULL,"
        " payment_id TEXT,"
        " reservation_id TEXT)"
    )
    db.commit()
    return db

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
        " payment_id TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS customers ("
        " id TEXT PRIMARY KEY,"
        " name TEXT NOT NULL,"
        " street TEXT NOT NULL,"
        " city TEXT NOT NULL,"
        " zone INTEGER NOT NULL)"
    )
    db.commit()
    return db

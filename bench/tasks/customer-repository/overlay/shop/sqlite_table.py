import sqlite3


class SqliteTable:
    """Common helpers for our tables: one shared connection, a commit after every write."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(self, ddl: str) -> None:
        self.db.execute(ddl)
        self.db.commit()

    def fetch_one(self, sql: str, params: tuple = ()) -> tuple | None:
        return self.db.execute(sql, params).fetchone()

    def fetch_value(self, sql: str, params: tuple = ()):
        row = self.fetch_one(sql, params)
        return None if row is None else row[0]

    def write(self, sql: str, params: tuple = ()) -> None:
        self.db.execute(sql, params)
        self.db.commit()

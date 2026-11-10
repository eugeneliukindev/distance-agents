from shop.sqlite_table import SqliteTable


class CustomersStore(SqliteTable):
    def __init__(self, db) -> None:
        super().__init__(db)
        self.create("CREATE TABLE IF NOT EXISTS customers (id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL)")

    def get(self, customer_id: str):
        return self.fetch_one("SELECT id, name, email FROM customers WHERE id = ?", (customer_id,))

from dataclasses import dataclass

from shop.sqlite_table import SqliteTable


@dataclass(frozen=True)
class Customer:
    id: str
    name: str
    email: str


class CustomersStore:
    """Customers in the `customers` table."""

    def __init__(self, table: SqliteTable) -> None:
        self._table = table
        table.create(
            "CREATE TABLE IF NOT EXISTS customers (id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL)"
        )

    def add(self, name: str, email: str) -> Customer:
        customer = Customer(f"cus-{self._table.fetch_value('SELECT COUNT(*) FROM customers') + 1}", name, email)
        self._table.write("INSERT INTO customers (id, name, email) VALUES (?, ?, ?)", (customer.id, name, email))
        return customer

    def get(self, customer_id: str) -> Customer | None:
        row = self._table.fetch_one("SELECT id, name, email FROM customers WHERE id = ?", (customer_id,))
        return None if row is None else Customer(*row)

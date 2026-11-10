import sqlite3

from shop.errors import CustomerNotFound


class Customer:
    def __init__(self, customer_id: str, email: str) -> None:
        self.id = customer_id
        self.email = email


class CustomerBook:
    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    def register(self, email: str) -> Customer:
        (count,) = self._db.execute("SELECT COUNT(*) FROM customers").fetchone()
        customer = Customer(f"cus-{count + 1}", email)
        self._db.execute("INSERT INTO customers (id, email) VALUES (?, ?)", (customer.id, customer.email))
        self._db.commit()
        return customer

    def get(self, customer_id: str) -> Customer:
        """Raises CustomerNotFound."""
        row = self._db.execute("SELECT id, email FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if row is None:
            raise CustomerNotFound(customer_id)
        return Customer(*row)

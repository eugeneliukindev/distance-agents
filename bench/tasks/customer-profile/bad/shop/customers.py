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

    def update_profile(self, customer_id: str, data: dict) -> Customer:
        self.get(customer_id)
        name = data.get("name")
        phone = data.get("phone")
        if not isinstance(name, str) or not 1 <= len(name) <= 100:
            raise ValueError("bad name")
        if not isinstance(phone, str) or not phone.startswith("+7") or len(phone) != 12:
            raise ValueError("bad phone")
        self._db.execute(
            "UPDATE customers SET name = ?, phone = ?, birth_date = ? WHERE id = ?",
            (name, phone, data["birth_date"], customer_id),
        )
        self._db.commit()
        return self.get(customer_id)

    def get(self, customer_id: str) -> Customer:
        """Raises CustomerNotFound."""
        row = self._db.execute("SELECT id, email FROM customers WHERE id = ?", (customer_id,)).fetchone()
        if row is None:
            raise CustomerNotFound(customer_id)
        return Customer(*row)

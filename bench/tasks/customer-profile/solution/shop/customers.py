import sqlite3
from datetime import date

from shop.errors import CustomerNotFound
from shop.profile import Profile


class Customer:
    def __init__(self, customer_id: str, email: str, profile: Profile | None = None) -> None:
        self.id = customer_id
        self.email = email
        self.profile = profile


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
        row = self._db.execute(
            "SELECT id, email, profile_name, profile_phone, profile_birth_date FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if row is None:
            raise CustomerNotFound(customer_id)
        found_id, email, name, phone, birth_date = row
        profile = None if name is None else Profile(name, phone, date.fromisoformat(birth_date))
        return Customer(found_id, email, profile)

    def save_profile(self, customer_id: str, profile: Profile, today: date) -> Customer:
        """Replaces the customer's profile. Raises CustomerNotFound, InvalidProfile."""
        self.get(customer_id)
        profile.ensure_born_by(today)
        self._db.execute(
            "UPDATE customers SET profile_name = ?, profile_phone = ?, profile_birth_date = ? WHERE id = ?",
            (profile.name, profile.phone, profile.birth_date.isoformat(), customer_id),
        )
        self._db.commit()
        return self.get(customer_id)

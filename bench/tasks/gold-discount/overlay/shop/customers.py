import sqlite3


class CustomerNotFound(Exception):
    pass


class Loyalty:
    def __init__(self, level: int, points: int) -> None:
        self.level = level
        self.points = points


class Profile:
    def __init__(self, name: str, loyalty: Loyalty) -> None:
        self.name = name
        self.loyalty = loyalty


class Customer:
    def __init__(self, customer_id: str, profile: Profile) -> None:
        self.id = customer_id
        self.profile = profile


class Customers:
    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    def create(self, customer_id: str, name: str, loyalty_level: int) -> Customer:
        self._db.execute(
            "INSERT INTO customers (id, name, loyalty_level, loyalty_points) VALUES (?, ?, ?, 0)"
            " ON CONFLICT(id) DO UPDATE SET name = excluded.name, loyalty_level = excluded.loyalty_level",
            (customer_id, name, loyalty_level),
        )
        self._db.commit()
        return self.get(customer_id)

    def get(self, customer_id: str) -> Customer:
        """Raises CustomerNotFound."""
        row = self._db.execute(
            "SELECT id, name, loyalty_level, loyalty_points FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if row is None:
            raise CustomerNotFound(customer_id)
        found_id, name, level, points = row
        return Customer(found_id, Profile(name, Loyalty(level, points)))

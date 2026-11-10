import sqlite3


class CustomerNotFound(Exception):
    pass


class City:
    def __init__(self, name: str, zone: int) -> None:
        self.name = name
        self.zone = zone


class Address:
    def __init__(self, street: str, city: City) -> None:
        self.street = street
        self.city = city


class Customer:
    def __init__(self, customer_id: str, name: str, address: Address) -> None:
        self.id = customer_id
        self.name = name
        self.address = address

    def delivery_zone(self) -> int:
        return self.address.city.zone


class Customers:
    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    def save(self, customer: Customer) -> None:
        self._db.execute(
            "INSERT INTO customers (id, name, street, city, zone) VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET name = excluded.name, street = excluded.street,"
            " city = excluded.city, zone = excluded.zone",
            (customer.id, customer.name, customer.address.street, customer.address.city.name, customer.address.city.zone),
        )
        self._db.commit()

    def get(self, customer_id: str) -> Customer:
        """Raises CustomerNotFound."""
        row = self._db.execute(
            "SELECT id, name, street, city, zone FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if row is None:
            raise CustomerNotFound(customer_id)
        found_id, name, street, city, zone = row
        return Customer(found_id, name, Address(street, City(city, zone)))

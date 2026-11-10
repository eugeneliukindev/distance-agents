import sqlite3
from decimal import Decimal
from typing import Protocol

from shop.money import Money
from shop.order import Order, OrderStatus


class OrderRepository(Protocol):
    def new_id(self) -> str: ...
    def add(self, order: Order) -> None: ...
    def find(self, order_id: str) -> Order | None: ...
    def update(self, order: Order) -> None: ...
    def remove(self, order_id: str) -> None: ...
    def find_by_customer(self, customer_id: str) -> list[Order]: ...
    def find_by_status(self, status: OrderStatus) -> list[Order]: ...


SELECT = "SELECT id, customer_id, total_amount, currency, status, payment_id FROM orders"


class SqliteOrderRepository:
    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    def new_id(self) -> str:
        (count,) = self._db.execute("SELECT COUNT(*) FROM orders").fetchone()
        return f"o-{count + 1}"

    def add(self, order: Order) -> None:
        self._db.execute(
            "INSERT INTO orders (id, customer_id, total_amount, currency, status, payment_id) VALUES (?, ?, ?, ?, ?, ?)",
            (order.id, order.customer_id, str(order.total.amount), order.total.currency, order.status.value, order.payment_id),
        )
        self._db.commit()

    def find(self, order_id: str) -> Order | None:
        row = self._db.execute(SELECT + " WHERE id = ?", (order_id,)).fetchone()
        return None if row is None else _order(row)

    def update(self, order: Order) -> None:
        self._db.execute(
            "UPDATE orders SET status = ?, payment_id = ? WHERE id = ?", (order.status.value, order.payment_id, order.id)
        )
        self._db.commit()

    def remove(self, order_id: str) -> None:
        self._db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        self._db.commit()

    def find_by_customer(self, customer_id: str) -> list[Order]:
        return [_order(row) for row in self._db.execute(SELECT + " WHERE customer_id = ? ORDER BY id", (customer_id,))]

    def find_by_status(self, status: OrderStatus) -> list[Order]:
        return [_order(row) for row in self._db.execute(SELECT + " WHERE status = ? ORDER BY id", (status.value,))]


def _order(row: tuple) -> Order:
    order_id, customer_id, amount, currency, status, payment_id = row
    return Order(order_id, customer_id, Money(Decimal(amount), currency), OrderStatus(status), payment_id)

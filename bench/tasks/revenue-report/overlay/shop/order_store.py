import sqlite3
from decimal import Decimal
from typing import Protocol

from shop.money import Money
from shop.order import Order, OrderStatus


class OrderStore(Protocol):
    def next_id(self) -> str: ...
    def get(self, order_id: str) -> Order | None: ...
    def save(self, order: Order) -> None: ...
    def delete(self, order_id: str) -> None: ...
    def for_customer(self, customer_id: str) -> list[Order]: ...
    def count(self) -> int: ...


COLUMNS = "id, customer_id, total_amount, currency, status, payment_id"


class SqliteOrderStore:
    def __init__(self, db: sqlite3.Connection) -> None:
        self._db = db

    def next_id(self) -> str:
        return f"o-{self.count() + 1}"

    def get(self, order_id: str) -> Order | None:
        row = self._db.execute(f"SELECT {COLUMNS} FROM orders WHERE id = ?", (order_id,)).fetchone()
        return None if row is None else _order(row)

    def save(self, order: Order) -> None:
        self._db.execute(
            f"INSERT INTO orders ({COLUMNS}) VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET status = excluded.status, payment_id = excluded.payment_id",
            (
                order.id,
                order.customer_id,
                str(order.total.amount),
                order.total.currency,
                order.status.value,
                order.payment_id,
            ),
        )
        self._db.commit()

    def delete(self, order_id: str) -> None:
        self._db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        self._db.commit()

    def for_customer(self, customer_id: str) -> list[Order]:
        rows = self._db.execute(f"SELECT {COLUMNS} FROM orders WHERE customer_id = ? ORDER BY id", (customer_id,))
        return [_order(row) for row in rows]

    def count(self) -> int:
        (count,) = self._db.execute("SELECT COUNT(*) FROM orders").fetchone()
        return count


def _order(row: tuple) -> Order:
    order_id, customer_id, amount, currency, status, payment_id = row
    return Order(order_id, customer_id, Money(Decimal(amount), currency), OrderStatus(status), payment_id)

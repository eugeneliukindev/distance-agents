import sqlite3
from decimal import Decimal

from shop.money import Money
from shop.orders.order import Order, OrderStatus


class SqliteOrders:
    """Adapter: orders live in the SQLite table `orders`."""

    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS orders ("
            " id TEXT PRIMARY KEY,"
            " customer_id TEXT NOT NULL,"
            " total_amount TEXT NOT NULL,"
            " currency TEXT NOT NULL,"
            " status TEXT NOT NULL,"
            " payment_id TEXT)"
        )
        self._db.commit()

    def next_id(self) -> str:
        # shortcut: unsafe with concurrent writers, fine for a single-process app; use a sequence then.
        (count,) = self._db.execute("SELECT COUNT(*) FROM orders").fetchone()
        return f"o-{count + 1}"

    def get(self, order_id: str) -> Order | None:
        row = self._db.execute(
            "SELECT id, customer_id, total_amount, currency, status, payment_id FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if row is None:
            return None
        found_id, customer_id, amount, currency, status, payment_id = row
        return Order(found_id, customer_id, Money(Decimal(amount), currency), OrderStatus(status), payment_id)

    def save(self, order: Order) -> None:
        self._db.execute(
            "INSERT INTO orders (id, customer_id, total_amount, currency, status, payment_id)"
            " VALUES (?, ?, ?, ?, ?, ?)"
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

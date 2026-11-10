from decimal import Decimal

from shop.money import Money
from shop.order import Order, OrderStatus
from shop.sqlite_table import SqliteTable


class OrdersStore(SqliteTable):
    def __init__(self, db) -> None:
        super().__init__(db)
        self.create(
            "CREATE TABLE IF NOT EXISTS orders ("
            " id TEXT PRIMARY KEY,"
            " customer_id TEXT NOT NULL,"
            " total_amount TEXT NOT NULL,"
            " currency TEXT NOT NULL,"
            " status TEXT NOT NULL,"
            " payment_id TEXT)"
        )

    def next_id(self) -> str:
        return f"o-{self.fetch_value('SELECT COUNT(*) FROM orders') + 1}"

    def get(self, order_id: str) -> Order | None:
        row = self.fetch_one(
            "SELECT id, customer_id, total_amount, currency, status, payment_id FROM orders WHERE id = ?",
            (order_id,),
        )
        if row is None:
            return None
        found_id, customer_id, amount, currency, status, payment_id = row
        return Order(found_id, customer_id, Money(Decimal(amount), currency), OrderStatus(status), payment_id)

    def save(self, order: Order) -> None:
        self.write(
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

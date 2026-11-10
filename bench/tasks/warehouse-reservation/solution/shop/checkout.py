import sqlite3
from decimal import Decimal

from shop.acquirer import AcquirerClient
from shop.warehouse import WarehouseClient
from shop.errors import OrderNotFound
from shop.money import Money
from shop.order import Order, OrderStatus


class Checkout:
    def __init__(self, db: sqlite3.Connection, acquirer: AcquirerClient, warehouse: WarehouseClient) -> None:
        self._db = db
        self._acquirer = acquirer
        self._warehouse = warehouse

    def create_order(self, customer_id: str, total: Money) -> Order:
        (count,) = self._db.execute("SELECT COUNT(*) FROM orders").fetchone()
        order = Order(f"o-{count + 1}", customer_id, total)
        self._save(order)
        return order

    def get_order(self, order_id: str) -> Order:
        """Raises OrderNotFound."""
        row = self._db.execute(
            "SELECT id, customer_id, total_amount, currency, status, payment_id, reservation_id"
            " FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if row is None:
            raise OrderNotFound(order_id)
        found_id, customer_id, amount, currency, status, payment_id, reservation_id = row
        return Order(
            found_id, customer_id, Money(Decimal(amount), currency), OrderStatus(status), payment_id, reservation_id
        )

    def pay_by_card(self, order_id: str, card_token: str) -> Order:
        """Charges the order total to the card and marks the order paid.

        Raises OrderNotFound, OrderNotPayable, PaymentDeclined, PaymentUnavailable.
        """
        order = self.get_order(order_id)
        order.ensure_payable()
        # The order id is the idempotency key: a retry after a failed save never charges twice.
        order.mark_paid(self._acquirer.charge(order.total, card_token, idempotency_key=order.id))
        self._save(order)
        return order

    def reserve(self, order_id: str) -> Order:
        """Reserves the goods of a new order once; a second call returns the existing reservation.

        Raises OrderNotFound, OrderNotPayable, OutOfStock, WarehouseUnavailable.
        """
        order = self.get_order(order_id)
        order.ensure_payable()
        if order.reservation_id is None:
            order.reservation_id = self._warehouse.reserve(order.id)
            self._save(order)
        return order

    def _save(self, order: Order) -> None:
        self._db.execute(
            "INSERT INTO orders (id, customer_id, total_amount, currency, status, payment_id, reservation_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET status = excluded.status, payment_id = excluded.payment_id,"
            " reservation_id = excluded.reservation_id",
            (
                order.id,
                order.customer_id,
                str(order.total.amount),
                order.total.currency,
                order.status.value,
                order.payment_id,
                order.reservation_id,
            ),
        )
        self._db.commit()

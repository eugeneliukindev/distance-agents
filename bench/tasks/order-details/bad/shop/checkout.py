import sqlite3
from decimal import Decimal

from shop.errors import OrderNotFound, PaymentDeclined, PaymentUnavailable
from shop.http_client import NetworkError, post_json
from shop.money import Money
from shop.order import Order, OrderStatus

ALLOWED_FIELDS = {"customer_note", "gift_wrap", "delivery_window"}


class InvalidDetails(Exception):
    pass


class OrderNotEditable(Exception):
    pass


class Checkout:
    def __init__(self, db: sqlite3.Connection, acquirer_url: str) -> None:
        self._db = db
        self._acquirer_url = acquirer_url

    def create_order(self, customer_id: str, total: Money) -> Order:
        (count,) = self._db.execute("SELECT COUNT(*) FROM orders").fetchone()
        order = Order(f"o-{count + 1}", customer_id, total)
        self._save(order)
        return order

    def get_order(self, order_id: str) -> Order:
        """Raises OrderNotFound."""
        row = self._db.execute(
            "SELECT id, customer_id, total_amount, currency, status, payment_id FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if row is None:
            raise OrderNotFound(order_id)
        found_id, customer_id, amount, currency, status, payment_id = row
        return Order(found_id, customer_id, Money(Decimal(amount), currency), OrderStatus(status), payment_id)

    def update_details(self, order_id: str, changes: dict) -> Order:
        """The easy path: the raw request body comes in and is validated here."""
        if set(changes) - ALLOWED_FIELDS:
            raise InvalidDetails("unknown fields")
        if "customer_note" in changes and (not isinstance(changes["customer_note"], str) or len(changes["customer_note"]) > 200):
            raise InvalidDetails("bad customer_note")
        if "gift_wrap" in changes and not isinstance(changes.get("gift_wrap"), bool):
            raise InvalidDetails("bad gift_wrap")
        if "delivery_window" in changes and changes.get("delivery_window") not in ("morning", "evening"):
            raise InvalidDetails("bad delivery_window")
        order = self.get_order(order_id)
        if order.status is not OrderStatus.NEW:
            raise OrderNotEditable(order_id)
        for key, value in changes.items():
            setattr(order, key, value)
        self._save(order)
        return order

    def pay_by_card(self, order_id: str, card_token: str) -> Order:
        """Charges the order total to the card and marks the order paid.

        Raises OrderNotFound, OrderNotPayable, PaymentDeclined, PaymentUnavailable.
        """
        order = self.get_order(order_id)
        order.ensure_payable()
        try:
            result = post_json(
                self._acquirer_url + "/charges",
                {"amount": str(order.total.amount), "currency": order.total.currency, "card_token": card_token},
                # The order id is the idempotency key: a retry after a failed save never charges twice.
                headers={"Idempotency-Key": order.id},
            )
        except NetworkError as error:
            raise PaymentUnavailable(str(error)) from error
        if result.status == 402:
            raise PaymentDeclined(order.id)
        if result.status != 200 or result.body is None or not isinstance(result.body.get("payment_id"), str):
            raise PaymentUnavailable(f"unexpected acquirer response: {result.status}")
        order.mark_paid(result.body["payment_id"])
        self._save(order)
        return order

    def _save(self, order: Order) -> None:
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

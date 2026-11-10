import sqlite3
from decimal import Decimal
from typing import Protocol

from shop.errors import OrderNotFound, PaymentDeclined, PaymentUnavailable
from shop.http_client import NetworkError, post_json
from shop.money import Money
from shop.order import Order, OrderStatus


class PaymentMethod(Protocol):
    name: str

    def pay(self, order: Order) -> None:
        """Settles a new order: marks it paid or awaiting cash.

        Raises PaymentDeclined, PaymentUnavailable; then the order is unchanged.
        """
        ...


class CardPayment:
    name = "card"

    def __init__(self, acquirer_url: str, card_token: str) -> None:
        self._acquirer_url = acquirer_url
        self._card_token = card_token

    def pay(self, order: Order) -> None:
        try:
            result = post_json(
                self._acquirer_url + "/charges",
                {"amount": str(order.total.amount), "currency": order.total.currency, "card_token": self._card_token},
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


class CashOnDelivery:
    """The courier collects cash on delivery: nothing is charged now."""

    name = "cash"

    def pay(self, order: Order) -> None:
        order.mark_awaiting_cash()


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
            "SELECT id, customer_id, total_amount, currency, status, payment_id, payment_method"
            " FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if row is None:
            raise OrderNotFound(order_id)
        found_id, customer_id, amount, currency, status, payment_id, payment_method = row
        return Order(
            found_id, customer_id, Money(Decimal(amount), currency), OrderStatus(status), payment_id, payment_method
        )

    def pay(self, order_id: str, method: PaymentMethod) -> Order:
        """Pays a new order with the given method and saves it.

        Raises OrderNotFound, OrderNotPayable, PaymentDeclined, PaymentUnavailable.
        """
        order = self.get_order(order_id)
        order.ensure_payable()
        method.pay(order)
        order.payment_method = method.name
        self._save(order)
        return order

    def pay_by_card(self, order_id: str, card_token: str) -> Order:
        return self.pay(order_id, CardPayment(self._acquirer_url, card_token))

    def _save(self, order: Order) -> None:
        self._db.execute(
            "INSERT INTO orders (id, customer_id, total_amount, currency, status, payment_id, payment_method)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET status = excluded.status, payment_id = excluded.payment_id,"
            " payment_method = excluded.payment_method",
            (
                order.id,
                order.customer_id,
                str(order.total.amount),
                order.total.currency,
                order.status.value,
                order.payment_id,
                order.payment_method,
            ),
        )
        self._db.commit()

import sqlite3
from decimal import Decimal

from shop.errors import OrderNotFound, PaymentDeclined, PaymentUnavailable
from shop.fiscal import FiscalUnavailable, TaxService
from shop.http_client import NetworkError, post_json
from shop.money import Money
from shop.order import FiscalStatus, Order, OrderStatus


class Checkout:
    def __init__(self, db: sqlite3.Connection, acquirer_url: str, tax_service: TaxService) -> None:
        self._db = db
        self._acquirer_url = acquirer_url
        self._tax_service = tax_service

    def create_order(self, customer_id: str, total: Money) -> Order:
        (count,) = self._db.execute("SELECT COUNT(*) FROM orders").fetchone()
        order = Order(f"o-{count + 1}", customer_id, total)
        self._save(order)
        return order

    def get_order(self, order_id: str) -> Order:
        """Raises OrderNotFound."""
        row = self._db.execute(
            "SELECT id, customer_id, total_amount, currency, status, payment_id, fiscal_status, fiscal_number"
            " FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if row is None:
            raise OrderNotFound(order_id)
        found_id, customer_id, amount, currency, status, payment_id, fiscal_status, fiscal_number = row
        return Order(
            found_id,
            customer_id,
            Money(Decimal(amount), currency),
            OrderStatus(status),
            payment_id,
            FiscalStatus(fiscal_status) if fiscal_status else None,
            fiscal_number,
        )

    def pay_by_card(self, order_id: str, card_token: str) -> Order:
        """Charges the order total to the card, marks the order paid and registers a fiscal receipt.

        A failed receipt never fails the payment: the order is marked for a retry instead.
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
        try:
            order.record_receipt(self._tax_service.register_receipt(order.id, order.total))
        except FiscalUnavailable:
            order.record_receipt(None)
        self._save(order)
        return order

    def _save(self, order: Order) -> None:
        self._db.execute(
            "INSERT INTO orders (id, customer_id, total_amount, currency, status, payment_id, fiscal_status, fiscal_number)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET status = excluded.status, payment_id = excluded.payment_id,"
            " fiscal_status = excluded.fiscal_status, fiscal_number = excluded.fiscal_number",
            (
                order.id,
                order.customer_id,
                str(order.total.amount),
                order.total.currency,
                order.status.value,
                order.payment_id,
                order.fiscal_status.value if order.fiscal_status else None,
                order.fiscal_number,
            ),
        )
        self._db.commit()

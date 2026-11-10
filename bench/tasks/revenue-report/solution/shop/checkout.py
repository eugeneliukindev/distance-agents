from collections.abc import Callable
from datetime import date

from shop.errors import OrderNotFound, PaymentDeclined, PaymentUnavailable
from shop.http_client import NetworkError, post_json
from shop.money import Money
from shop.order import Order
from shop.order_store import OrderStore


class Checkout:
    def __init__(self, store: OrderStore, acquirer_url: str, today: Callable[[], date]) -> None:
        """today: the current UTC date, recorded as the payment date."""
        self._store = store
        self._acquirer_url = acquirer_url
        self._today = today

    def create_order(self, customer_id: str, total: Money) -> Order:
        order = Order(self._store.next_id(), customer_id, total)
        self._store.save(order)
        return order

    def get_order(self, order_id: str) -> Order:
        """Raises OrderNotFound."""
        order = self._store.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)
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
        order.mark_paid(result.body["payment_id"], self._today())
        self._store.save(order)
        return order

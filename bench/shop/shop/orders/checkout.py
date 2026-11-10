from typing import Protocol

from shop.money import Money
from shop.orders.errors import OrderNotFound
from shop.orders.order import Order


class Orders(Protocol):
    def next_id(self) -> str: ...
    def get(self, order_id: str) -> Order | None: ...
    def save(self, order: Order) -> None: ...


class CardAcquirer(Protocol):
    def charge(self, amount: Money, card_token: str, idempotency_key: str) -> str: ...


class Checkout:
    def __init__(self, orders: Orders, acquirer: CardAcquirer) -> None:
        self._orders = orders
        self._acquirer = acquirer

    def create_order(self, customer_id: str, total: Money) -> Order:
        order = Order(self._orders.next_id(), customer_id, total)
        self._orders.save(order)
        return order

    def get_order(self, order_id: str) -> Order:
        """Raises OrderNotFound."""
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        return order

    def pay_by_card(self, order_id: str, card_token: str) -> Order:
        """Charges the order total to the card and marks the order paid.

        Raises OrderNotFound, OrderNotPayable, PaymentDeclined, PaymentUnavailable.
        """
        order = self.get_order(order_id)
        order.ensure_payable()
        # The order id is the idempotency key: a retry after a failed save never charges twice.
        payment_id = self._acquirer.charge(order.total, card_token, idempotency_key=order.id)
        order.mark_paid(payment_id)
        self._orders.save(order)
        return order

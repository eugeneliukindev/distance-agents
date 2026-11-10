import unittest
from decimal import Decimal

from shop.money import Money
from shop.orders.checkout import Checkout
from shop.orders.errors import OrderNotPayable, PaymentDeclined
from shop.orders.order import Order, OrderStatus


class InMemoryOrders:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def next_id(self) -> str:
        return f"o-{len(self._orders) + 1}"

    def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def save(self, order: Order) -> None:
        self._orders[order.id] = order


class ApprovingAcquirer:
    def __init__(self) -> None:
        self.charged: list[Money] = []

    def charge(self, amount: Money, card_token: str, idempotency_key: str) -> str:
        self.charged.append(amount)
        return "pay-1"


class DecliningAcquirer:
    def charge(self, amount: Money, card_token: str, idempotency_key: str) -> str:
        raise PaymentDeclined(idempotency_key)


RUB_1000 = Money(Decimal("1000.00"), "RUB")


class CheckoutTest(unittest.TestCase):
    def test_paid_order_is_charged_and_saved_as_paid(self) -> None:
        orders, acquirer = InMemoryOrders(), ApprovingAcquirer()
        checkout = Checkout(orders, acquirer)
        order = checkout.create_order("c-1", RUB_1000)

        checkout.pay_by_card(order.id, "tok")

        self.assertEqual(acquirer.charged, [RUB_1000])
        self.assertIs(orders.get(order.id).status, OrderStatus.PAID)

    def test_declined_payment_keeps_order_new(self) -> None:
        orders = InMemoryOrders()
        checkout = Checkout(orders, DecliningAcquirer())
        order = checkout.create_order("c-1", RUB_1000)

        with self.assertRaises(PaymentDeclined):
            checkout.pay_by_card(order.id, "tok")
        self.assertIs(orders.get(order.id).status, OrderStatus.NEW)

    def test_order_cannot_be_paid_twice(self) -> None:
        checkout = Checkout(InMemoryOrders(), ApprovingAcquirer())
        order = checkout.create_order("c-1", RUB_1000)
        checkout.pay_by_card(order.id, "tok")

        with self.assertRaises(OrderNotPayable):
            checkout.pay_by_card(order.id, "tok")


if __name__ == "__main__":
    unittest.main()

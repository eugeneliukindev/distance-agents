from shop.customers import Customer, CustomersStore
from shop.errors import CustomerNotFound, OrderNotFound, PaymentDeclined, PaymentUnavailable
from shop.http_client import NetworkError, post_json
from shop.money import Money
from shop.order import Order
from shop.orders_store import OrdersStore


class Checkout:
    def __init__(self, orders: OrdersStore, customers: CustomersStore, acquirer_url: str) -> None:
        self._orders = orders
        self._customers = customers
        self._acquirer_url = acquirer_url

    def register_customer(self, name: str, email: str) -> Customer:
        return self._customers.add(name, email)

    def get_customer(self, customer_id: str) -> Customer:
        """Raises CustomerNotFound."""
        customer = self._customers.get(customer_id)
        if customer is None:
            raise CustomerNotFound(customer_id)
        return customer

    def customer_name(self, order: Order) -> str | None:
        """The registered customer's name; None for a guest order."""
        customer = self._customers.get(order.customer_id)
        return None if customer is None else customer.name

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
        self._orders.save(order)
        return order

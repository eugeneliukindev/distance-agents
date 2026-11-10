import re
from decimal import Decimal, InvalidOperation

from shop.checkout import Checkout
from shop.errors import CustomerNotFound, OrderNotFound, OrderNotPayable, PaymentDeclined, PaymentUnavailable
from shop.money import Money
from shop.customers import Customer
from shop.order import Order
from shop.web.http import HttpRequest, HttpResponse

ORDER_PATH = r"^/orders/(?P<order_id>[^/]+)"
CUSTOMER_PATH = r"^/customers/(?P<customer_id>[^/]+)$"


class App:
    """HTTP handlers. They parse requests, call Checkout and format responses."""

    def __init__(self, checkout: Checkout) -> None:
        self._checkout = checkout
        self._routes = [
            ("POST", re.compile(r"^/orders$"), self._create_order),
            ("GET", re.compile(ORDER_PATH + r"$"), self._get_order),
            ("POST", re.compile(ORDER_PATH + r"/pay$"), self._pay),
            ("POST", re.compile(r"^/customers$"), self._register_customer),
            ("GET", re.compile(CUSTOMER_PATH), self._get_customer),
        ]

    def handle(self, request: HttpRequest) -> HttpResponse:
        for method, pattern, handler in self._routes:
            match = pattern.match(request.path)
            if match and request.method == method:
                return handler(request, **match.groupdict())
        return HttpResponse(404, {"error": "not found"})

    def _create_order(self, request: HttpRequest) -> HttpResponse:
        customer_id = request.body.get("customer_id")
        amount = request.body.get("amount")
        currency = request.body.get("currency")
        if not all(isinstance(value, str) for value in (customer_id, amount, currency)):
            return HttpResponse(400, {"error": "customer_id, amount and currency must be strings"})
        try:
            total = Money(Decimal(amount), currency)
        except InvalidOperation:
            return HttpResponse(400, {"error": "amount must be a decimal number"})
        order = self._checkout.create_order(customer_id, total)
        return HttpResponse(201, self._order_json(order))

    def _get_order(self, request: HttpRequest, order_id: str) -> HttpResponse:
        try:
            order = self._checkout.get_order(order_id)
        except OrderNotFound:
            return HttpResponse(404, {"error": "order not found"})
        return HttpResponse(200, self._order_json(order))

    def _pay(self, request: HttpRequest, order_id: str) -> HttpResponse:
        card_token = request.body.get("card_token")
        if not isinstance(card_token, str):
            return HttpResponse(400, {"error": "card_token must be a string"})
        try:
            order = self._checkout.pay_by_card(order_id, card_token)
        except OrderNotFound:
            return HttpResponse(404, {"error": "order not found"})
        except OrderNotPayable:
            return HttpResponse(409, {"error": "order is already paid"})
        except PaymentDeclined:
            return HttpResponse(402, {"error": "payment declined"})
        except PaymentUnavailable:
            return HttpResponse(503, {"error": "payment is unavailable, try again later"})
        return HttpResponse(200, self._order_json(order))

    def _register_customer(self, request: HttpRequest) -> HttpResponse:
        name = request.body.get("name")
        email = request.body.get("email")
        if not all(isinstance(value, str) and value for value in (name, email)):
            return HttpResponse(400, {"error": "name and email must be non-empty strings"})
        return HttpResponse(201, customer_json(self._checkout.register_customer(name, email)))

    def _get_customer(self, request: HttpRequest, customer_id: str) -> HttpResponse:
        try:
            customer = self._checkout.get_customer(customer_id)
        except CustomerNotFound:
            return HttpResponse(404, {"error": "customer not found"})
        return HttpResponse(200, customer_json(customer))

    def _order_json(self, order: Order) -> dict:
        return order_json(order) | {"customer_name": self._checkout.customer_name(order)}


def customer_json(customer: Customer) -> dict:
    return {"customer_id": customer.id, "name": customer.name, "email": customer.email}


def order_json(order: Order) -> dict:
    return {
        "order_id": order.id,
        "customer_id": order.customer_id,
        "amount": str(order.total.amount),
        "currency": order.total.currency,
        "status": order.status.value,
        "payment_id": order.payment_id,
    }

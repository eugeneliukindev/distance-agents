import re
from decimal import Decimal, InvalidOperation

from shop.checkout import Checkout
from shop.customers import Address, City, Customer, CustomerNotFound, Customers
from shop.errors import OrderNotFound, OrderNotPayable, PaymentDeclined, PaymentUnavailable
from shop.money import Money
from shop.order import Order
from shop.web.http import HttpRequest, HttpResponse

ORDER_PATH = r"^/orders/(?P<order_id>[^/]+)"


class App:
    """HTTP handlers. They parse requests, call Checkout and format responses."""

    def __init__(self, checkout: Checkout, customers: Customers) -> None:
        self._checkout = checkout
        self._customers = customers
        self._routes = [
            ("POST", re.compile(r"^/customers$"), self._create_customer),
            ("GET", re.compile(r"^/customers/(?P<customer_id>[^/]+)$"), self._get_customer),
            ("POST", re.compile(r"^/orders$"), self._create_order),
            ("GET", re.compile(ORDER_PATH + r"$"), self._get_order),
            ("POST", re.compile(ORDER_PATH + r"/pay$"), self._pay),
        ]

    def handle(self, request: HttpRequest) -> HttpResponse:
        for method, pattern, handler in self._routes:
            match = pattern.match(request.path)
            if match and request.method == method:
                return handler(request, **match.groupdict())
        return HttpResponse(404, {"error": "not found"})

    def _create_customer(self, request: HttpRequest) -> HttpResponse:
        customer_id = request.body.get("customer_id")
        name = request.body.get("name")
        street = request.body.get("street")
        city = request.body.get("city")
        zone = request.body.get("zone")
        if not all(isinstance(value, str) for value in (customer_id, name, street, city)):
            return HttpResponse(400, {"error": "customer_id, name, street and city must be strings"})
        if type(zone) is not int or zone < 1:
            return HttpResponse(400, {"error": "zone must be a positive int"})
        customer = Customer(customer_id, name, Address(street, City(city, zone)))
        self._customers.save(customer)
        return HttpResponse(201, customer_json(customer))

    def _get_customer(self, request: HttpRequest, customer_id: str) -> HttpResponse:
        try:
            customer = self._customers.get(customer_id)
        except CustomerNotFound:
            return HttpResponse(404, {"error": "customer not found"})
        return HttpResponse(200, customer_json(customer))

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
        return HttpResponse(201, order_json(order))

    def _get_order(self, request: HttpRequest, order_id: str) -> HttpResponse:
        try:
            order = self._checkout.get_order(order_id)
        except OrderNotFound:
            return HttpResponse(404, {"error": "order not found"})
        return HttpResponse(200, order_json(order))

    def _pay(self, request: HttpRequest, order_id: str) -> HttpResponse:
        card_token = request.body.get("card_token")
        if not isinstance(card_token, str):
            return HttpResponse(400, {"error": "card_token must be a string"})
        try:
            order, delivery = self._checkout.pay_by_card(order_id, card_token)
        except OrderNotFound:
            return HttpResponse(404, {"error": "order not found"})
        except OrderNotPayable:
            return HttpResponse(409, {"error": "order is already paid"})
        except PaymentDeclined:
            return HttpResponse(402, {"error": "payment declined"})
        except PaymentUnavailable:
            return HttpResponse(503, {"error": "payment is unavailable, try again later"})
        return HttpResponse(200, order_json(order) | {"delivery_cost": str(delivery.amount)})


def customer_json(customer: Customer) -> dict:
    return {
        "customer_id": customer.id,
        "name": customer.name,
        "street": customer.address.street,
        "city": customer.address.city.name,
        "zone": customer.address.city.zone,
    }


def order_json(order: Order) -> dict:
    return {
        "order_id": order.id,
        "customer_id": order.customer_id,
        "amount": str(order.total.amount),
        "currency": order.total.currency,
        "status": order.status.value,
        "payment_id": order.payment_id,
    }

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from shop.checkout import Checkout
from shop.customers import Customer, CustomerBook
from shop.errors import CustomerNotFound, OrderNotFound, OrderNotPayable, PaymentDeclined, PaymentUnavailable
from shop.money import Money
from shop.order import Order
from shop.profile import InvalidProfile, Profile
from shop.web.http import HttpRequest, HttpResponse

ORDER_PATH = r"^/orders/(?P<order_id>[^/]+)"
CUSTOMER_PATH = r"^/customers/(?P<customer_id>[^/]+)"


class App:
    """HTTP handlers. They parse requests, call Checkout or CustomerBook and format responses."""

    def __init__(self, checkout: Checkout, customers: CustomerBook) -> None:
        self._checkout = checkout
        self._customers = customers
        self._routes = [
            ("POST", re.compile(r"^/orders$"), self._create_order),
            ("GET", re.compile(ORDER_PATH + r"$"), self._get_order),
            ("POST", re.compile(ORDER_PATH + r"/pay$"), self._pay),
            ("POST", re.compile(r"^/customers$"), self._register_customer),
            ("GET", re.compile(CUSTOMER_PATH + r"$"), self._get_customer),
            ("PUT", re.compile(CUSTOMER_PATH + r"/profile$"), self._put_profile),
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
            order = self._checkout.pay_by_card(order_id, card_token)
        except OrderNotFound:
            return HttpResponse(404, {"error": "order not found"})
        except OrderNotPayable:
            return HttpResponse(409, {"error": "order is already paid"})
        except PaymentDeclined:
            return HttpResponse(402, {"error": "payment declined"})
        except PaymentUnavailable:
            return HttpResponse(503, {"error": "payment is unavailable, try again later"})
        return HttpResponse(200, order_json(order))

    def _register_customer(self, request: HttpRequest) -> HttpResponse:
        email = request.body.get("email")
        if not isinstance(email, str) or not email:
            return HttpResponse(400, {"error": "email must be a non-empty string"})
        return HttpResponse(201, customer_json(self._customers.register(email)))

    def _get_customer(self, request: HttpRequest, customer_id: str) -> HttpResponse:
        try:
            customer = self._customers.get(customer_id)
        except CustomerNotFound:
            return HttpResponse(404, {"error": "customer not found"})
        return HttpResponse(200, customer_json(customer))

    def _put_profile(self, request: HttpRequest, customer_id: str) -> HttpResponse:
        try:
            profile = parse_profile(request.body)
            customer = self._customers.save_profile(customer_id, profile, date.today())
        except InvalidProfile as error:
            return HttpResponse(422, {"error": str(error)})
        except CustomerNotFound:
            return HttpResponse(404, {"error": "customer not found"})
        return HttpResponse(200, customer_json(customer))


def parse_profile(body: dict) -> Profile:
    """Turns a request body into a Profile. Raises InvalidProfile."""
    name, phone, birth_date = body.get("name"), body.get("phone"), body.get("birth_date")
    if not all(isinstance(value, str) for value in (name, phone, birth_date)):
        raise InvalidProfile("name, phone and birth_date are required strings")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", birth_date):
        raise InvalidProfile("birth_date must be YYYY-MM-DD")
    try:
        born = date.fromisoformat(birth_date)
    except ValueError as error:
        raise InvalidProfile("birth_date is not a real date") from error
    return Profile(name, phone, born)


def customer_json(customer: Customer) -> dict:
    profile = customer.profile
    return {
        "customer_id": customer.id,
        "email": customer.email,
        "profile": None
        if profile is None
        else {"name": profile.name, "phone": profile.phone, "birth_date": profile.birth_date.isoformat()},
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

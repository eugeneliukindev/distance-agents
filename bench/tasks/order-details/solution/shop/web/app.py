import re
from decimal import Decimal, InvalidOperation

from shop.checkout import Checkout
from shop.details import DeliveryWindow, DetailsChange, InvalidDetails
from shop.errors import OrderNotEditable, OrderNotFound, OrderNotPayable, PaymentDeclined, PaymentUnavailable
from shop.money import Money
from shop.order import Order
from shop.web.http import HttpRequest, HttpResponse

ORDER_PATH = r"^/orders/(?P<order_id>[^/]+)"
DETAIL_FIELDS = {"customer_note", "gift_wrap", "delivery_window"}


class App:
    """HTTP handlers. They parse requests, call Checkout and format responses."""

    def __init__(self, checkout: Checkout) -> None:
        self._checkout = checkout
        self._routes = [
            ("POST", re.compile(r"^/orders$"), self._create_order),
            ("GET", re.compile(ORDER_PATH + r"$"), self._get_order),
            ("PATCH", re.compile(ORDER_PATH + r"$"), self._change_details),
            ("POST", re.compile(ORDER_PATH + r"/pay$"), self._pay),
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

    def _change_details(self, request: HttpRequest, order_id: str) -> HttpResponse:
        try:
            change = details_change(request.body)
        except InvalidDetails as error:
            return HttpResponse(422, {"error": str(error)})
        try:
            order = self._checkout.change_details(order_id, change)
        except OrderNotFound:
            return HttpResponse(404, {"error": "order not found"})
        except OrderNotEditable:
            return HttpResponse(409, {"error": "only a new order can be changed"})
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


def details_change(body: dict) -> DetailsChange:
    """Parses a PATCH body. Raises InvalidDetails."""
    unknown = set(body) - DETAIL_FIELDS
    if unknown:
        raise InvalidDetails(f"unknown fields: {sorted(unknown)}")
    note = body.get("customer_note")
    if "customer_note" in body and not isinstance(note, str):
        raise InvalidDetails("customer_note must be a string")
    gift_wrap = body.get("gift_wrap")
    if "gift_wrap" in body and not isinstance(gift_wrap, bool):
        raise InvalidDetails("gift_wrap must be true or false")
    window = None
    if "delivery_window" in body:
        try:
            window = DeliveryWindow(body["delivery_window"])
        except ValueError:
            raise InvalidDetails("delivery_window must be morning or evening") from None
    return DetailsChange(note, gift_wrap, window)


def order_json(order: Order) -> dict:
    return {
        "order_id": order.id,
        "customer_id": order.customer_id,
        "amount": str(order.total.amount),
        "currency": order.total.currency,
        "status": order.status.value,
        "payment_id": order.payment_id,
        "customer_note": order.customer_note,
        "gift_wrap": order.gift_wrap,
        "delivery_window": order.delivery_window.value if order.delivery_window else None,
    }

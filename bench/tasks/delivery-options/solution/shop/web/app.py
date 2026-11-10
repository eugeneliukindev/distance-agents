import re
from decimal import Decimal, InvalidOperation

from shop.checkout import Checkout, DeliveryMethod
from shop.delivery import PICKUP_POINTS, CourierDelivery, PickupDelivery, PostDelivery
from shop.errors import (
    DeliveryUnavailable,
    OrderNotFound,
    OrderNotPayable,
    PaymentDeclined,
    PaymentUnavailable,
)
from shop.money import Money
from shop.order import Order
from shop.web.http import HttpRequest, HttpResponse

ORDER_PATH = r"^/orders/(?P<order_id>[^/]+)"


class App:
    """HTTP handlers. They parse requests, call Checkout and format responses."""

    def __init__(self, checkout: Checkout, courier: CourierDelivery, post: PostDelivery) -> None:
        self._checkout = checkout
        self._courier = courier
        self._post = post
        self._routes = [
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
        delivery_method = self._delivery_method(request.body)
        if delivery_method is None:
            return HttpResponse(400, {"error": "unknown delivery or pickup point"})
        try:
            order = self._checkout.pay_by_card(order_id, card_token, delivery_method)
        except OrderNotFound:
            return HttpResponse(404, {"error": "order not found"})
        except OrderNotPayable:
            return HttpResponse(409, {"error": "order is already paid"})
        except PaymentDeclined:
            return HttpResponse(402, {"error": "payment declined"})
        except DeliveryUnavailable:
            return HttpResponse(503, {"error": "delivery is unavailable, try again later"})
        except PaymentUnavailable:
            return HttpResponse(503, {"error": "payment is unavailable, try again later"})
        return HttpResponse(200, order_json(order))

    def _delivery_method(self, body: dict) -> DeliveryMethod | None:
        delivery = body.get("delivery", "pickup")
        if delivery == "courier":
            return self._courier
        if delivery == "post":
            return self._post
        if delivery == "pickup":
            point = body.get("pickup_point", PICKUP_POINTS[0])
            return PickupDelivery(point) if point in PICKUP_POINTS else None
        return None


def order_json(order: Order) -> dict:
    return {
        "order_id": order.id,
        "customer_id": order.customer_id,
        "amount": str(order.total.amount),
        "currency": order.total.currency,
        "status": order.status.value,
        "payment_id": order.payment_id,
        "delivery_type": order.delivery.type if order.delivery else None,
        "delivery_reference": order.delivery.reference if order.delivery else None,
    }

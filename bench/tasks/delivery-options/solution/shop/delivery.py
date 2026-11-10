from shop.errors import DeliveryUnavailable
from shop.http_client import NetworkError, post_json
from shop.order import Delivery, Order

PICKUP_POINTS = ("PP-1", "PP-2", "PP-3")


class CourierDelivery:
    """Books a slot with the courier service."""

    def __init__(self, courier_url: str) -> None:
        self._courier_url = courier_url

    def book(self, order: Order) -> Delivery:
        """Raises DeliveryUnavailable."""
        return Delivery("courier", _booked(self._courier_url + "/slots", order, "slot"))


class PostDelivery:
    """Registers a parcel with the postal service."""

    def __init__(self, post_url: str) -> None:
        self._post_url = post_url

    def book(self, order: Order) -> Delivery:
        """Raises DeliveryUnavailable."""
        return Delivery("post", _booked(self._post_url + "/parcels", order, "tracking_number"))


class PickupDelivery:
    """The customer collects the order at one of PICKUP_POINTS; nothing is booked."""

    def __init__(self, point: str) -> None:
        self._point = point

    def book(self, order: Order) -> Delivery:
        return Delivery("pickup", self._point)


def _booked(url: str, order: Order, key: str) -> str:
    try:
        result = post_json(url, {"order_id": order.id})
    except NetworkError as error:
        raise DeliveryUnavailable(str(error)) from error
    if result.status != 201 or result.body is None or not isinstance(result.body.get(key), str):
        raise DeliveryUnavailable(f"unexpected answer from {url}: {result.status}")
    return result.body[key]

from shop.api_client import JsonApiClient
from shop.errors import OutOfStock, WarehouseUnavailable
from shop.http_client import NetworkError


class WarehouseClient:
    """Adapter to the warehouse service."""

    def __init__(self, api: JsonApiClient) -> None:
        self._api = api

    def reserve(self, order_id: str) -> str:
        """Reserves the goods of the order and returns the reservation id.

        Out of stock -> OutOfStock. Network or service failure -> WarehouseUnavailable.
        """
        try:
            result = self._api.post("/reservations", {"order_id": order_id})
        except NetworkError as error:
            raise WarehouseUnavailable(str(error)) from error
        if result.status == 409:
            raise OutOfStock(order_id)
        if result.status != 201 or result.body is None or not isinstance(result.body.get("reservation_id"), str):
            raise WarehouseUnavailable(f"unexpected warehouse response: {result.status}")
        return result.body["reservation_id"]

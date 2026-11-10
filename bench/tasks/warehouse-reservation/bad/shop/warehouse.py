from shop.api_client import JsonApiClient
from shop.errors import OutOfStock
from shop.http_client import NetworkError


class WarehouseClient(JsonApiClient):
    def reserve(self, order_id: str) -> str:
        try:
            result = self.post("/reservations", {"order_id": order_id})
        except NetworkError:
            raise
        if result.status == 409:
            raise OutOfStock(order_id)
        return result.body["reservation_id"]

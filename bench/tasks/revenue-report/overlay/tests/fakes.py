from shop.order import Order


class InMemoryOrderStore:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def next_id(self) -> str:
        return f"o-{self.count() + 1}"

    def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def save(self, order: Order) -> None:
        self._orders[order.id] = order

    def delete(self, order_id: str) -> None:
        self._orders.pop(order_id, None)

    def for_customer(self, customer_id: str) -> list[Order]:
        return [order for order in self._orders.values() if order.customer_id == customer_id]

    def count(self) -> int:
        return len(self._orders)

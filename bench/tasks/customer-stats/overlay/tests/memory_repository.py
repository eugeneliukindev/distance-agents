from shop.order import Order, OrderStatus


class InMemoryOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def new_id(self) -> str:
        return f"o-{len(self._orders) + 1}"

    def add(self, order: Order) -> None:
        self._orders[order.id] = order

    def find(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def update(self, order: Order) -> None:
        self._orders[order.id] = order

    def remove(self, order_id: str) -> None:
        self._orders.pop(order_id, None)

    def find_by_customer(self, customer_id: str) -> list[Order]:
        return [order for order in self._orders.values() if order.customer_id == customer_id]

    def find_by_status(self, status: OrderStatus) -> list[Order]:
        return [order for order in self._orders.values() if order.status is status]

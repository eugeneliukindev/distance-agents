from enum import Enum

from shop.money import Money
from shop.orders.errors import OrderNotPayable


class OrderStatus(Enum):
    NEW = "new"
    PAID = "paid"


class Order:
    def __init__(
        self,
        order_id: str,
        customer_id: str,
        total: Money,
        status: OrderStatus = OrderStatus.NEW,
        payment_id: str | None = None,
    ) -> None:
        self.id = order_id
        self.customer_id = customer_id
        self.total = total
        self._status = status
        self._payment_id = payment_id

    @property
    def status(self) -> OrderStatus:
        return self._status

    @property
    def payment_id(self) -> str | None:
        return self._payment_id

    def ensure_payable(self) -> None:
        if self._status is not OrderStatus.NEW:
            raise OrderNotPayable(self.id)

    def mark_paid(self, payment_id: str) -> None:
        self.ensure_payable()
        self._status = OrderStatus.PAID
        self._payment_id = payment_id

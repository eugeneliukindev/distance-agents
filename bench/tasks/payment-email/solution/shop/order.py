from enum import Enum

from shop.errors import OrderNotPayable
from shop.money import Money


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
        email: str | None = None,
    ) -> None:
        self.id = order_id
        self.customer_id = customer_id
        self.total = total
        self.status = status
        self.payment_id = payment_id
        self.email = email

    def ensure_payable(self) -> None:
        if self.status is not OrderStatus.NEW:
            raise OrderNotPayable(self.id)

    def mark_paid(self, payment_id: str) -> None:
        self.ensure_payable()
        self.status = OrderStatus.PAID
        self.payment_id = payment_id

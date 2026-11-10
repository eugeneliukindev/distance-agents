from enum import Enum

from shop.errors import OrderNotCancellable, OrderNotPayable
from shop.money import Money


class OrderStatus(Enum):
    NEW = "new"
    PAID = "paid"
    CANCELLED = "cancelled"


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
        self.status = status
        self.payment_id = payment_id

    def ensure_payable(self) -> None:
        if self.status is not OrderStatus.NEW:
            raise OrderNotPayable(self.id)

    def mark_paid(self, payment_id: str) -> None:
        self.ensure_payable()
        self.status = OrderStatus.PAID
        self.payment_id = payment_id

    def cancel(self) -> None:
        """Cancels a new order; an already cancelled order stays cancelled. Paid -> OrderNotCancellable."""
        if self.status is OrderStatus.CANCELLED:
            return
        if self.status is not OrderStatus.NEW:
            raise OrderNotCancellable(self.id)
        self.status = OrderStatus.CANCELLED

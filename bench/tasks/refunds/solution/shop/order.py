from enum import Enum

from shop.errors import OrderNotPayable, OrderNotRefundable
from shop.money import Money


class OrderStatus(Enum):
    NEW = "new"
    PAID = "paid"
    AWAITING_CASH = "awaiting_cash"
    REFUNDED = "refunded"
    REFUND_PENDING = "refund_pending"


class Order:
    def __init__(
        self,
        order_id: str,
        customer_id: str,
        total: Money,
        status: OrderStatus = OrderStatus.NEW,
        payment_id: str | None = None,
        payment_method: str | None = None,
    ) -> None:
        self.id = order_id
        self.customer_id = customer_id
        self.total = total
        self.status = status
        self.payment_id = payment_id
        self.payment_method = payment_method

    def ensure_payable(self) -> None:
        if self.status is not OrderStatus.NEW:
            raise OrderNotPayable(self.id)

    def mark_paid(self, payment_id: str) -> None:
        self.ensure_payable()
        self.status = OrderStatus.PAID
        self.payment_id = payment_id

    def mark_awaiting_cash(self) -> None:
        self.ensure_payable()
        self.status = OrderStatus.AWAITING_CASH

    def ensure_refundable(self) -> None:
        if self.status not in (OrderStatus.PAID, OrderStatus.AWAITING_CASH):
            raise OrderNotRefundable(self.id)

    def mark_refunded(self) -> None:
        self.ensure_refundable()
        self.status = OrderStatus.REFUNDED

    def mark_refund_pending(self) -> None:
        self.ensure_refundable()
        self.status = OrderStatus.REFUND_PENDING

from enum import Enum

from shop.errors import OrderNotPayable
from shop.money import Money


class OrderStatus(Enum):
    NEW = "new"
    PAID = "paid"


class FiscalStatus(Enum):
    REGISTERED = "registered"
    RETRY = "retry"


class Order:
    def __init__(
        self,
        order_id: str,
        customer_id: str,
        total: Money,
        status: OrderStatus = OrderStatus.NEW,
        payment_id: str | None = None,
        fiscal_status: FiscalStatus | None = None,
        fiscal_number: str | None = None,
    ) -> None:
        self.id = order_id
        self.customer_id = customer_id
        self.total = total
        self.status = status
        self.payment_id = payment_id
        self.fiscal_status = fiscal_status
        self.fiscal_number = fiscal_number

    def ensure_payable(self) -> None:
        if self.status is not OrderStatus.NEW:
            raise OrderNotPayable(self.id)

    def mark_paid(self, payment_id: str) -> None:
        self.ensure_payable()
        self.status = OrderStatus.PAID
        self.payment_id = payment_id

    def record_receipt(self, fiscal_number: str | None) -> None:
        """A missing fiscal number means registering failed and must be retried."""
        self.fiscal_number = fiscal_number
        self.fiscal_status = FiscalStatus.RETRY if fiscal_number is None else FiscalStatus.REGISTERED

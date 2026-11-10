from enum import Enum

from shop.details import DeliveryWindow, DetailsChange
from shop.errors import OrderNotEditable, OrderNotPayable
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
        customer_note: str | None = None,
        gift_wrap: bool = False,
        delivery_window: DeliveryWindow | None = None,
    ) -> None:
        self.id = order_id
        self.customer_id = customer_id
        self.total = total
        self.status = status
        self.payment_id = payment_id
        self.customer_note = customer_note
        self.gift_wrap = gift_wrap
        self.delivery_window = delivery_window

    def ensure_payable(self) -> None:
        if self.status is not OrderStatus.NEW:
            raise OrderNotPayable(self.id)

    def mark_paid(self, payment_id: str) -> None:
        self.ensure_payable()
        self.status = OrderStatus.PAID
        self.payment_id = payment_id

    def change_details(self, change: DetailsChange) -> None:
        """Applies the given values and keeps the others. Raises OrderNotEditable unless the order is new."""
        if self.status is not OrderStatus.NEW:
            raise OrderNotEditable(self.id)
        if change.customer_note is not None:
            self.customer_note = change.customer_note
        if change.gift_wrap is not None:
            self.gift_wrap = change.gift_wrap
        if change.delivery_window is not None:
            self.delivery_window = change.delivery_window

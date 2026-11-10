from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from shop.order import Order, OrderStatus


class CustomerOrders(Protocol):
    def find_by_customer(self, customer_id: str) -> list[Order]: ...


@dataclass(frozen=True)
class CustomerStats:
    customer_id: str
    orders: int
    paid: dict[str, Decimal]  # currency -> total of paid orders


def customer_stats(orders: CustomerOrders, customer_id: str) -> CustomerStats:
    found = orders.find_by_customer(customer_id)
    paid: dict[str, Decimal] = {}
    for order in found:
        if order.status is OrderStatus.PAID:
            paid[order.total.currency] = paid.get(order.total.currency, Decimal("0")) + order.total.amount
    return CustomerStats(customer_id, len(found), paid)

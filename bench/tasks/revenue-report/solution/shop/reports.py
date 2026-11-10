from datetime import date
from typing import Protocol

from shop.money import Money
from shop.order import Order


class PaidOrders(Protocol):
    def paid_between(self, start: date, end: date) -> list[Order]:
        """Orders paid from start to end, both included."""
        ...


def revenue_by_currency(orders: PaidOrders, start: date, end: date) -> dict[str, Money]:
    """Revenue of the orders paid in the period, per currency. Currencies without payments are left out."""
    revenue: dict[str, Money] = {}
    for order in orders.paid_between(start, end):
        currency = order.total.currency
        revenue[currency] = revenue.get(currency, Money.zero(currency)).plus(order.total)
    return revenue

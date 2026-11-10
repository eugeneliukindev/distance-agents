from datetime import date

from shop.money import Money
from shop.order_store import OrderStore


def revenue_by_currency(store: OrderStore, start: date, end: date) -> dict[str, Money]:
    revenue: dict[str, Money] = {}
    for order in store.paid_between(start, end):
        currency = order.total.currency
        revenue[currency] = revenue.get(currency, Money.zero(currency)).plus(order.total)
    return revenue

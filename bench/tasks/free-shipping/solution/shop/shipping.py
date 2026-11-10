from decimal import Decimal

from shop.money import Money

FREE_SHIPPING_FROM = Decimal("5000")
SHIPPING_FEE = Decimal("300.00")


def ships_free(total: Money) -> bool:
    return total.amount >= FREE_SHIPPING_FROM


def shipping_cost(total: Money) -> Money:
    """Shipping for an order of this total, in the same currency."""
    return Money(Decimal("0.00") if ships_free(total) else SHIPPING_FEE, total.currency)

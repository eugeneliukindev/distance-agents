from decimal import Decimal

from shop.money import Money

COST_BY_ZONE = {1: Decimal("200.00"), 2: Decimal("350.00")}
FAR_ZONE_COST = Decimal("600.00")


def delivery_cost(zone: int | None, currency: str) -> Money:
    """Delivery cost for a zone; None means the customer collects the order and pays nothing."""
    if zone is None:
        return Money(Decimal("0.00"), currency)
    return Money(COST_BY_ZONE.get(zone, FAR_ZONE_COST), currency)

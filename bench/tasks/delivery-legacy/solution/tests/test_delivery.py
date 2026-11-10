import unittest
from datetime import datetime

from shop.delivery import delivery_date


class Order:
    def __init__(self, city: str, created_at: datetime) -> None:
        self.city = city
        self.created_at = created_at


class DeliveryDateTest(unittest.TestCase):
    """Pins the old behavior before the weekend change, then checks the change."""

    def test_moscow_takes_two_days(self) -> None:
        self.assertEqual(delivery_date(Order("Moscow", datetime(2026, 11, 9, 10))).isoformat(), "2026-11-11")

    def test_moskva_spelling_counts_as_moscow(self) -> None:
        self.assertEqual(delivery_date(Order("Moskva", datetime(2026, 11, 9, 10))).isoformat(), "2026-11-11")

    def test_other_cities_take_five_days(self) -> None:
        self.assertEqual(delivery_date(Order("Kazan", datetime(2026, 11, 9, 10))).isoformat(), "2026-11-14")

    def test_friday_adds_two_days(self) -> None:
        self.assertEqual(delivery_date(Order("Moscow", datetime(2026, 11, 13, 10))).isoformat(), "2026-11-17")

    def test_weekend_orders_count_from_monday(self) -> None:
        self.assertEqual(delivery_date(Order("Moscow", datetime(2026, 11, 14, 10))).isoformat(), "2026-11-18")
        self.assertEqual(delivery_date(Order("Moscow", datetime(2026, 11, 15, 10))).isoformat(), "2026-11-18")

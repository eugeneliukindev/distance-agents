import unittest

from _bench.support import call, make_app


class DeliveryDateTest(unittest.TestCase):
    """Dates in November 2026: the 9th is a Monday."""

    def setUp(self) -> None:
        self.app = make_app()

    def delivery(self, city: str, created_at: str) -> str:
        response = call(
            self.app, "POST", "/orders",
            {"customer_id": "c-1", "amount": "100.00", "currency": "RUB", "city": city, "created_at": created_at},
        )
        self.assertEqual(response.status, 201)
        result = call(self.app, "GET", f"/orders/{response.body['order_id']}/delivery-date")
        self.assertEqual(result.status, 200)
        return result.body["delivery_date"]

    def test_saturday_counts_from_monday(self) -> None:
        self.assertEqual(self.delivery("Moscow", "2026-11-14T10:00:00"), "2026-11-18")
        self.assertEqual(self.delivery("Kazan", "2026-11-14T23:59:00"), "2026-11-21")

    def test_sunday_counts_from_monday(self) -> None:
        self.assertEqual(self.delivery("Moscow", "2026-11-15T08:00:00"), "2026-11-18")
        self.assertEqual(self.delivery("Kazan", "2026-11-15T08:00:00"), "2026-11-21")

    def test_weekdays_are_unchanged(self) -> None:
        self.assertEqual(self.delivery("Moscow", "2026-11-09T10:00:00"), "2026-11-11")
        self.assertEqual(self.delivery("Kazan", "2026-11-12T10:00:00"), "2026-11-17")

    def test_friday_rule_is_unchanged(self) -> None:
        self.assertEqual(self.delivery("Moscow", "2026-11-13T10:00:00"), "2026-11-17")
        self.assertEqual(self.delivery("Kazan", "2026-11-13T10:00:00"), "2026-11-20")

    def test_old_spelling_of_moscow_still_counts(self) -> None:
        self.assertEqual(self.delivery("Moskva", "2026-11-09T10:00:00"), "2026-11-11")
        self.assertEqual(self.delivery("Moskva", "2026-11-14T10:00:00"), "2026-11-18")

    def test_unknown_order_is_404(self) -> None:
        self.assertEqual(call(self.app, "GET", "/orders/missing/delivery-date").status, 404)

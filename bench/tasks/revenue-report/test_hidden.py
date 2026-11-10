import unittest
from datetime import datetime, timedelta, timezone

from _bench.support import FakeService, call, create_order, make_app


class RevenueReportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.addCleanup(self.acquirer.close)
        self.app = make_app(acquirer_url=self.acquirer.url)
        self.today = datetime.now(timezone.utc).date()

    def paid_order(self, amount: str, currency: str = "RUB") -> str:
        order_id = create_order(self.app, amount=amount, currency=currency)
        response = call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})
        self.assertEqual(response.status, 200, response)
        return order_id

    def report(self, start: str, end: str):
        return call(self.app, "GET", f"/reports/revenue/{start}/{end}")

    def test_paid_orders_are_summed_per_currency(self) -> None:
        self.paid_order("1000.00")
        self.paid_order("950.50")
        self.paid_order("10.00", currency="USD")
        create_order(self.app, amount="500.00")  # not paid
        day = self.today.isoformat()
        response = self.report(day, day)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, {"from": day, "to": day, "revenue": {"RUB": "1950.50", "USD": "10.00"}})

    def test_period_without_payments_is_empty(self) -> None:
        self.paid_order("1000.00")
        yesterday = (self.today - timedelta(days=1)).isoformat()
        self.assertEqual(self.report("2020-01-01", yesterday).body["revenue"], {})

    def test_period_bounds_are_included(self) -> None:
        self.paid_order("1000.00")
        start = (self.today - timedelta(days=3)).isoformat()
        self.assertEqual(self.report(start, self.today.isoformat()).body["revenue"], {"RUB": "1000.00"})

    def test_paid_at_is_shown_on_the_order(self) -> None:
        order_id = create_order(self.app)
        self.assertIsNone(call(self.app, "GET", f"/orders/{order_id}").body["paid_at"])
        call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})
        self.assertEqual(call(self.app, "GET", f"/orders/{order_id}").body["paid_at"], self.today.isoformat())

    def test_invalid_period_is_400(self) -> None:
        for start, end in (("2026-13-01", "2026-12-31"), ("yesterday", "2026-12-31"), ("2026-11-30", "2026-11-01")):
            with self.subTest(start=start, end=end):
                self.assertEqual(self.report(start, end).status, 400)

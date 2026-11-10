import unittest

from _bench.support import FakeService, call, make_app


class CustomerStatsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.addCleanup(self.acquirer.close)
        self.app = make_app(acquirer_url=self.acquirer.url)

    def order(self, customer_id: str, amount: str, currency: str = "RUB", paid: bool = True) -> None:
        response = call(self.app, "POST", "/orders", {"customer_id": customer_id, "amount": amount, "currency": currency})
        self.assertEqual(response.status, 201)
        if paid:
            pay = call(self.app, "POST", f"/orders/{response.body['order_id']}/pay", {"card_token": "tok"})
            self.assertEqual(pay.status, 200)

    def stats(self, customer_id: str) -> dict:
        response = call(self.app, "GET", f"/customers/{customer_id}/stats")
        self.assertEqual(response.status, 200)
        return response.body

    def test_customer_without_orders(self) -> None:
        self.assertEqual(self.stats("c-0"), {"customer_id": "c-0", "orders": 0, "paid": {}})

    def test_paid_totals_per_currency(self) -> None:
        self.order("c-7", "1000.00")
        self.order("c-7", "950.50")
        self.order("c-7", "10.00", currency="USD")
        self.assertEqual(self.stats("c-7"), {"customer_id": "c-7", "orders": 3, "paid": {"RUB": "1950.50", "USD": "10.00"}})

    def test_unpaid_orders_count_but_add_nothing(self) -> None:
        self.order("c-7", "500.00")
        self.order("c-7", "70.00", currency="EUR", paid=False)
        self.assertEqual(self.stats("c-7"), {"customer_id": "c-7", "orders": 2, "paid": {"RUB": "500.00"}})

    def test_other_customers_are_not_counted(self) -> None:
        self.order("c-7", "100.00")
        self.order("c-8", "200.00")
        self.assertEqual(self.stats("c-8"), {"customer_id": "c-8", "orders": 1, "paid": {"RUB": "200.00"}})

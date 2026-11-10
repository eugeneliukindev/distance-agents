import unittest

from _bench.support import FakeService, call, create_order, make_app


class GoldDiscountTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.addCleanup(self.acquirer.close)
        self.app = make_app(acquirer_url=self.acquirer.url)

    def register(self, level: int) -> None:
        response = call(self.app, "POST", "/customers", {"customer_id": "c-1", "name": "Ann", "loyalty_level": level})
        self.assertEqual(response.status, 201)

    def charged(self, amount: str = "1000.00") -> str:
        order_id = create_order(self.app, amount=amount)
        response = call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["amount"], amount)
        return self.acquirer.requests[-1][1]["amount"]

    def test_level_three_gets_five_percent_off(self) -> None:
        self.register(3)
        self.assertEqual(self.charged(), "950.00")

    def test_higher_levels_get_the_discount(self) -> None:
        self.register(5)
        self.assertEqual(self.charged(), "950.00")

    def test_level_two_pays_full_total(self) -> None:
        self.register(2)
        self.assertEqual(self.charged(), "1000.00")

    def test_unregistered_customer_pays_full_total(self) -> None:
        self.assertEqual(self.charged(), "1000.00")

    def test_discount_is_rounded_to_cents(self) -> None:
        self.register(3)
        self.assertEqual(self.charged("99.99"), "94.99")

    def test_level_at_payment_time_counts(self) -> None:
        self.register(1)
        order_id = create_order(self.app)
        self.register(4)
        call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})
        self.assertEqual(self.acquirer.requests[-1][1]["amount"], "950.00")

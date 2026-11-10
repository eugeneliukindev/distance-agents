import unittest

from _bench.support import FakeService, call, create_order, make_app


class FreeShippingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.addCleanup(self.acquirer.close)
        self.app = make_app(acquirer_url=self.acquirer.url)

    def order(self, amount: str) -> dict:
        return call(self.app, "GET", f"/orders/{create_order(self.app, amount=amount)}").body

    def charged_for(self, amount: str) -> str:
        order_id = create_order(self.app, amount=amount)
        response = call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})
        self.assertEqual(response.status, 200)
        return self.acquirer.requests[-1][1]["amount"]

    def test_small_order_pays_for_shipping(self) -> None:
        body = self.order("1000.00")
        self.assertEqual((body["shipping_cost"], body["free_shipping"], body["amount"]), ("300.00", False, "1000.00"))

    def test_threshold_is_inclusive(self) -> None:
        body = self.order("5000.00")
        self.assertEqual((body["shipping_cost"], body["free_shipping"]), ("0.00", True))

    def test_just_below_threshold(self) -> None:
        self.assertEqual(self.order("4999.99")["free_shipping"], False)

    def test_card_is_charged_total_plus_shipping(self) -> None:
        self.assertEqual(self.charged_for("1000.00"), "1300.00")

    def test_free_shipping_order_is_charged_total(self) -> None:
        self.assertEqual(self.charged_for("6000.00"), "6000.00")

    def test_responses_include_shipping(self) -> None:
        response = call(self.app, "POST", "/orders", {"customer_id": "c-1", "amount": "100.00", "currency": "RUB"})
        self.assertEqual(response.body["shipping_cost"], "300.00")
        paid = call(self.app, "POST", f"/orders/{response.body['order_id']}/pay", {"card_token": "tok"})
        self.assertEqual((paid.body["shipping_cost"], paid.body["free_shipping"]), ("300.00", False))

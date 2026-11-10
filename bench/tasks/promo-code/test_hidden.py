import unittest

from _bench.support import FakeService, call, create_order, make_app


class PromoCodeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.addCleanup(self.acquirer.close)
        self.app = make_app(acquirer_url=self.acquirer.url)

    def pay(self, order_id: str, **extra: str):
        return call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok", **extra})

    def test_welcome5_charges_five_percent_less(self) -> None:
        order_id = create_order(self.app, amount="1000.00")
        response = self.pay(order_id, promo_code="WELCOME5")
        self.assertEqual(response.status, 200)
        self.assertEqual(self.acquirer.requests[0][1]["amount"], "950.00")
        self.assertEqual(call(self.app, "GET", f"/orders/{order_id}").body["paid_amount"], "950.00")

    def test_discount_is_rounded_to_cents(self) -> None:
        order_id = create_order(self.app, amount="99.99")
        self.pay(order_id, promo_code="WELCOME5")
        self.assertEqual(self.acquirer.requests[0][1]["amount"], "94.99")

    def test_no_code_charges_full_total(self) -> None:
        order_id = create_order(self.app, amount="1000.00")
        self.assertIsNone(call(self.app, "GET", f"/orders/{order_id}").body["paid_amount"])
        self.pay(order_id)
        self.assertEqual(self.acquirer.requests[0][1]["amount"], "1000.00")
        self.assertEqual(call(self.app, "GET", f"/orders/{order_id}").body["paid_amount"], "1000.00")

    def test_unknown_code_is_422_and_nothing_is_charged(self) -> None:
        order_id = create_order(self.app)
        response = self.pay(order_id, promo_code="FREE100")
        self.assertEqual((response.status, response.body), (422, {"error": "unknown promo code"}))
        self.assertEqual(self.acquirer.requests, [])
        self.assertEqual(call(self.app, "GET", f"/orders/{order_id}").body["status"], "new")

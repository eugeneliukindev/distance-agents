import unittest

from _bench.support import FakeService, call, create_order, make_app


class GiftCardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "card-pay"})
        self.gift = FakeService(200, {"payment_id": "gift-pay"})
        self.addCleanup(self.acquirer.close)
        self.addCleanup(self.gift.close)
        self.app = make_app(acquirer_url=self.acquirer.url, gift_card_url=self.gift.url)
        self.order_id = create_order(self.app)

    def pay(self, body: dict):
        return call(self.app, "POST", f"/orders/{self.order_id}/pay", body)

    def status(self) -> str:
        return call(self.app, "GET", f"/orders/{self.order_id}").body["status"]

    def test_gift_card_marks_paid(self) -> None:
        response = self.pay({"method": "gift_card", "gift_card_code": "GC-1"})
        self.assertEqual((response.status, response.body["payment_id"]), (200, "gift-pay"))
        self.assertEqual(self.gift.requests[0], ("/redeem", {"code": "GC-1", "amount": "1000.00", "currency": "RUB"}))

    def test_low_balance_is_402_and_order_stays_new(self) -> None:
        self.gift.status = 409
        response = self.pay({"method": "gift_card", "gift_card_code": "GC-1"})
        self.assertEqual((response.status, response.body), (402, {"error": "gift card balance is too low"}))
        self.assertEqual(self.status(), "new")

    def test_gift_card_service_failure_is_503(self) -> None:
        self.gift.status = 500
        self.assertEqual(self.pay({"method": "gift_card", "gift_card_code": "GC-1"}).status, 503)
        self.assertEqual(self.status(), "new")

    def test_missing_code_is_400(self) -> None:
        self.assertEqual(self.pay({"method": "gift_card"}).status, 400)

    def test_other_methods_still_work(self) -> None:
        self.assertEqual(self.pay({"method": "cash"}).body["status"], "awaiting_cash")

import unittest

from _bench.support import FakeService, call, create_order, make_app


class PaymentMethodsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "card-pay"})
        self.sbp = FakeService(200, {"payment_id": "sbp-pay"})
        self.addCleanup(self.acquirer.close)
        self.addCleanup(self.sbp.close)
        self.app = make_app(acquirer_url=self.acquirer.url, sbp_url=self.sbp.url)
        self.order_id = create_order(self.app)

    def pay(self, body: dict):
        return call(self.app, "POST", f"/orders/{self.order_id}/pay", body)

    def test_explicit_card(self) -> None:
        response = self.pay({"method": "card", "card_token": "tok"})
        self.assertEqual((response.status, response.body["status"]), (200, "paid"))

    def test_cash_charges_nothing(self) -> None:
        response = self.pay({"method": "cash"})
        self.assertEqual((response.status, response.body["status"]), (200, "awaiting_cash"))
        self.assertEqual(self.acquirer.requests + self.sbp.requests, [])

    def test_sbp_marks_paid(self) -> None:
        response = self.pay({"method": "sbp"})
        self.assertEqual((response.status, response.body["status"]), (200, "paid"))
        self.assertEqual(response.body["payment_id"], "sbp-pay")
        path, body = self.sbp.requests[0]
        self.assertEqual(path, "/payments")
        self.assertEqual(body, {"order_id": self.order_id, "amount": "1000.00", "currency": "RUB"})

    def test_sbp_failure_is_503_and_order_stays_new(self) -> None:
        self.sbp.status = 500
        self.assertEqual(self.pay({"method": "sbp"}).status, 503)
        self.assertEqual(call(self.app, "GET", f"/orders/{self.order_id}").body["status"], "new")

    def test_sbp_unreachable_is_503(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url)
        order_id = create_order(app)
        self.assertEqual(call(app, "POST", f"/orders/{order_id}/pay", {"method": "sbp"}).status, 503)

    def test_unknown_method_is_400(self) -> None:
        self.assertEqual(self.pay({"method": "bitcoin"}).status, 400)

    def test_cash_order_cannot_be_paid_again(self) -> None:
        self.pay({"method": "cash"})
        self.assertEqual(self.pay({"method": "card", "card_token": "tok"}).status, 409)

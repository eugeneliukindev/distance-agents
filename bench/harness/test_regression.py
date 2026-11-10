"""PASS_TO_PASS: behavior that every task must keep."""

import unittest

from _bench.support import FakeService, call, create_order, make_app


class RegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.addCleanup(self.acquirer.close)
        self.app = make_app(acquirer_url=self.acquirer.url)

    def test_created_order_is_new(self) -> None:
        order_id = create_order(self.app)
        response = call(self.app, "GET", f"/orders/{order_id}")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["status"], "new")
        self.assertEqual(response.body["amount"], "1000.00")

    def test_unknown_order_is_404(self) -> None:
        self.assertEqual(call(self.app, "GET", "/orders/missing").status, 404)

    def test_card_payment_marks_order_paid(self) -> None:
        order_id = create_order(self.app)
        response = call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["status"], "paid")
        self.assertEqual(response.body["payment_id"], "pay-1")
        self.assertEqual(self.acquirer.requests[0][0], "/charges")

    def test_paying_twice_is_409(self) -> None:
        order_id = create_order(self.app)
        call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})
        response = call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})
        self.assertEqual(response.status, 409)

    def test_declined_card_is_402_and_order_stays_new(self) -> None:
        self.acquirer.status = 402
        order_id = create_order(self.app)
        self.assertEqual(call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"}).status, 402)
        self.assertEqual(call(self.app, "GET", f"/orders/{order_id}").body["status"], "new")

    def test_acquirer_down_is_503(self) -> None:
        app = make_app()
        order_id = create_order(app)
        self.assertEqual(call(app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"}).status, 503)

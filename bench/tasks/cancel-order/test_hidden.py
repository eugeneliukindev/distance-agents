import unittest

from _bench.support import FakeService, call, create_order, make_app


class CancelOrderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.addCleanup(self.acquirer.close)
        self.app = make_app(acquirer_url=self.acquirer.url)
        self.order_id = create_order(self.app)

    def cancel(self, order_id: str | None = None):
        return call(self.app, "POST", f"/orders/{order_id or self.order_id}/cancel")

    def status(self) -> str:
        return call(self.app, "GET", f"/orders/{self.order_id}").body["status"]

    def test_new_order_is_cancelled(self) -> None:
        response = self.cancel()
        self.assertEqual((response.status, response.body["status"]), (200, "cancelled"))
        self.assertEqual(self.status(), "cancelled")

    def test_cancelling_twice_is_fine(self) -> None:
        self.cancel()
        response = self.cancel()
        self.assertEqual((response.status, response.body["status"]), (200, "cancelled"))

    def test_paid_order_cannot_be_cancelled(self) -> None:
        call(self.app, "POST", f"/orders/{self.order_id}/pay", {"card_token": "tok"})
        response = self.cancel()
        self.assertEqual(response.status, 409)
        self.assertIn("error", response.body)
        self.assertEqual(self.status(), "paid")

    def test_cancelled_order_cannot_be_paid(self) -> None:
        self.cancel()
        response = call(self.app, "POST", f"/orders/{self.order_id}/pay", {"card_token": "tok"})
        self.assertEqual(response.status, 409)
        self.assertEqual(self.acquirer.requests, [])
        self.assertEqual(self.status(), "cancelled")

    def test_unknown_order_is_404(self) -> None:
        self.assertEqual(self.cancel("missing").status, 404)

import unittest

from _bench.support import FakeService, call, create_order, make_app


class RefundTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.tasks = FakeService(201, {"task_id": "t-1"})
        self.addCleanup(self.acquirer.close)
        self.addCleanup(self.tasks.close)
        self.app = make_app(acquirer_url=self.acquirer.url, tasks_url=self.tasks.url)
        self.order_id = create_order(self.app)

    def pay(self, body: dict) -> None:
        response = call(self.app, "POST", f"/orders/{self.order_id}/pay", body)
        self.assertEqual(response.status, 200, response)

    def refund(self):
        return call(self.app, "POST", f"/orders/{self.order_id}/refund")

    def status(self) -> str:
        return call(self.app, "GET", f"/orders/{self.order_id}").body["status"]

    def test_card_order_is_refunded_through_the_acquirer(self) -> None:
        self.pay({"card_token": "tok"})
        response = self.refund()
        self.assertEqual((response.status, response.body["status"]), (200, "refunded"))
        self.assertEqual(
            self.acquirer.requests[-1], ("/refunds", {"payment_id": "pay-1", "amount": "1000.00", "currency": "RUB"})
        )
        self.assertEqual(self.tasks.requests, [])
        self.assertEqual(self.status(), "refunded")

    def test_card_refund_failure_is_503_and_order_stays_paid(self) -> None:
        self.pay({"card_token": "tok"})
        self.acquirer.status = 500
        self.assertEqual(self.refund().status, 503)
        self.assertEqual(self.status(), "paid")

    def test_cash_order_gets_an_operator_task(self) -> None:
        self.pay({"method": "cash"})
        response = self.refund()
        self.assertEqual((response.status, response.body["status"]), (200, "refund_pending"))
        self.assertEqual(
            self.tasks.requests,
            [("/tasks", {"type": "cash_refund", "order_id": self.order_id, "amount": "1000.00", "currency": "RUB"})],
        )
        self.assertEqual([path for path, _ in self.acquirer.requests], [])
        self.assertEqual(self.status(), "refund_pending")

    def test_task_service_failure_is_503_and_order_stays_awaiting_cash(self) -> None:
        self.pay({"method": "cash"})
        self.tasks.status = 500
        self.assertEqual(self.refund().status, 503)
        self.assertEqual(self.status(), "awaiting_cash")

    def test_task_service_unreachable_is_503(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url)
        order_id = create_order(app)
        call(app, "POST", f"/orders/{order_id}/pay", {"method": "cash"})
        self.assertEqual(call(app, "POST", f"/orders/{order_id}/refund").status, 503)

    def test_new_order_cannot_be_refunded(self) -> None:
        self.assertEqual(self.refund().status, 409)

    def test_refunded_order_cannot_be_refunded_again(self) -> None:
        self.pay({"card_token": "tok"})
        self.refund()
        self.assertEqual(self.refund().status, 409)
        self.assertEqual([path for path, _ in self.acquirer.requests].count("/refunds"), 1)

    def test_unknown_order_is_404(self) -> None:
        self.assertEqual(call(self.app, "POST", "/orders/missing/refund").status, 404)

import unittest

from _bench.support import FakeService, call, create_order, make_app


class CourierTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.courier = FakeService(201, {"tracking_number": "TRK-1"})
        self.addCleanup(self.acquirer.close)
        self.addCleanup(self.courier.close)

    def paid_order(self, app) -> tuple[str, object]:
        order_id = create_order(app)
        return order_id, call(app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})

    def test_new_order_has_no_shipping(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url, courier_url=self.courier.url)
        body = call(app, "GET", f"/orders/{create_order(app)}").body
        self.assertEqual((body["shipping_status"], body["tracking_number"]), (None, None))
        self.assertEqual(self.courier.requests, [])

    def test_paid_order_is_registered_with_courier(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url, courier_url=self.courier.url)
        order_id, response = self.paid_order(app)
        self.assertEqual(response.status, 200)
        self.assertEqual((response.body["shipping_status"], response.body["tracking_number"]), ("registered", "TRK-1"))
        self.assertEqual(self.courier.requests, [("/shipments", {"order_id": order_id})])
        body = call(app, "GET", f"/orders/{order_id}").body
        self.assertEqual((body["status"], body["shipping_status"], body["tracking_number"]), ("paid", "registered", "TRK-1"))

    def test_courier_error_keeps_payment_and_marks_pending(self) -> None:
        self.courier.status = 500
        app = make_app(acquirer_url=self.acquirer.url, courier_url=self.courier.url)
        order_id, response = self.paid_order(app)
        self.assertEqual((response.status, response.body["status"]), (200, "paid"))
        body = call(app, "GET", f"/orders/{order_id}").body
        self.assertEqual((body["shipping_status"], body["tracking_number"]), ("pending", None))

    def test_courier_unreachable_keeps_payment_and_marks_pending(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url)
        order_id, response = self.paid_order(app)
        self.assertEqual((response.status, response.body["status"]), (200, "paid"))
        self.assertEqual(call(app, "GET", f"/orders/{order_id}").body["shipping_status"], "pending")

    def test_declined_payment_does_not_call_courier(self) -> None:
        self.acquirer.status = 402
        app = make_app(acquirer_url=self.acquirer.url, courier_url=self.courier.url)
        self.paid_order(app)
        self.assertEqual(self.courier.requests, [])

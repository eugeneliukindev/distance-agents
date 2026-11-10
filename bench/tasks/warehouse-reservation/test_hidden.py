import unittest

from _bench.support import FakeService, call, create_order, make_app


class ReservationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.warehouse = FakeService(201, {"reservation_id": "R-1"})
        self.addCleanup(self.acquirer.close)
        self.addCleanup(self.warehouse.close)
        self.app = make_app(acquirer_url=self.acquirer.url, warehouse_url=self.warehouse.url)
        self.order_id = create_order(self.app)

    def reserve(self, order_id: str | None = None):
        return call(self.app, "POST", f"/orders/{order_id or self.order_id}/reservation")

    def reservation_id(self) -> str | None:
        return call(self.app, "GET", f"/orders/{self.order_id}").body["reservation_id"]

    def test_new_order_has_no_reservation(self) -> None:
        self.assertIsNone(self.reservation_id())

    def test_reservation_is_saved(self) -> None:
        response = self.reserve()
        self.assertEqual((response.status, response.body["reservation_id"]), (200, "R-1"))
        self.assertEqual(self.warehouse.requests, [("/reservations", {"order_id": self.order_id})])
        self.assertEqual(self.reservation_id(), "R-1")

    def test_out_of_stock_is_409(self) -> None:
        self.warehouse.status = 409
        response = self.reserve()
        self.assertEqual((response.status, response.body), (409, {"error": "out of stock"}))
        self.assertIsNone(self.reservation_id())

    def test_warehouse_failure_is_503(self) -> None:
        self.warehouse.status = 500
        self.assertEqual(self.reserve().status, 503)
        self.assertIsNone(self.reservation_id())

    def test_warehouse_unreachable_is_503(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url)
        order_id = create_order(app)
        self.assertEqual(call(app, "POST", f"/orders/{order_id}/reservation").status, 503)

    def test_second_reservation_returns_the_first(self) -> None:
        self.reserve()
        self.warehouse.body = {"reservation_id": "R-2"}
        response = self.reserve()
        self.assertEqual((response.status, response.body["reservation_id"]), (200, "R-1"))
        self.assertEqual(len(self.warehouse.requests), 1)

    def test_paid_order_cannot_be_reserved(self) -> None:
        call(self.app, "POST", f"/orders/{self.order_id}/pay", {"card_token": "tok"})
        self.assertEqual(self.reserve().status, 409)
        self.assertEqual(self.warehouse.requests, [])

    def test_unknown_order_is_404(self) -> None:
        self.assertEqual(self.reserve("missing").status, 404)

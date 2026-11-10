import unittest

from _bench.support import FakeService, call, create_order, make_app


class DeliveryOptionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.courier = FakeService(201, {"slot": "SLOT-7"})
        self.post = FakeService(201, {"tracking_number": "RA123"})
        for service in (self.acquirer, self.courier, self.post):
            self.addCleanup(service.close)
        self.app = make_app(acquirer_url=self.acquirer.url, courier_url=self.courier.url, post_url=self.post.url)
        self.order_id = create_order(self.app)

    def pay(self, **body: str):
        return call(self.app, "POST", f"/orders/{self.order_id}/pay", {"card_token": "tok", **body})

    def order(self) -> dict:
        return call(self.app, "GET", f"/orders/{self.order_id}").body

    def delivery(self) -> tuple:
        body = self.order()
        return body["delivery_type"], body["delivery_reference"]

    def test_new_order_has_no_delivery(self) -> None:
        self.assertEqual(self.delivery(), (None, None))

    def test_default_is_pickup_at_first_point(self) -> None:
        self.assertEqual(self.pay().status, 200)
        self.assertEqual(self.delivery(), ("pickup", "PP-1"))
        self.assertEqual(self.courier.requests + self.post.requests, [])

    def test_pickup_at_chosen_point(self) -> None:
        response = self.pay(delivery="pickup", pickup_point="PP-3")
        self.assertEqual((response.status, response.body["delivery_reference"]), (200, "PP-3"))

    def test_unknown_pickup_point_is_400_and_nothing_charged(self) -> None:
        self.assertEqual(self.pay(delivery="pickup", pickup_point="PP-9").status, 400)
        self.assertEqual(self.acquirer.requests, [])

    def test_courier_books_a_slot(self) -> None:
        response = self.pay(delivery="courier")
        self.assertEqual((response.status, response.body["status"]), (200, "paid"))
        self.assertEqual(self.courier.requests, [("/slots", {"order_id": self.order_id})])
        self.assertEqual(self.delivery(), ("courier", "SLOT-7"))

    def test_post_registers_a_parcel(self) -> None:
        self.assertEqual(self.pay(delivery="post").status, 200)
        self.assertEqual(self.post.requests, [("/parcels", {"order_id": self.order_id})])
        self.assertEqual(self.delivery(), ("post", "RA123"))

    def test_courier_failure_is_503_and_nothing_charged(self) -> None:
        self.courier.status = 500
        self.assertEqual(self.pay(delivery="courier").status, 503)
        self.assertEqual(self.acquirer.requests, [])
        self.assertEqual(self.order()["status"], "new")

    def test_post_unreachable_is_503(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url, courier_url=self.courier.url)
        order_id = create_order(app)
        self.assertEqual(call(app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok", "delivery": "post"}).status, 503)
        self.assertEqual(self.acquirer.requests, [])

    def test_unknown_delivery_is_400(self) -> None:
        self.assertEqual(self.pay(delivery="drone").status, 400)
        self.assertEqual(self.acquirer.requests, [])

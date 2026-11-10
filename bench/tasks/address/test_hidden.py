import unittest

from _bench.support import call, create_order, make_app


class AddressTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = make_app()
        self.order_id = create_order(self.app)

    def put(self, body: dict, order_id: str | None = None):
        return call(self.app, "PUT", f"/orders/{order_id or self.order_id}/address", body)

    def test_new_order_has_no_address(self) -> None:
        self.assertIsNone(call(self.app, "GET", f"/orders/{self.order_id}").body["address"])

    def test_valid_address_is_saved(self) -> None:
        response = self.put({"zip": "101000", "street": "Tverskaya 1"})
        self.assertEqual(response.status, 200)
        body = call(self.app, "GET", f"/orders/{self.order_id}").body
        self.assertEqual(body["address"], {"zip": "101000", "street": "Tverskaya 1"})

    def test_address_can_be_changed(self) -> None:
        self.put({"zip": "101000", "street": "Tverskaya 1"})
        self.put({"zip": "620000", "street": "Lenina 5"})
        self.assertEqual(call(self.app, "GET", f"/orders/{self.order_id}").body["address"]["zip"], "620000")

    def test_invalid_input_is_422(self) -> None:
        for body in ({"zip": "12345", "street": "A"}, {"zip": "12345a", "street": "A"},
                     {"zip": "123456", "street": "   "}, {"zip": 123456, "street": "A"}, {"street": "A"}):
            with self.subTest(body=body):
                self.assertEqual(self.put(body).status, 422)
        self.assertIsNone(call(self.app, "GET", f"/orders/{self.order_id}").body["address"])

    def test_unknown_order_is_404(self) -> None:
        self.assertEqual(self.put({"zip": "101000", "street": "A"}, order_id="missing").status, 404)
        self.assertEqual(call(self.app, "GET", "/orders/missing/delivery-estimate").status, 404)

    def test_delivery_estimate(self) -> None:
        self.put({"zip": "101000", "street": "A"})
        self.assertEqual(call(self.app, "GET", f"/orders/{self.order_id}/delivery-estimate").body, {"days": 2})
        self.put({"zip": "620000", "street": "A"})
        self.assertEqual(call(self.app, "GET", f"/orders/{self.order_id}/delivery-estimate").body, {"days": 5})

    def test_estimate_without_address_is_409(self) -> None:
        self.assertEqual(call(self.app, "GET", f"/orders/{self.order_id}/delivery-estimate").status, 409)

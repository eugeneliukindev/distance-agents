import unittest

from _bench.support import FakeService, call, create_order, make_app


class DeliveryZoneTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.addCleanup(self.acquirer.close)
        self.app = make_app(acquirer_url=self.acquirer.url)

    def register(self, city: str, zone: int) -> None:
        body = {"customer_id": "c-1", "name": "Ann", "street": "Lenina 1", "city": city, "zone": zone}
        self.assertEqual(call(self.app, "POST", "/customers", body).status, 201)

    def pay(self, amount: str = "1000.00"):
        order_id = create_order(self.app, amount=amount)
        response = call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["amount"], amount)
        return response.body["delivery_cost"], self.acquirer.requests[-1][1]["amount"]

    def test_zone_one(self) -> None:
        self.register("Moscow", 1)
        self.assertEqual(self.pay(), ("200.00", "1200.00"))

    def test_zone_two(self) -> None:
        self.register("Tver", 2)
        self.assertEqual(self.pay(), ("350.00", "1350.00"))

    def test_far_zones(self) -> None:
        for zone in (3, 7):
            with self.subTest(zone=zone):
                self.register("Far", zone)
                self.assertEqual(self.pay(), ("600.00", "1600.00"))

    def test_unregistered_customer_pays_no_delivery(self) -> None:
        self.assertEqual(self.pay(), ("0.00", "1000.00"))

    def test_moving_changes_the_zone(self) -> None:
        self.register("Moscow", 1)
        self.pay()
        self.register("Omsk", 3)
        self.assertEqual(self.pay("50.50"), ("600.00", "650.50"))

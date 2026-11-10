import unittest

from _bench.support import call, make_app


class CustomersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = make_app()

    def register(self, name: str = "Anna", email: str = "anna@example.com"):
        return call(self.app, "POST", "/customers", {"name": name, "email": email})

    def order_for(self, customer_id: str) -> dict:
        response = call(self.app, "POST", "/orders", {"customer_id": customer_id, "amount": "500.00", "currency": "RUB"})
        self.assertEqual(response.status, 201)
        return response.body

    def test_registered_customer_can_be_read_back(self) -> None:
        created = self.register()
        self.assertEqual(created.status, 201)
        customer_id = created.body["customer_id"]
        self.assertEqual(created.body, {"customer_id": customer_id, "name": "Anna", "email": "anna@example.com"})
        self.assertEqual(call(self.app, "GET", f"/customers/{customer_id}").body, created.body)

    def test_customers_get_different_ids(self) -> None:
        first = self.register("Anna", "anna@example.com").body["customer_id"]
        second = self.register("Boris", "boris@example.com").body["customer_id"]
        self.assertNotEqual(first, second)
        self.assertEqual(call(self.app, "GET", f"/customers/{second}").body["name"], "Boris")

    def test_unknown_customer_is_404(self) -> None:
        self.assertEqual(call(self.app, "GET", "/customers/nobody").status, 404)

    def test_invalid_customer_is_400(self) -> None:
        for body in ({"name": "Anna"}, {"email": "a@example.com"}, {"name": "", "email": "a@example.com"},
                     {"name": "Anna", "email": 5}):
            with self.subTest(body=body):
                self.assertEqual(call(self.app, "POST", "/customers", body).status, 400)

    def test_order_shows_registered_customer_name(self) -> None:
        customer_id = self.register().body["customer_id"]
        order = self.order_for(customer_id)
        self.assertEqual(order["customer_name"], "Anna")
        self.assertEqual(call(self.app, "GET", f"/orders/{order['order_id']}").body["customer_name"], "Anna")

    def test_guest_order_has_no_customer_name(self) -> None:
        order = self.order_for("guest-42")
        self.assertIsNone(call(self.app, "GET", f"/orders/{order['order_id']}").body["customer_name"])

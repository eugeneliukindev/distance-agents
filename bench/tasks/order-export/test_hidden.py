import unittest

from _bench.support import FakeService, call, create_order, make_app

HEADER = "order_id,customer_id,amount,currency,status\r\n"


class OrderExportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.addCleanup(self.acquirer.close)
        self.app = make_app(acquirer_url=self.acquirer.url)

    def export(self, order_id: str):
        return call(self.app, "GET", f"/orders/{order_id}/export")

    def test_new_order(self) -> None:
        order_id = create_order(self.app, amount="1000.00")
        response = self.export(order_id)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, {"csv": HEADER + f"{order_id},c-1,1000.00,RUB,new\r\n"})

    def test_paid_order_shows_status(self) -> None:
        order_id = create_order(self.app)
        call(self.app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})
        self.assertTrue(self.export(order_id).body["csv"].endswith(",paid\r\n"))

    def test_values_are_quoted(self) -> None:
        response = call(self.app, "POST", "/orders", {"customer_id": 'Acme, "Ltd"', "amount": "5.50", "currency": "RUB"})
        order_id = response.body["order_id"]
        self.assertEqual(self.export(order_id).body["csv"], HEADER + f'{order_id},"Acme, ""Ltd""",5.50,RUB,new\r\n')

    def test_unknown_order_is_404(self) -> None:
        self.assertEqual(self.export("missing").status, 404)

import unittest

from _bench.support import FakeService, call, create_order, make_app


class FiscalReceiptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.fiscal = FakeService(201, {"fiscal_number": "FN-7"})
        self.addCleanup(self.acquirer.close)
        self.addCleanup(self.fiscal.close)

    def paid_order(self, app, amount: str = "1000.00") -> tuple[str, object]:
        order_id = create_order(app, amount=amount)
        return order_id, call(app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})

    def test_new_order_has_no_receipt(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url, fiscal_url=self.fiscal.url)
        body = call(app, "GET", f"/orders/{create_order(app)}").body
        self.assertEqual((body["fiscal_status"], body["fiscal_number"]), (None, None))
        self.assertEqual(self.fiscal.requests, [])

    def test_paid_order_gets_a_receipt(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url, fiscal_url=self.fiscal.url)
        order_id, response = self.paid_order(app, amount="1250.50")
        self.assertEqual(response.status, 200)
        self.assertEqual((response.body["fiscal_status"], response.body["fiscal_number"]), ("registered", "FN-7"))
        self.assertEqual(self.fiscal.requests, [("/receipts", {"order_id": order_id, "amount": "1250.50", "currency": "RUB"})])
        body = call(app, "GET", f"/orders/{order_id}").body
        self.assertEqual((body["status"], body["fiscal_status"], body["fiscal_number"]), ("paid", "registered", "FN-7"))

    def test_tax_service_error_keeps_payment_and_marks_retry(self) -> None:
        self.fiscal.status = 503
        app = make_app(acquirer_url=self.acquirer.url, fiscal_url=self.fiscal.url)
        order_id, response = self.paid_order(app)
        self.assertEqual((response.status, response.body["status"]), (200, "paid"))
        body = call(app, "GET", f"/orders/{order_id}").body
        self.assertEqual((body["fiscal_status"], body["fiscal_number"]), ("retry", None))

    def test_unexpected_answer_marks_retry(self) -> None:
        self.fiscal.body = {"unexpected": True}
        app = make_app(acquirer_url=self.acquirer.url, fiscal_url=self.fiscal.url)
        order_id, _ = self.paid_order(app)
        self.assertEqual(call(app, "GET", f"/orders/{order_id}").body["fiscal_status"], "retry")

    def test_tax_service_unreachable_keeps_payment_and_marks_retry(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url)
        order_id, response = self.paid_order(app)
        self.assertEqual((response.status, response.body["status"]), (200, "paid"))
        self.assertEqual(call(app, "GET", f"/orders/{order_id}").body["fiscal_status"], "retry")

    def test_declined_payment_has_no_receipt(self) -> None:
        self.acquirer.status = 402
        app = make_app(acquirer_url=self.acquirer.url, fiscal_url=self.fiscal.url)
        order_id, response = self.paid_order(app)
        self.assertEqual(response.status, 402)
        self.assertEqual(self.fiscal.requests, [])
        self.assertIsNone(call(app, "GET", f"/orders/{order_id}").body["fiscal_status"])

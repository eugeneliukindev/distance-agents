import unittest

from _bench.support import FakeService, call, make_app


class PaymentEmailTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.mailer = FakeService(200, {"ok": True})
        self.addCleanup(self.acquirer.close)
        self.addCleanup(self.mailer.close)

    def order(self, app, **extra: object) -> str:
        response = call(app, "POST", "/orders", {"customer_id": "c-1", "amount": "1000.00", "currency": "RUB", **extra})
        self.assertEqual(response.status, 201)
        return response.body["order_id"]

    def pay(self, app, order_id: str):
        return call(app, "POST", f"/orders/{order_id}/pay", {"card_token": "tok"})

    def test_paid_order_with_email_sends_mail(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url, mailer_url=self.mailer.url)
        order_id = self.order(app, email="ann@example.com")
        response = self.pay(app, order_id)
        self.assertEqual((response.status, response.body["status"]), (200, "paid"))
        self.assertEqual(
            self.mailer.requests,
            [("/send", {"to": "ann@example.com", "template": "order_paid", "order_id": order_id})],
        )

    def test_email_is_saved(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url, mailer_url=self.mailer.url)
        order_id = self.order(app, email="ann@example.com")
        self.assertEqual(call(app, "GET", f"/orders/{order_id}").body["email"], "ann@example.com")
        self.assertIsNone(call(app, "GET", f"/orders/{self.order(app)}").body["email"])

    def test_order_without_email_sends_nothing(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url, mailer_url=self.mailer.url)
        self.assertEqual(self.pay(app, self.order(app)).status, 200)
        self.assertEqual(self.mailer.requests, [])

    def test_mail_error_does_not_fail_payment(self) -> None:
        self.mailer.status = 500
        app = make_app(acquirer_url=self.acquirer.url, mailer_url=self.mailer.url)
        order_id = self.order(app, email="ann@example.com")
        response = self.pay(app, order_id)
        self.assertEqual((response.status, response.body["status"]), (200, "paid"))
        self.assertEqual(call(app, "GET", f"/orders/{order_id}").body["status"], "paid")

    def test_unreachable_mailer_does_not_fail_payment(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url)
        response = self.pay(app, self.order(app, email="ann@example.com"))
        self.assertEqual((response.status, response.body["status"]), (200, "paid"))

    def test_declined_payment_sends_nothing(self) -> None:
        self.acquirer.status = 402
        app = make_app(acquirer_url=self.acquirer.url, mailer_url=self.mailer.url)
        self.assertEqual(self.pay(app, self.order(app, email="ann@example.com")).status, 402)
        self.assertEqual(self.mailer.requests, [])

    def test_email_must_be_a_string(self) -> None:
        app = make_app(acquirer_url=self.acquirer.url, mailer_url=self.mailer.url)
        response = call(app, "POST", "/orders", {"customer_id": "c-1", "amount": "1.00", "currency": "RUB", "email": 5})
        self.assertEqual(response.status, 400)

import unittest

from _bench.support import FakeService, call, create_order, make_app


class OrderDetailsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acquirer = FakeService(200, {"payment_id": "pay-1"})
        self.addCleanup(self.acquirer.close)
        self.app = make_app(acquirer_url=self.acquirer.url)
        self.order_id = create_order(self.app)

    def patch(self, body: dict, order_id: str | None = None):
        return call(self.app, "PATCH", f"/orders/{order_id or self.order_id}", body)

    def details(self) -> tuple:
        body = call(self.app, "GET", f"/orders/{self.order_id}").body
        return body["customer_note"], body["gift_wrap"], body["delivery_window"]

    def test_defaults(self) -> None:
        self.assertEqual(self.details(), (None, False, None))

    def test_all_fields_are_saved(self) -> None:
        response = self.patch({"customer_note": "Ring twice", "gift_wrap": True, "delivery_window": "evening"})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["delivery_window"], "evening")
        self.assertEqual(self.details(), ("Ring twice", True, "evening"))

    def test_missing_fields_keep_their_values(self) -> None:
        self.patch({"customer_note": "Ring twice", "delivery_window": "morning"})
        self.patch({"gift_wrap": True})
        self.assertEqual(self.details(), ("Ring twice", True, "morning"))

    def test_gift_wrap_can_be_switched_off(self) -> None:
        self.patch({"gift_wrap": True})
        self.patch({"gift_wrap": False})
        self.assertEqual(self.details()[1], False)

    def test_note_of_200_characters_is_accepted(self) -> None:
        self.assertEqual(self.patch({"customer_note": "x" * 200}).status, 200)

    def test_invalid_input_is_422_and_changes_nothing(self) -> None:
        self.patch({"customer_note": "keep"})
        for body in (
            {"customer_note": "x" * 201},
            {"customer_note": 5},
            {"gift_wrap": "yes"},
            {"delivery_window": "night"},
            {"delivery_window": None},
            {"color": "red"},
            {"customer_note": "new", "color": "red"},
            {"customer_note": "new", "gift_wrap": "yes"},
        ):
            with self.subTest(body=body):
                response = self.patch(body)
                self.assertEqual(response.status, 422)
                self.assertIn("error", response.body)
        self.assertEqual(self.details(), ("keep", False, None))

    def test_paid_order_cannot_be_changed(self) -> None:
        call(self.app, "POST", f"/orders/{self.order_id}/pay", {"card_token": "tok"})
        self.assertEqual(self.patch({"gift_wrap": True}).status, 409)
        self.assertEqual(self.details()[1], False)

    def test_unknown_order_is_404(self) -> None:
        self.assertEqual(self.patch({"gift_wrap": True}, order_id="missing").status, 404)

    def test_paid_order_json_includes_details(self) -> None:
        self.patch({"customer_note": "Ring twice"})
        response = call(self.app, "POST", f"/orders/{self.order_id}/pay", {"card_token": "tok"})
        self.assertEqual(response.body["customer_note"], "Ring twice")

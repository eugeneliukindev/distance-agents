import json
import threading
import unittest
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from shop.acquirer import AcquirerClient
from shop.api_client import JsonApiClient
from shop.checkout import Checkout
from shop.db import connect
from shop.errors import OrderNotPayable, PaymentDeclined
from shop.money import Money
from shop.order import OrderStatus
from shop.warehouse import WarehouseClient


class FakeAcquirer:
    """Local HTTP server that answers /charges with a fixed status."""

    def __init__(self, status: int) -> None:
        self.charged: list[dict] = []
        acquirer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                acquirer.charged.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                payload = json.dumps({"payment_id": "pay-1"}).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args: object) -> None:
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_port}"
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()


RUB_1000 = Money(Decimal("1000.00"), "RUB")


class CheckoutTest(unittest.TestCase):
    def checkout(self, status: int) -> tuple[Checkout, FakeAcquirer]:
        acquirer = FakeAcquirer(status)
        self.addCleanup(acquirer.close)
        return Checkout(connect(":memory:"), AcquirerClient(acquirer.url), WarehouseClient(JsonApiClient(acquirer.url))), acquirer

    def test_paid_order_is_charged_and_saved_as_paid(self) -> None:
        checkout, acquirer = self.checkout(200)
        order = checkout.create_order("c-1", RUB_1000)

        checkout.pay_by_card(order.id, "tok")

        self.assertEqual(acquirer.charged[0]["amount"], "1000.00")
        self.assertIs(checkout.get_order(order.id).status, OrderStatus.PAID)

    def test_declined_payment_keeps_order_new(self) -> None:
        checkout, _ = self.checkout(402)
        order = checkout.create_order("c-1", RUB_1000)

        with self.assertRaises(PaymentDeclined):
            checkout.pay_by_card(order.id, "tok")
        self.assertIs(checkout.get_order(order.id).status, OrderStatus.NEW)

    def test_order_cannot_be_paid_twice(self) -> None:
        checkout, _ = self.checkout(200)
        order = checkout.create_order("c-1", RUB_1000)
        checkout.pay_by_card(order.id, "tok")

        with self.assertRaises(OrderNotPayable):
            checkout.pay_by_card(order.id, "tok")


if __name__ == "__main__":
    unittest.main()

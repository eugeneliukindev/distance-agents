"""Helpers for hidden tests. They talk to the shop only through build_app and HTTP-like requests,
so they work with any internal design the agent chooses."""

import inspect
import json
import socket
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from shop.main import Config, build_app
from shop.web.http import HttpRequest


class FakeService:
    """Local HTTP server that answers every POST with a scripted response and records requests."""

    def __init__(self, status: int = 200, body: dict | None = None) -> None:
        self.status = status
        self.body = body or {}
        self.requests: list[tuple[str, dict]] = []
        service = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                service.requests.append((self.path, json.loads(raw or b"{}")))
                payload = json.dumps(service.body).encode()
                self.send_response(service.status)
                self.send_header("Content-Type", "application/json")
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


def dead_url() -> str:
    """URL of a port where nothing listens."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return f"http://127.0.0.1:{port}"


def make_app(**urls: str):
    """Builds the app with a fresh database. Config fields ending in _url that are not given point to a dead port."""
    db_path = str(Path(tempfile.mkdtemp()) / "shop.db")
    kwargs = {"db_path": db_path}
    for name in inspect.signature(Config).parameters:
        if name.endswith("_url"):
            kwargs[name] = urls.get(name, dead_url())
    return build_app(Config(**kwargs))


def call(app, method: str, path: str, body: dict | None = None):
    return app.handle(HttpRequest(method, path, body or {}))


def create_order(app, amount: str = "1000.00", currency: str = "RUB") -> str:
    response = call(app, "POST", "/orders", {"customer_id": "c-1", "amount": amount, "currency": currency})
    assert response.status == 201, response
    return response.body["order_id"]

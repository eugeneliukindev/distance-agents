from shop.http_client import HttpResult, NetworkError, post_json


class JsonApiClient:
    """Base class for clients of partner JSON APIs: shared headers, timeout and retries."""

    timeout = 5
    retries = 1

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def headers(self) -> dict[str, str]:
        return {"Accept": "application/json", "User-Agent": "shop/1.0"}

    def post(self, path: str, body: dict, headers: dict[str, str] | None = None) -> HttpResult:
        """POSTs JSON and retries a network failure `retries` times. Still failing -> NetworkError."""
        attempts_left = self.retries + 1
        while True:
            attempts_left -= 1
            try:
                return post_json(
                    self.base_url + path, body, headers={**self.headers(), **(headers or {})}, timeout=self.timeout
                )
            except NetworkError:
                if attempts_left == 0:
                    raise

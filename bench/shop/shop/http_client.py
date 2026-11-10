import json
import urllib.error
import urllib.request
from dataclasses import dataclass


class NetworkError(Exception):
    """The request did not reach the server or got no answer in time."""


@dataclass(frozen=True)
class HttpResult:
    status: int
    body: dict | None  # parsed JSON object, None if the body is not a JSON object


def post_json(url: str, body: dict, headers: dict[str, str] | None = None, timeout: float = 5) -> HttpResult:
    """Sends a JSON POST. Any HTTP status is a result; no answer -> NetworkError."""
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return HttpResult(response.status, _json_object(response.read()))
    except urllib.error.HTTPError as error:
        return HttpResult(error.code, _json_object(error.read()))
    except (urllib.error.URLError, OSError) as error:
        raise NetworkError(str(error)) from error


def _json_object(raw: bytes) -> dict | None:
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None

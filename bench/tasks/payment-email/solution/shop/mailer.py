from shop.http_client import NetworkError, post_json


class MailNotSent(Exception):
    """The mail service failed or did not answer."""


class HttpMailer:
    """Adapter to the mail service."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def send_order_paid(self, email: str, order_id: str) -> None:
        """Sends the "order paid" email. Raises MailNotSent."""
        try:
            result = post_json(self._base_url + "/send", {"to": email, "template": "order_paid", "order_id": order_id})
        except NetworkError as error:
            raise MailNotSent(str(error)) from error
        if not 200 <= result.status < 300:
            raise MailNotSent(f"mail service answered {result.status}")

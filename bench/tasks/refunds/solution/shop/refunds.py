from shop.errors import RefundUnavailable
from shop.http_client import NetworkError, post_json
from shop.order import Order


class CardRefund:
    """Refunds a card payment through the acquirer."""

    def __init__(self, acquirer_url: str) -> None:
        self._acquirer_url = acquirer_url

    def refund(self, order: Order) -> None:
        try:
            result = post_json(
                self._acquirer_url + "/refunds",
                {"payment_id": order.payment_id, "amount": str(order.total.amount), "currency": order.total.currency},
            )
        except NetworkError as error:
            raise RefundUnavailable(str(error)) from error
        if result.status != 200:
            raise RefundUnavailable(f"unexpected acquirer response: {result.status}")
        order.mark_refunded()


class CashRefund:
    """Cash cannot be returned automatically: an operator gets a task to return it."""

    def __init__(self, tasks_url: str) -> None:
        self._tasks_url = tasks_url

    def refund(self, order: Order) -> None:
        try:
            result = post_json(
                self._tasks_url + "/tasks",
                {
                    "type": "cash_refund",
                    "order_id": order.id,
                    "amount": str(order.total.amount),
                    "currency": order.total.currency,
                },
            )
        except NetworkError as error:
            raise RefundUnavailable(str(error)) from error
        if result.status != 201:
            raise RefundUnavailable(f"unexpected task service response: {result.status}")
        order.mark_refund_pending()

from shop.http_client import NetworkError, post_json
from shop.money import Money


class FiscalUnavailable(Exception):
    """The tax service did not register the receipt. Retrying later may help."""


class TaxService:
    """Adapter to the tax service that registers fiscal receipts."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def register_receipt(self, order_id: str, amount: Money) -> str:
        """Returns the fiscal number. Any failure -> FiscalUnavailable."""
        try:
            result = post_json(
                self._base_url + "/receipts",
                {"order_id": order_id, "amount": str(amount.amount), "currency": amount.currency},
            )
        except NetworkError as error:
            raise FiscalUnavailable(str(error)) from error
        if result.status != 201 or result.body is None or not isinstance(result.body.get("fiscal_number"), str):
            raise FiscalUnavailable(f"unexpected tax service response: {result.status}")
        return result.body["fiscal_number"]

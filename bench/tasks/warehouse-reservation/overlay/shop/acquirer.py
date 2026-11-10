from shop.api_client import JsonApiClient
from shop.errors import PaymentDeclined, PaymentUnavailable
from shop.http_client import NetworkError
from shop.money import Money


class AcquirerClient(JsonApiClient):
    def charge(self, amount: Money, card_token: str, idempotency_key: str) -> str:
        """Charges the whole amount or nothing and returns the payment id.

        Declined by the bank -> PaymentDeclined. Network or service failure -> PaymentUnavailable.
        """
        try:
            result = self.post(
                "/charges",
                {"amount": str(amount.amount), "currency": amount.currency, "card_token": card_token},
                headers={"Idempotency-Key": idempotency_key},
            )
        except NetworkError as error:
            raise PaymentUnavailable(str(error)) from error
        if result.status == 402:
            raise PaymentDeclined(idempotency_key)
        if result.status != 200 or result.body is None or not isinstance(result.body.get("payment_id"), str):
            raise PaymentUnavailable(f"unexpected acquirer response: {result.status}")
        return result.body["payment_id"]

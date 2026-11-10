Add gift card payments to `POST /orders/{order_id}/pay`: `"method": "gift_card"` with a field `"gift_card_code"`.

Call `POST {gift_card_url}/redeem` with JSON `{"code": ..., "amount": ..., "currency": ...}` (amount as a string like `"1000.00"`). A 200 answer has JSON `{"payment_id": "..."}`; then the order is `paid` with that payment id. A 409 answer means the balance is too low: respond 402 with `{"error": "gift card balance is too low"}` and keep the order `new`. If the service is unreachable or answers anything else, respond 503. A missing `gift_card_code` is a 400.

Add `gift_card_url` to `Config`. Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

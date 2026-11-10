Add two more payment methods to `POST /orders/{order_id}/pay`, next to the existing card payment.

- `cash`: cash on delivery. Nothing is charged now. The order status becomes `awaiting_cash` and the response is 200.
- `sbp`: the Fast Payment System. Call `POST {sbp_url}/payments` with JSON `{"order_id": ..., "amount": ..., "currency": ...}` (amount as a string like `"1000.00"`). A 200 answer has JSON `{"payment_id": "..."}`; then the order is `paid` with that payment id. If the SBP service is unreachable or answers anything else, respond 503 and keep the order `new`.

The request body gets a field `method`: `"card"`, `"cash"` or `"sbp"`. If `method` is missing, it is `"card"`, so old clients keep working. An unknown method is a 400. Only a `new` order can be paid by any method; otherwise 409.

Add `sbp_url` to `Config`. Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

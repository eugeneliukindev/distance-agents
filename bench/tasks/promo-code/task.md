Support the promo code `WELCOME5` when paying by card.

`POST /orders/{order_id}/pay` accepts an optional `"promo_code"`. With `WELCOME5` the card is charged 5% less than the order total, rounded to cents. Any other non-empty code is a 422 with `{"error": "unknown promo code"}` and nothing is charged. Without a code the full total is charged, as now.

The order JSON gets `"paid_amount"`: the amount actually charged as a string like `"950.00"`, or `null` if the order is not paid. It must survive reloading the order from the database.

Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

Add shipping costs to orders.

Shipping is free for orders of 5000 RUB or more; otherwise it costs 300 RUB.

- The order JSON (`GET /orders/{order_id}`, the create and pay responses) gets `"shipping_cost"` as a string with two decimals (`"300.00"` or `"0.00"`) and `"free_shipping"` (`true` or `false`). `"amount"` stays the order total without shipping.
- `POST /orders/{order_id}/pay` charges the card the order total plus shipping, for example `"1300.00"` for a 1000 RUB order.

Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

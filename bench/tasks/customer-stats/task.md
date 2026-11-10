Support wants a quick summary of a customer's orders.

Add `GET /customers/{customer_id}/stats`:

```json
{"customer_id": "c-7", "orders": 3, "paid": {"RUB": "1950.50", "USD": "10.00"}}
```

`orders` counts all orders of the customer, paid or not. `paid` sums the totals of the paid orders per currency; currencies without paid orders are left out. A customer with no orders gets `{"customer_id": ..., "orders": 0, "paid": {}}`.

Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

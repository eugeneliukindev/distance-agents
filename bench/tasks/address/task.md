Add a delivery address to orders.

- `PUT /orders/{order_id}/address` with JSON `{"zip": "...", "street": "..."}`. `zip` must be exactly 6 digits and `street` must not be empty after trimming spaces; otherwise respond 422 with `{"error": "..."}`. A valid address is saved on the order (it can be changed later) and the response is the order JSON.
- `GET /orders/{order_id}` includes `"address": {"zip": ..., "street": ...}` or `null`.
- `GET /orders/{order_id}/delivery-estimate` returns `{"days": N}`: 2 days if the zip starts with `1`, otherwise 5. If the order has no address, respond 409.

Unknown orders are 404 everywhere. The address must survive reloading the order from the database. Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

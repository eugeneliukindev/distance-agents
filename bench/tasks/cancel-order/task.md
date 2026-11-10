Let customers cancel orders.

Add `POST /orders/{order_id}/cancel`:

- A `new` order becomes `cancelled`; the response is 200 with the order JSON.
- Cancelling an order that is already `cancelled` is fine: respond 200 with the order JSON.
- A `paid` order cannot be cancelled: respond 409 with `{"error": "..."}` and keep it `paid`.
- An unknown order is a 404.

A cancelled order cannot be paid: `POST /orders/{order_id}/pay` answers 409 and charges nothing. The status must survive reloading the order from the database.

Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

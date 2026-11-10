Add stock reservation: `POST /orders/{order_id}/reservation` (no body).

Call the warehouse service `POST {warehouse_url}/reservations` with JSON `{"order_id": "..."}`. Use the same headers, timeout and retries as for the acquirer. A 201 answer has JSON `{"reservation_id": "..."}`; save it on the order and respond 200 with the order JSON. A 409 answer means the goods are out of stock: respond 409 with `{"error": "out of stock"}`. If the warehouse is unreachable or answers anything else, respond 503.

If the order already has a reservation, return it without calling the warehouse again. Only `new` orders can be reserved (409 otherwise); unknown orders are 404. `GET /orders/{order_id}` includes `"reservation_id"` (`null` if none), and it must survive reloading the order from the database.

Add `warehouse_url` to `Config`. Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

We want to know who our customers are, not only their ids.

- `POST /customers` with JSON `{"name": "...", "email": "..."}` registers a customer and responds 201 with `{"customer_id": "...", "name": "...", "email": "..."}`. Both fields are required non-empty strings, otherwise 400.
- `GET /customers/{customer_id}` returns the same JSON, or 404 for an unknown id.
- Customers are stored in the database next to orders, in their own table.
- `POST /orders` keeps working as now. Guest checkout stays allowed: an order may carry a `customer_id` that is not registered. The order JSON gets `"customer_name"`: the registered customer's name, or `null` for a guest.

Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

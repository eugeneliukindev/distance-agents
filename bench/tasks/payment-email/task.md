Send customers an email when their order is paid.

- `POST /orders` accepts an optional `"email"` field. If it is present, it must be a string, otherwise respond 400. The order JSON includes `"email"` (`null` if none), and it must survive reloading the order from the database.
- After a successful card payment of an order that has an email, call `POST {mailer_url}/send` with JSON `{"to": "<email>", "template": "order_paid", "order_id": "<order id>"}`.
- The email is a courtesy: if the mail service is unreachable or answers with an error, the payment still succeeds and the response is the same as without email. Orders without an email and failed payments send nothing.

Add `mailer_url` to `Config`. Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

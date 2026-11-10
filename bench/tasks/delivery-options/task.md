Customers should choose how they get their order when they pay.

`POST /orders/{order_id}/pay` accepts an optional `"delivery"` field:

- `"courier"`: book a courier slot with `POST {courier_url}/slots` and JSON `{"order_id": "..."}`. A 201 answer has JSON `{"slot": "..."}`.
- `"post"`: register a parcel with the postal service, `POST {post_url}/parcels` with JSON `{"order_id": "..."}`. A 201 answer has JSON `{"tracking_number": "..."}`.
- `"pickup"`: the customer collects the order at one of our pickup points `PP-1`, `PP-2` or `PP-3`, given in `"pickup_point"` (default `PP-1`). Nothing is called.

Without `"delivery"` the order is a pickup at `PP-1`, as for old clients. Book the delivery before charging the card: if the courier or postal service is unreachable or answers anything else, respond 503, charge nothing and keep the order `new`. An unknown delivery or pickup point is a 400 and nothing is charged.

The order JSON gets `"delivery_type"` (`"courier"`, `"post"` or `"pickup"`) and `"delivery_reference"` (the slot, the tracking number or the pickup point), both `null` until the order is paid. They must survive reloading the order from the database.

Add `courier_url` and `post_url` to `Config`. Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

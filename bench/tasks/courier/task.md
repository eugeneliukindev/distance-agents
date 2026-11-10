After an order is paid, register a shipment with the courier service.

Call `POST {courier_url}/shipments` with JSON `{"order_id": "..."}`. A 201 answer has JSON `{"tracking_number": "..."}`; save it on the order and set its shipping status to `registered`. If the courier service is unreachable or answers anything else, the payment still succeeds: the order stays `paid`, has no tracking number and its shipping status is `pending`.

`GET /orders/{order_id}` and the pay response include `"shipping_status"` (`null` before payment) and `"tracking_number"` (`null` if there is none). Both must survive reloading the order from the database.

Add `courier_url` to `Config`. Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

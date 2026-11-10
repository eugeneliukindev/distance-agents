Customers want to add details to an order before paying.

Add `PATCH /orders/{order_id}` with a JSON body that contains any subset of these fields:

- `customer_note`: a string of at most 200 characters;
- `gift_wrap`: `true` or `false`;
- `delivery_window`: `"morning"` or `"evening"`.

Fields that are not in the body keep their current values. A value of the wrong type, a note longer than 200 characters, an unknown delivery window or an unknown field is a 422 with `{"error": "..."}`, and nothing is changed. Only a `new` order can be changed; otherwise respond 409. Unknown orders are 404. A successful PATCH responds 200 with the order JSON.

The order JSON (in every response that returns an order) includes `"customer_note"` (`null` by default), `"gift_wrap"` (`false` by default) and `"delivery_window"` (`null` by default). The details must survive reloading the order from the database.

Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

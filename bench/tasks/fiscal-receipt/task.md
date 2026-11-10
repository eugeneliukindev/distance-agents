We have to issue fiscal receipts for card payments.

After an order is paid by card, register a receipt with the tax service: `POST {fiscal_url}/receipts` with JSON `{"order_id": ..., "amount": ..., "currency": ...}` (amount as a string like `"1000.00"`). A 201 answer has JSON `{"fiscal_number": "..."}`; store it on the order.

The tax service is often slow or down. That must never break a payment: if it is unreachable or answers anything else, the payment still succeeds and we will retry the receipt later.

The order JSON gets two fields: `"fiscal_status"` (`null` before payment, `"registered"` once we have a fiscal number, `"retry"` if registering failed) and `"fiscal_number"` (`null` if there is none). Both must survive reloading the order from the database. Declined payments do not produce receipts.

Add `fiscal_url` to `Config`. Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

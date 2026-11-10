Add a revenue report for accounting.

`GET /reports/revenue/{from}/{to}`, where `from` and `to` are dates like `2026-11-01`, both included. It returns the revenue of the orders paid in that period, per currency:

```json
{"from": "2026-11-01", "to": "2026-11-30", "revenue": {"RUB": "1950.50", "USD": "10.00"}}
```

An order counts on the date it was paid (UTC). Currencies with no paid orders in the period are left out, so a period without payments has `"revenue": {}`. An invalid date or `from` after `to` is a 400.

Record when an order is paid: the order JSON gets `"paid_at"` with the payment date (`"2026-11-10"`) or `null`, and it must survive reloading the order from the database.

Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

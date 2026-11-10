Delivery is no longer free: it costs depending on the delivery zone of the customer's city.

- zone 1: 200.00
- zone 2: 350.00
- zone 3 and further: 600.00

The cost is in the order's currency. Customers who are not registered collect their orders themselves and pay no delivery.

Paying by card (`POST /orders/{order_id}/pay`) charges the order total plus the delivery cost, and the pay response includes `"delivery_cost"` as a string like `"350.00"`. The order total itself does not change. If a customer moves to another city, the next payment uses the new zone.

Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

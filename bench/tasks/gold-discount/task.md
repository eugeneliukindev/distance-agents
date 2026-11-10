Give gold customers a discount.

Customers with loyalty level 3 or higher get 5% off when they pay by card: the card is charged 95% of the order total, rounded to cents (a 1000.00 RUB order is charged `"950.00"`). Customers below level 3, and orders whose customer is not registered through `POST /customers`, pay the full total. The level that counts is the customer's level at the moment of payment. `"amount"` in the order JSON stays the full order total.

Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

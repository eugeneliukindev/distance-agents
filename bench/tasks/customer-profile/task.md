Customers should be able to fill in their profile.

`PUT /customers/{customer_id}/profile` takes JSON `{"name": ..., "phone": ..., "birth_date": ...}`. All three fields are required:

- `name`: a string of 1 to 100 characters;
- `phone`: `+7` followed by exactly 10 digits, like `+79161234567`;
- `birth_date`: a real date as `YYYY-MM-DD`, not in the future.

If anything is missing or wrong, respond 422 with `{"error": "..."}` and keep the old profile. A valid request saves the profile (it can be changed later) and responds 200 with the customer JSON. Unknown customers are 404.

`GET /customers/{customer_id}` includes `"profile": {"name": ..., "phone": ..., "birth_date": ...}`, or `null` until it is filled in. The profile must survive reloading the customer from the database.

Keep the existing tests passing and add tests for the new behavior. Run tests with `python3 -m unittest`.

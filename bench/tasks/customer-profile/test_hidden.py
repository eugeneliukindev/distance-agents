import unittest

from _bench.support import call, make_app

VALID = {"name": "Anna Petrova", "phone": "+79161234567", "birth_date": "1990-05-17"}


class CustomerProfileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = make_app()
        response = call(self.app, "POST", "/customers", {"email": "anna@example.com"})
        self.assertEqual(response.status, 201)
        self.customer_id = response.body["customer_id"]

    def put(self, body: dict, customer_id: str | None = None):
        return call(self.app, "PUT", f"/customers/{customer_id or self.customer_id}/profile", body)

    def profile(self):
        return call(self.app, "GET", f"/customers/{self.customer_id}").body["profile"]

    def test_new_customer_has_no_profile(self) -> None:
        self.assertIsNone(self.profile())

    def test_valid_profile_is_saved(self) -> None:
        response = self.put(VALID)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body["profile"], VALID)
        self.assertEqual(self.profile(), VALID)

    def test_profile_can_be_changed(self) -> None:
        self.put(VALID)
        self.put(VALID | {"name": "Anna Ivanova"})
        self.assertEqual(self.profile()["name"], "Anna Ivanova")

    def test_invalid_profile_is_422_and_keeps_the_old_one(self) -> None:
        self.put(VALID)
        invalid = [
            {"phone": VALID["phone"], "birth_date": VALID["birth_date"]},
            VALID | {"name": ""},
            VALID | {"name": "x" * 101},
            VALID | {"name": 42},
            VALID | {"phone": "89161234567"},
            VALID | {"phone": "+7916123456"},
            VALID | {"phone": "+7916123456a"},
            VALID | {"birth_date": "1990-02-30"},
            VALID | {"birth_date": "17.05.1990"},
            VALID | {"birth_date": "2999-01-01"},
            VALID | {"birth_date": None},
        ]
        for body in invalid:
            with self.subTest(body=body):
                response = self.put(body)
                self.assertEqual(response.status, 422)
                self.assertIsInstance(response.body.get("error"), str)
        self.assertEqual(self.profile(), VALID)

    def test_hundred_characters_is_still_a_valid_name(self) -> None:
        self.assertEqual(self.put(VALID | {"name": "x" * 100}).status, 200)

    def test_unknown_customer_is_404(self) -> None:
        self.assertEqual(self.put(VALID, customer_id="nobody").status, 404)

import unittest
from datetime import date

from shop.customers import CustomerBook
from shop.db import connect
from shop.profile import InvalidProfile, Profile

TODAY = date(2026, 11, 10)


class ProfileTest(unittest.TestCase):
    def test_valid_profile_is_saved(self) -> None:
        book = CustomerBook(connect(":memory:"))
        customer = book.register("anna@example.com")
        profile = Profile("Anna", "+79161234567", date(1990, 5, 17))
        self.assertEqual(book.save_profile(customer.id, profile, TODAY).profile, profile)
        self.assertEqual(book.get(customer.id).profile, profile)

    def test_invalid_values_are_rejected(self) -> None:
        for name, phone in (("", "+79161234567"), ("x" * 101, "+79161234567"), ("Anna", "89161234567")):
            with self.subTest(name=name, phone=phone), self.assertRaises(InvalidProfile):
                Profile(name, phone, date(1990, 5, 17))

    def test_birth_date_in_the_future_is_rejected(self) -> None:
        book = CustomerBook(connect(":memory:"))
        customer = book.register("anna@example.com")
        with self.assertRaises(InvalidProfile):
            book.save_profile(customer.id, Profile("Anna", "+79161234567", date(2030, 1, 1)), TODAY)


if __name__ == "__main__":
    unittest.main()

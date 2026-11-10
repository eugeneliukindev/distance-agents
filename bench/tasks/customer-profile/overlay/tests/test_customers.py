import unittest

from shop.customers import CustomerBook
from shop.db import connect
from shop.errors import CustomerNotFound


class CustomerBookTest(unittest.TestCase):
    def test_registered_customer_can_be_read_back(self) -> None:
        book = CustomerBook(connect(":memory:"))
        customer = book.register("anna@example.com")
        self.assertEqual(book.get(customer.id).email, "anna@example.com")

    def test_unknown_customer_raises(self) -> None:
        with self.assertRaises(CustomerNotFound):
            CustomerBook(connect(":memory:")).get("nobody")


if __name__ == "__main__":
    unittest.main()

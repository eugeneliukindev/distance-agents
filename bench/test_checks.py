"""Self-check: the static checks flag new violations and ignore the ones already in the starter.

    python3 -m unittest discover -s bench -p "test_checks.py"
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from checks import run_checks

STARTER = Path(__file__).resolve().parent / "shop"
VARIANTS = {"card", "cash", "sbp"}

VIOLATIONS = '''

import json
from typing import Protocol


class Discounts(Protocol):
    def apply(self, total): ...


class OnlyDiscounts:
    def apply(self, total):
        return total


class Checkout(Checkout):
    def pay_by_sbp(self, method: str, payload: dict):
        if self._sbp is None:
            return None
        if method == "sbp":
            try:
                result = post_json(self._sbp_url + "/payments", {})
            except NetworkError:
                return None
            if result.status == 201:
                return payload["zip"]
'''


def copy_starter() -> Path:
    work = Path(tempfile.mkdtemp())
    shutil.copytree(STARTER, work, dirs_exist_ok=True)
    return work


class ChecksTest(unittest.TestCase):
    def test_starter_has_no_new_findings(self) -> None:
        results = run_checks(STARTER, STARTER, VARIANTS, {"/payments"})
        self.assertEqual({k: v for k, v in results.items() if not k.startswith("_") and v}, {})

    def test_new_violations_are_found(self) -> None:
        work = copy_starter()
        with (work / "shop/checkout.py").open("a") as checkout:
            checkout.write(VIOLATIONS)

        results = run_checks(work, STARTER, VARIANTS, {"/payments"})

        for check in ("I1_infra_imports", "markers", "T1_raw_payload", "T2_foreign_errors",
                      "I2_single_impl_interfaces", "optional_dependencies",
                      "A1_variant_branches", "A1_variant_api"):
            with self.subTest(check=check):
                self.assertTrue(results[check], check)

    def test_value_object_attribute_names_are_not_raw_keys(self) -> None:
        work = copy_starter()
        (work / "shop/address.py").write_text(
            "class Address:\n    def __init__(self, street):\n        object.__setattr__(self, 'street', street.strip())\n"
        )
        with (work / "shop/order.py").open("a") as order:
            order.write("\nfrom shop.address import Address\n")

        self.assertEqual(run_checks(work, STARTER, VARIANTS, {"street"})["markers"], [])

    def test_adapters_imported_by_business_logic_are_not_business_logic(self) -> None:
        work = copy_starter()
        (work / "shop/courier.py").write_text(
            "from shop.http_client import post_json\n\n\nclass Courier:\n"
            "    def register(self, order_id):\n        return post_json('/shipments', {})\n"
        )
        with (work / "shop/checkout.py").open("a") as checkout:
            checkout.write("\nfrom shop.courier import Courier\n")

        self.assertEqual(run_checks(work, STARTER, VARIANTS, {"/shipments"})["markers"], [])

    def test_branching_in_handlers_is_allowed(self) -> None:
        work = copy_starter()
        with (work / "shop/web/app.py").open("a") as handlers:
            handlers.write('\n\ndef choose(method):\n    return {"card": 1, "cash": 2}[method] if method != "sbp" else 3\n')

        self.assertEqual(run_checks(work, STARTER, VARIANTS)["A1_variant_branches"], [])


if __name__ == "__main__":
    unittest.main()

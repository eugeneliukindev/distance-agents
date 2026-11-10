"""Self-check: the static checks flag known violations and stay quiet on the starter.

    python3 -m unittest bench/test_checks.py
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from checks import run_checks

STARTER = Path(__file__).resolve().parent / "shop"

VIOLATING_CHECKOUT = '''
import json
from typing import Protocol
from shop.infra.http import HttpClient, NetworkError


class Discounts(Protocol):
    def apply(self, total): ...


class OnlyDiscounts:
    def apply(self, total):
        return total


class Checkout:
    def pay(self, method: str, payload: dict):
        if method == "sbp":
            try:
                result = HttpClient("x").post("/payments", {})
            except NetworkError:
                return None
            if result.status == 200:
                return payload["zip"]
'''


class ChecksTest(unittest.TestCase):
    def test_starter_is_clean(self) -> None:
        results = run_checks(STARTER, STARTER, {"card", "cash", "sbp"})
        self.assertEqual({k: v for k, v in results.items() if not k.startswith("_") and v}, {})

    def test_violations_are_found(self) -> None:
        work = Path(tempfile.mkdtemp())
        shutil.copytree(STARTER, work, dirs_exist_ok=True)
        (work / "shop/orders/checkout.py").write_text(VIOLATING_CHECKOUT)

        results = run_checks(work, STARTER, {"card", "cash", "sbp"})

        for check in ("I1_infra_imports", "T1_raw_payload", "T2_foreign_errors",
                      "I2_single_impl_interfaces", "A1_variant_branches"):
            with self.subTest(check=check):
                self.assertTrue(results[check], check)

    def test_branching_in_handlers_is_allowed(self) -> None:
        work = Path(tempfile.mkdtemp())
        shutil.copytree(STARTER, work, dirs_exist_ok=True)
        with (work / "shop/web/app.py").open("a") as handlers:
            handlers.write('\n\ndef choose(method):\n    return {"card": 1, "cash": 2}[method] if method != "sbp" else 3\n')

        self.assertEqual(run_checks(work, STARTER, {"card", "cash", "sbp"})["A1_variant_branches"], [])


if __name__ == "__main__":
    unittest.main()

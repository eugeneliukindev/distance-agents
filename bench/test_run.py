"""Self-check for the ablation conditions.

    python3 -m unittest discover -s bench -p "test_run.py"
"""

import re
import unittest

import run


class AblationTest(unittest.TestCase):
    def test_minus_letter_drops_exactly_that_letters_rules(self) -> None:
        full = run.RULES.read_text()
        for letter in run.LETTERS:
            with self.subTest(letter=letter):
                ablated = run.rules_file(f"minus-{letter}").read_text()
                self.assertEqual(re.findall(rf"\*\*{letter}\d\. ", ablated), [])
                kept = re.findall(r"\*\*([A-Z]\d)\. ", ablated)
                self.assertEqual(kept, [r for r in re.findall(r"\*\*([A-Z]\d)\. ", full) if r[0] != letter])

    def test_unknown_condition_fails(self) -> None:
        for condition in ("minus-X", "minus-", "distance2"):
            with self.subTest(condition=condition), self.assertRaises(ValueError):
                run.rules_file(condition)


if __name__ == "__main__":
    unittest.main()

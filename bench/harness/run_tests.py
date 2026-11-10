"""Runs hidden and regression tests inside a run directory and prints a JSON summary."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # the run directory: `shop` and `_bench`

suite = unittest.TestSuite()
loader = unittest.TestLoader()
for name in ("_bench.test_regression", "_bench.test_hidden"):
    try:
        suite.addTests(loader.loadTestsFromName(name))
    except Exception as error:  # the agent's code may not even import
        print(json.dumps({"import_error": f"{name}: {error!r}"}))
        sys.exit(0)

result = unittest.TestResult()
suite.run(result)
failed = [test.id() for test, _ in result.failures + result.errors]
print(json.dumps({"total": result.testsRun, "failed": failed}))

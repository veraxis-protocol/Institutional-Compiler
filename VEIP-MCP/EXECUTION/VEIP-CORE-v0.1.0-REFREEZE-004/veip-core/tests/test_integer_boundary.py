from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from veip_core.canonical import dumps  # noqa: E402

MAX_SAFE_INTEGER = 9007199254740991  # 2^53 - 1


class IntegerBoundaryTests(unittest.TestCase):
    def test_boundary_values_accepted(self) -> None:
        self.assertEqual(str(MAX_SAFE_INTEGER), dumps(MAX_SAFE_INTEGER))
        self.assertEqual(str(-MAX_SAFE_INTEGER), dumps(-MAX_SAFE_INTEGER))
        self.assertEqual("0", dumps(0))

    def test_two_pow_53_rejected_despite_exact_binary64(self) -> None:
        value = 2**53  # = 9007199254740992 — exactly representable in float64 but outside safe domain
        with self.assertRaises(ValueError):
            dumps(value)
        with self.assertRaises(ValueError):
            dumps(-value)

    def test_arbitrary_precision_rejected(self) -> None:
        for value in (2**68, -(2**68), 10**20, MAX_SAFE_INTEGER + 1, -(MAX_SAFE_INTEGER + 1)):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    dumps(value)

    def test_rejection_does_not_silently_truncate(self) -> None:
        large = MAX_SAFE_INTEGER + 1
        try:
            result = dumps(large)
            self.fail(f"Expected ValueError but got: {result}")
        except ValueError:
            pass


if __name__ == "__main__":
    unittest.main()

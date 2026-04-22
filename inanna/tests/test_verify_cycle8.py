from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

import verify_cycle8


class VerifyCycle8Tests(unittest.TestCase):
    def run_check_silently(self, fn) -> bool:
        with redirect_stdout(io.StringIO()):
            return verify_cycle8.check("test", fn, group="A")

    def test_verify_cycle8_module_imports(self) -> None:
        self.assertTrue(hasattr(verify_cycle8, "CYCLE8_CHECKS"))

    def test_check_returns_true_on_true(self) -> None:
        self.assertTrue(self.run_check_silently(lambda: True))

    def test_check_returns_true_on_pass_string(self) -> None:
        self.assertTrue(self.run_check_silently(lambda: "pass"))

    def test_check_returns_true_on_skip_string(self) -> None:
        self.assertTrue(self.run_check_silently(lambda: "skip"))

    def test_check_returns_false_on_false(self) -> None:
        self.assertFalse(self.run_check_silently(lambda: False))

    def test_check_returns_false_on_error_reason_string(self) -> None:
        self.assertFalse(self.run_check_silently(lambda: "error reason"))

    def test_check_returns_false_on_exception(self) -> None:
        def boom():
            raise RuntimeError("boom")

        self.assertFalse(self.run_check_silently(boom))

    def test_cycle8_checks_has_exactly_twenty_five_entries(self) -> None:
        self.assertEqual(25, len(verify_cycle8.CYCLE8_CHECKS))

    def test_cycle8_checks_cover_groups_a_through_e(self) -> None:
        groups = [check.group for check in verify_cycle8.CYCLE8_CHECKS]
        self.assertEqual(["A", "B", "C", "D", "E"], sorted(set(groups)))
        self.assertEqual(5, groups.count("A"))
        self.assertEqual(5, groups.count("B"))
        self.assertEqual(5, groups.count("C"))
        self.assertEqual(5, groups.count("D"))
        self.assertEqual(5, groups.count("E"))

    def test_write_proof_document_is_callable(self) -> None:
        self.assertTrue(callable(verify_cycle8.write_proof_document))


if __name__ == "__main__":
    unittest.main()

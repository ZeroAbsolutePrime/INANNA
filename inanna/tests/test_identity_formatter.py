"""Tests for IdentityFormatter — Phase 6.6."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.profile import IdentityFormatter, ProfileManager


class TestIdentityFormatter(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.pm = ProfileManager(Path(self.tmp) / "profiles")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fmt(self) -> IdentityFormatter:
        return IdentityFormatter(self.pm)

    def test_address_returns_preferred_name(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.pm.update_field("u1", "preferred_name", "Zohar")
        self.assertEqual(self._fmt().address("u1", "fallback"), "Zohar")

    def test_address_returns_fallback_when_not_set(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.assertEqual(self._fmt().address("u1", "fallback"), "fallback")

    def test_subject_she(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.pm.update_field("u1", "pronouns", "she/her")
        self.assertEqual(self._fmt().subject("u1"), "she")

    def test_subject_he(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.pm.update_field("u1", "pronouns", "he/him")
        self.assertEqual(self._fmt().subject("u1"), "he")

    def test_subject_they(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.pm.update_field("u1", "pronouns", "they/them")
        self.assertEqual(self._fmt().subject("u1"), "they")

    def test_subject_defaults_to_they_for_unknown(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.pm.update_field("u1", "pronouns", "unknown/xyz")
        self.assertEqual(self._fmt().subject("u1"), "they")

    def test_subject_defaults_to_they_for_empty(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.assertEqual(self._fmt().subject("u1"), "they")

    def test_object_pronoun_she(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.pm.update_field("u1", "pronouns", "she/her")
        self.assertEqual(self._fmt().object_pronoun("u1"), "her")

    def test_possessive_they(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.pm.update_field("u1", "pronouns", "they/them")
        self.assertEqual(self._fmt().possessive("u1"), "their")

    def test_format_greeting_includes_name(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.pm.update_field("u1", "preferred_name", "Zohar")
        self.assertIn("Zohar", self._fmt().format_greeting("u1", "fallback"))

    def test_format_greeting_fallback_when_no_name(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.assertEqual(self._fmt().format_greeting("u1", ""), "Welcome back.")

    def test_format_time_returns_string(self) -> None:
        self.pm.ensure_profile_exists("u1")
        result = self._fmt().format_time("2026-04-20T22:15:00+00:00", "u1")
        self.assertIsInstance(result, str)
        self.assertIn("Apr", result)

    def test_format_time_falls_back_on_invalid_timezone(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.pm.update_field("u1", "timezone", "Invalid/Zone")
        result = self._fmt().format_time("2026-04-20T22:15:00+00:00", "u1")
        self.assertIsInstance(result, str)

    def test_ze_zir_pronouns(self) -> None:
        self.pm.ensure_profile_exists("u1")
        self.pm.update_field("u1", "pronouns", "ze/zir")
        self.assertEqual(self._fmt().subject("u1"), "ze")
        self.assertEqual(self._fmt().object_pronoun("u1"), "zir")


if __name__ == "__main__":
    unittest.main()

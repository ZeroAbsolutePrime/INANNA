from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.profile import ProfileManager, UserProfile
from main import needs_onboarding


class ProfileTests(unittest.TestCase):
    def make_manager(self) -> tuple[TemporaryDirectory, Path, ProfileManager]:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        manager = ProfileManager(root / "profiles")
        return temp_dir, root, manager

    def test_user_profile_can_be_instantiated_with_user_id_only(self) -> None:
        profile = UserProfile(user_id="user_123")

        self.assertEqual(profile.user_id, "user_123")

    def test_user_profile_defaults_are_correct(self) -> None:
        profile = UserProfile(user_id="user_123")

        self.assertEqual(profile.version, "1.0")
        self.assertTrue(profile.created_at)
        self.assertTrue(profile.last_updated)
        self.assertEqual(profile.preferred_name, "")
        self.assertEqual(profile.pronouns, "")
        self.assertEqual(profile.gender, "")
        self.assertEqual(profile.sex, "")
        self.assertEqual(profile.languages, [])
        self.assertEqual(profile.timezone, "")
        self.assertEqual(profile.location_city, "")
        self.assertEqual(profile.location_region, "")
        self.assertEqual(profile.location_country, "")
        self.assertEqual(profile.departments, [])
        self.assertEqual(profile.groups, [])
        self.assertEqual(profile.notification_scope, "realm")
        self.assertEqual(profile.communication_style, "")
        self.assertEqual(profile.preferred_length, "")
        self.assertEqual(profile.formality, "")
        self.assertEqual(profile.observed_patterns, [])
        self.assertEqual(profile.domains, [])
        self.assertEqual(profile.recurring_topics, [])
        self.assertEqual(profile.named_projects, [])
        self.assertEqual(profile.session_trusted_tools, [])
        self.assertEqual(profile.persistent_trusted_tools, [])
        self.assertFalse(profile.onboarding_completed)
        self.assertEqual(profile.onboarding_completed_at, "")
        self.assertEqual(profile.survey_responses, {})
        self.assertEqual(profile.inanna_notes, [])

    def test_ensure_profile_exists_creates_profile_file(self) -> None:
        _, root, manager = self.make_manager()

        profile = manager.ensure_profile_exists("user_123")

        self.assertEqual(profile.user_id, "user_123")
        self.assertTrue((root / "profiles" / "user_123.json").exists())

    def test_load_returns_profile_for_existing_profile(self) -> None:
        _, _, manager = self.make_manager()
        manager.save(UserProfile(user_id="user_123", preferred_name="ZAERA"))

        loaded = manager.load("user_123")

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.preferred_name, "ZAERA")

    def test_load_returns_none_for_missing_profile(self) -> None:
        _, _, manager = self.make_manager()

        self.assertIsNone(manager.load("missing_user"))

    def test_save_writes_json_to_disk(self) -> None:
        _, root, manager = self.make_manager()
        profile = UserProfile(user_id="user_123", preferred_name="ZAERA")

        manager.save(profile)

        profile_path = root / "profiles" / "user_123.json"
        self.assertTrue(profile_path.exists())
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["preferred_name"], "ZAERA")
        self.assertEqual(payload["user_id"], "user_123")

    def test_update_field_updates_string_field(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")

        updated = manager.update_field("user_123", "preferred_name", "ZAERA")
        loaded = manager.load("user_123")

        self.assertTrue(updated)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.preferred_name, "ZAERA")

    def test_update_field_updates_list_field(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")

        updated = manager.update_field("user_123", "departments", ["Research", "Operations"])
        loaded = manager.load("user_123")

        self.assertTrue(updated)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.departments, ["Research", "Operations"])

    def test_update_field_rejects_unknown_field(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")

        self.assertFalse(manager.update_field("user_123", "unknown_field", "value"))

    def test_delete_removes_profile_file(self) -> None:
        _, root, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")

        deleted = manager.delete("user_123")

        self.assertTrue(deleted)
        self.assertFalse((root / "profiles" / "user_123.json").exists())

    def test_list_profiles_returns_all_profiles(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")
        manager.ensure_profile_exists("user_456")

        profiles = manager.list_profiles()

        self.assertEqual([profile.user_id for profile in profiles], ["user_123", "user_456"])

    def test_display_name_for_returns_preferred_name_if_set(self) -> None:
        _, _, manager = self.make_manager()
        manager.save(UserProfile(user_id="user_123", preferred_name="ZAERA"))

        self.assertEqual(manager.display_name_for("user_123", fallback="Guardian"), "ZAERA")

    def test_display_name_for_returns_fallback_if_not_set(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")

        self.assertEqual(manager.display_name_for("user_123", fallback="Guardian"), "Guardian")

    def test_pronouns_for_returns_pronouns_if_set(self) -> None:
        _, _, manager = self.make_manager()
        manager.save(UserProfile(user_id="user_123", pronouns="she/her"))

        self.assertEqual(manager.pronouns_for("user_123"), "she/her")

    def test_pronouns_for_returns_empty_string_if_not_set(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")

        self.assertEqual(manager.pronouns_for("user_123"), "")

    def test_profile_json_is_valid_after_save_load_round_trip(self) -> None:
        _, root, manager = self.make_manager()
        original = UserProfile(
            user_id="user_123",
            preferred_name="ZAERA",
            pronouns="she/her",
            departments=["Operations"],
            survey_responses={"timezone": "Europe/Madrid"},
            inanna_notes=["Prefers direct answers."],
        )

        manager.save(original)
        payload = json.loads((root / "profiles" / "user_123.json").read_text(encoding="utf-8"))
        loaded = manager.load("user_123")

        self.assertEqual(payload["preferred_name"], "ZAERA")
        self.assertEqual(payload["survey_responses"], {"timezone": "Europe/Madrid"})
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.preferred_name, "ZAERA")
        self.assertEqual(loaded.pronouns, "she/her")
        self.assertEqual(loaded.departments, ["Operations"])
        self.assertEqual(loaded.inanna_notes, ["Prefers direct answers."])

    def test_needs_onboarding_returns_true_for_incomplete_profile(self) -> None:
        profile = UserProfile(user_id="user_123", onboarding_completed=False)

        self.assertTrue(needs_onboarding(profile))

    def test_needs_onboarding_returns_false_for_completed_profile(self) -> None:
        profile = UserProfile(user_id="user_123", onboarding_completed=True)

        self.assertFalse(needs_onboarding(profile))

    def test_needs_onboarding_returns_false_for_none(self) -> None:
        self.assertFalse(needs_onboarding(None))


if __name__ == "__main__":
    unittest.main()

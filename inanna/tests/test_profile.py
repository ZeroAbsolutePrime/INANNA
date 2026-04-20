from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.profile import CommunicationObserver, NotificationStore, ProfileManager, UserProfile
from main import (
    PROFILE_PROTECTED_CLEAR_FIELDS,
    assign_profile_membership,
    clear_communication_observations,
    coerce_profile_field_value,
    deliver_pending_notifications,
    format_profile_output,
    needs_onboarding,
    parse_profile_clear_command,
    parse_profile_edit_command,
    unassign_profile_membership,
)


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

    def test_format_profile_output_formats_complete_profile(self) -> None:
        profile = UserProfile(
            user_id="user_123",
            preferred_name="ZAERA",
            pronouns="she/her",
            languages=["es", "en", "pt"],
            location_city="Barcelona",
            location_region="Catalonia",
            location_country="Spain",
            communication_style="Direct",
            preferred_length="medium",
            formality="Warm",
            observed_patterns=["Concise"],
            domains=["Systems"],
            recurring_topics=["Architecture"],
            named_projects=["INANNA"],
            session_trusted_tools=["web_search"],
            persistent_trusted_tools=["resolve_host"],
            onboarding_completed=True,
            onboarding_completed_at="2026-04-19T22:15:00+00:00",
        )

        rendered = format_profile_output(profile, "Zohar")

        self.assertIn("Your profile", rendered)
        self.assertIn("Name         Zohar", rendered)
        self.assertIn("Preferred    ZAERA", rendered)
        self.assertIn("Languages    es, en, pt", rendered)
        self.assertIn("Location     Barcelona, Catalonia, Spain", rendered)
        self.assertIn("Length       medium", rendered)
        self.assertIn("Onboarding   completed Apr 19 22:15", rendered)

    def test_format_profile_output_shows_empty_marker_for_blank_fields(self) -> None:
        rendered = format_profile_output(UserProfile(user_id="user_123"), "Alice")

        self.assertIn("Preferred    —", rendered)
        self.assertIn("Languages    —", rendered)
        self.assertIn("Location     —", rendered)
        self.assertIn("Length       —", rendered)
        self.assertIn("Departments  —", rendered)

    def test_parse_profile_edit_command_extracts_field_and_value(self) -> None:
        self.assertEqual(
            parse_profile_edit_command("my-profile edit preferred_name Zohar"),
            ("preferred_name", "Zohar"),
        )

    def test_parse_profile_edit_command_returns_none_for_missing_value(self) -> None:
        self.assertIsNone(parse_profile_edit_command("my-profile edit preferred_name"))

    def test_coerce_profile_field_value_splits_list_fields_on_commas(self) -> None:
        self.assertEqual(
            coerce_profile_field_value("languages", "en, es, pt"),
            ["en", "es", "pt"],
        )

    def test_parse_profile_clear_command_extracts_field(self) -> None:
        self.assertEqual(
            parse_profile_clear_command("my-profile clear pronouns"),
            "pronouns",
        )

    def test_protected_clear_fields_include_phase_critical_fields(self) -> None:
        self.assertTrue(
            {"user_id", "version", "created_at", "onboarding_completed"}.issubset(
                PROFILE_PROTECTED_CLEAR_FIELDS
            )
        )

    def test_communication_observer_instantiates_with_profile_manager(self) -> None:
        _, _, manager = self.make_manager()

        observer = CommunicationObserver(manager)

        self.assertIs(observer.profile_manager, manager)

    def test_observe_session_sets_short_length_for_short_messages(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")
        observer = CommunicationObserver(manager)

        observer.observe_session("user_123", ["hey", "ok thanks"], ["governance"])

        self.assertEqual(manager.load("user_123").preferred_length, "short")

    def test_observe_session_sets_long_length_for_long_messages(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")
        observer = CommunicationObserver(manager)
        long_message = " ".join(["careful"] * 80)

        observer.observe_session("user_123", [long_message], ["architecture"])

        self.assertEqual(manager.load("user_123").preferred_length, "long")

    def test_observe_session_sets_formality_to_formal(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")
        observer = CommunicationObserver(manager)

        observer.observe_session(
            "user_123",
            ["Please review this request. Thank you, I would appreciate it."],
            [],
        )

        self.assertEqual(manager.load("user_123").formality, "formal")

    def test_observe_session_sets_formality_to_casual(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")
        observer = CommunicationObserver(manager)

        observer.observe_session(
            "user_123",
            ["hey yeah ok cool thanks lol"],
            [],
        )

        self.assertEqual(manager.load("user_123").formality, "casual")

    def test_observe_session_updates_recurring_topics(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")
        observer = CommunicationObserver(manager)

        observer.observe_session("user_123", ["hello there"], ["security", "networks"])

        self.assertEqual(manager.load("user_123").recurring_topics, ["security", "networks"])

    def test_observe_session_deduplicates_topics(self) -> None:
        _, _, manager = self.make_manager()
        manager.save(UserProfile(user_id="user_123", recurring_topics=["security"]))
        observer = CommunicationObserver(manager)

        observer.observe_session("user_123", ["hello there"], ["security", "governance"])

        self.assertEqual(
            manager.load("user_123").recurring_topics,
            ["security", "governance"],
        )

    def test_observe_session_caps_topics_at_twenty(self) -> None:
        _, _, manager = self.make_manager()
        existing = [f"topic{i}" for i in range(10)]
        manager.save(UserProfile(user_id="user_123", recurring_topics=existing))
        observer = CommunicationObserver(manager)
        new_topics = [f"new{i}" for i in range(15)]

        observer.observe_session("user_123", ["hello there"], new_topics)

        recurring_topics = manager.load("user_123").recurring_topics
        self.assertEqual(len(recurring_topics), 20)
        self.assertEqual(recurring_topics[0], "topic5")
        self.assertEqual(recurring_topics[-1], "new14")

    def test_observe_session_with_empty_messages_makes_no_updates(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")
        observer = CommunicationObserver(manager)

        observer.observe_session("user_123", [], ["security"])

        profile = manager.load("user_123")
        self.assertEqual(profile.preferred_length, "")
        self.assertEqual(profile.formality, "")
        self.assertEqual(profile.recurring_topics, [])

    def test_observe_session_with_unknown_user_id_makes_no_changes(self) -> None:
        _, root, manager = self.make_manager()
        observer = CommunicationObserver(manager)

        observer.observe_session("missing_user", ["hello"], ["security"])

        self.assertFalse((root / "profiles" / "missing_user.json").exists())

    def test_clear_communication_observations_resets_all_fields(self) -> None:
        _, _, manager = self.make_manager()
        manager.save(
            UserProfile(
                user_id="user_123",
                communication_style="direct",
                preferred_length="short",
                formality="casual",
                observed_patterns=["brief"],
            )
        )

        cleared = clear_communication_observations(manager, "user_123")
        profile = manager.load("user_123")

        self.assertTrue(cleared)
        self.assertEqual(profile.communication_style, "")
        self.assertEqual(profile.preferred_length, "")
        self.assertEqual(profile.formality, "")
        self.assertEqual(profile.observed_patterns, [])

    def test_notification_store_add_persists_notification(self) -> None:
        _, root, _ = self.make_manager()
        store = NotificationStore(root / "notifications")

        store.add(
            "user_123",
            {
                "notification_id": "notif-1",
                "from": "guardian",
                "department": "engineering",
                "message": "Standup in 10 minutes.",
                "created_at": "2026-04-20T10:00:00+00:00",
                "delivered": False,
            },
        )

        payload = json.loads((root / "notifications" / "user_123.json").read_text(encoding="utf-8"))
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["message"], "Standup in 10 minutes.")

    def test_notification_store_load_pending_returns_only_undelivered_records(self) -> None:
        _, root, _ = self.make_manager()
        store = NotificationStore(root / "notifications")
        (root / "notifications" / "user_123.json").write_text(
            json.dumps(
                [
                    {
                        "notification_id": "notif-1",
                        "from": "guardian",
                        "department": "engineering",
                        "message": "Pending.",
                        "created_at": "2026-04-20T10:00:00+00:00",
                        "delivered": False,
                    },
                    {
                        "notification_id": "notif-2",
                        "from": "guardian",
                        "department": "engineering",
                        "message": "Delivered.",
                        "created_at": "2026-04-20T10:05:00+00:00",
                        "delivered": True,
                    },
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

        pending = store.load_pending("user_123")

        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["notification_id"], "notif-1")

    def test_notification_store_mark_delivered_marks_target_record(self) -> None:
        _, root, _ = self.make_manager()
        store = NotificationStore(root / "notifications")
        store.add(
            "user_123",
            {
                "notification_id": "notif-1",
                "from": "guardian",
                "department": "engineering",
                "message": "Ping.",
                "created_at": "2026-04-20T10:00:00+00:00",
                "delivered": False,
            },
        )

        marked = store.mark_delivered("user_123", "notif-1")
        payload = json.loads((root / "notifications" / "user_123.json").read_text(encoding="utf-8"))

        self.assertTrue(marked)
        self.assertTrue(payload[0]["delivered"])

    def test_notification_store_clear_delivered_removes_delivered_records(self) -> None:
        _, root, _ = self.make_manager()
        store = NotificationStore(root / "notifications")
        (root / "notifications" / "user_123.json").write_text(
            json.dumps(
                [
                    {
                        "notification_id": "notif-1",
                        "from": "guardian",
                        "department": "engineering",
                        "message": "Delivered.",
                        "created_at": "2026-04-20T10:00:00+00:00",
                        "delivered": True,
                    },
                    {
                        "notification_id": "notif-2",
                        "from": "guardian",
                        "department": "engineering",
                        "message": "Pending.",
                        "created_at": "2026-04-20T10:05:00+00:00",
                        "delivered": False,
                    },
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

        store.clear_delivered("user_123")
        payload = json.loads((root / "notifications" / "user_123.json").read_text(encoding="utf-8"))

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["notification_id"], "notif-2")

    def test_assign_profile_membership_updates_department(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")

        updated, department = assign_profile_membership(
            manager,
            "user_123",
            "departments",
            "Engineering",
        )

        self.assertTrue(updated)
        self.assertEqual(department, "engineering")
        self.assertEqual(manager.load("user_123").departments, ["engineering"])

    def test_assign_profile_membership_updates_group(self) -> None:
        _, _, manager = self.make_manager()
        manager.ensure_profile_exists("user_123")

        updated, group = assign_profile_membership(
            manager,
            "user_123",
            "groups",
            "Core Team",
        )

        self.assertTrue(updated)
        self.assertEqual(group, "core team")
        self.assertEqual(manager.load("user_123").groups, ["core team"])

    def test_duplicate_department_assignment_is_idempotent(self) -> None:
        _, _, manager = self.make_manager()
        manager.save(UserProfile(user_id="user_123", departments=["engineering"]))

        assign_profile_membership(manager, "user_123", "departments", "Engineering")
        assign_profile_membership(manager, "user_123", "departments", "engineering")

        self.assertEqual(manager.load("user_123").departments, ["engineering"])

    def test_unassign_missing_department_returns_gracefully(self) -> None:
        _, _, manager = self.make_manager()
        manager.save(UserProfile(user_id="user_123", departments=["engineering"]))

        updated, removed, department = unassign_profile_membership(
            manager,
            "user_123",
            "departments",
            "research",
        )

        self.assertTrue(updated)
        self.assertFalse(removed)
        self.assertEqual(department, "research")
        self.assertEqual(manager.load("user_123").departments, ["engineering"])

    def test_deliver_pending_notifications_marks_and_clears_records(self) -> None:
        _, root, _ = self.make_manager()
        store = NotificationStore(root / "notifications")
        store.add(
            "user_123",
            {
                "notification_id": "notif-1",
                "from": "guardian",
                "department": "engineering",
                "message": "Standup in 10 minutes.",
                "created_at": "2026-04-20T10:00:00+00:00",
                "delivered": False,
            },
        )

        lines = deliver_pending_notifications(store, "user_123")

        self.assertEqual(
            lines,
            ["\U0001F4E2 [engineering notification] Standup in 10 minutes."],
        )
        self.assertFalse((root / "notifications" / "user_123.json").exists())


if __name__ == "__main__":
    unittest.main()

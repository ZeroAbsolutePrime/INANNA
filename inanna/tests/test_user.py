from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from core.user import (
    UserManager,
    UserRecord,
    can_access_realm,
    check_privilege,
    ensure_guardian_exists,
)


ROLES_PAYLOAD = {
    "roles": {
        "guardian": {
            "description": "Full system access - assigned directly only",
            "privileges": ["all"],
        },
        "operator": {
            "description": "Realm-scoped admin",
            "privileges": [
                "manage_users_in_realm",
                "approve_proposals_in_realm",
                "read_realm_audit_log",
                "invite_users",
            ],
        },
        "user": {
            "description": "Standard interaction",
            "privileges": [
                "converse",
                "approve_own_memory",
                "read_own_log",
                "forget_own_memory",
            ],
        },
    }
}


class UserTests(unittest.TestCase):
    def make_user_manager(self) -> tuple[TemporaryDirectory, Path, UserManager]:
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        roles_path = root / "roles.json"
        roles_path.write_text(json.dumps(ROLES_PAYLOAD, indent=2), encoding="utf-8")
        manager = UserManager(data_root=root, roles_config_path=roles_path)
        return temp_dir, root, manager

    def test_user_record_can_be_instantiated(self) -> None:
        record = UserRecord(
            user_id="user_12345678",
            display_name="INANNA NAMMU",
            role="guardian",
            assigned_realms=["all"],
        )

        self.assertEqual(record.display_name, "INANNA NAMMU")
        self.assertEqual(record.assigned_realms, ["all"])

    def test_create_user_writes_json_file(self) -> None:
        _, root, manager = self.make_user_manager()

        record = manager.create_user(
            display_name="Alice",
            role="user",
            assigned_realms=["default"],
            created_by="system",
        )

        user_path = root / "users" / f"{record.user_id}.json"
        self.assertTrue(user_path.exists())
        payload = json.loads(user_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["display_name"], "Alice")
        self.assertEqual(payload["assigned_realms"], ["default"])

    def test_ensure_guardian_exists_returns_same_guardian_on_second_call(self) -> None:
        _, _, manager = self.make_user_manager()

        first = ensure_guardian_exists(manager)
        second = ensure_guardian_exists(manager)

        self.assertEqual(first.user_id, second.user_id)
        self.assertEqual(len(manager.list_users()), 1)

    def test_can_access_realm_covers_all_assigned_and_unassigned(self) -> None:
        guardian = UserRecord(
            user_id="user_guard",
            display_name="INANNA NAMMU",
            role="guardian",
            assigned_realms=["all"],
        )
        user = UserRecord(
            user_id="user_a",
            display_name="Alice",
            role="user",
            assigned_realms=["default", "work"],
        )

        self.assertTrue(can_access_realm(guardian, "private"))
        self.assertTrue(can_access_realm(user, "work"))
        self.assertFalse(can_access_realm(user, "arcanum"))

    def test_assign_realm_adds_realm_and_rejects_duplicate(self) -> None:
        _, _, manager = self.make_user_manager()
        record = manager.create_user(
            display_name="Alice",
            role="user",
            assigned_realms=["default"],
            created_by="system",
        )

        first = manager.assign_realm(record.user_id, "work")
        refreshed = manager.get_user(record.user_id)
        second = manager.assign_realm(record.user_id, "work")

        self.assertTrue(first)
        assert refreshed is not None
        self.assertEqual(refreshed.assigned_realms, ["default", "work"])
        self.assertFalse(second)

    def test_unassign_realm_removes_realm_and_protects_last_realm(self) -> None:
        _, _, manager = self.make_user_manager()
        record = manager.create_user(
            display_name="Alice",
            role="user",
            assigned_realms=["default", "work"],
            created_by="system",
        )

        first = manager.unassign_realm(record.user_id, "work")
        refreshed = manager.get_user(record.user_id)
        second = manager.unassign_realm(record.user_id, "default")

        self.assertTrue(first)
        assert refreshed is not None
        self.assertEqual(refreshed.assigned_realms, ["default"])
        self.assertFalse(second)

    def test_check_privilege_requires_active_user_and_allows_guardian(self) -> None:
        _, _, manager = self.make_user_manager()
        guardian = ensure_guardian_exists(manager)
        allowed, reason = check_privilege(None, manager, "all")
        guardian_allowed, guardian_reason = check_privilege(guardian, manager, "invite_users")

        self.assertFalse(allowed)
        self.assertIn("No active session", reason)
        self.assertTrue(guardian_allowed)
        self.assertEqual(guardian_reason, "")

    def test_create_invite_creates_invite_record_with_inanna_code(self) -> None:
        _, _, manager = self.make_user_manager()

        invite = manager.create_invite(
            role="user",
            assigned_realms=["default"],
            created_by="user_guardian",
        )

        self.assertTrue(invite.invite_code.startswith("INANNA-"))
        self.assertEqual(invite.role, "user")
        self.assertEqual(invite.assigned_realms, ["default"])
        self.assertEqual(invite.status, "pending")

    def test_get_invite_returns_record_for_valid_code(self) -> None:
        _, _, manager = self.make_user_manager()
        invite = manager.create_invite("user", ["default"], "user_guardian")

        loaded = manager.get_invite(invite.invite_code)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.invite_code, invite.invite_code)

    def test_get_invite_returns_none_for_unknown_code(self) -> None:
        _, _, manager = self.make_user_manager()

        self.assertIsNone(manager.get_invite("INANNA-XXXX-XXXX"))

    def test_accept_invite_creates_user_and_updates_invite_status(self) -> None:
        _, _, manager = self.make_user_manager()
        invite = manager.create_invite("user", ["default"], "user_guardian")

        created = manager.accept_invite(invite.invite_code, "Alice")
        updated = manager.get_invite(invite.invite_code)

        self.assertIsNotNone(created)
        self.assertEqual(created.display_name, "Alice")
        self.assertEqual(created.role, "user")
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "accepted")
        self.assertEqual(updated.accepted_by, created.user_id)

    def test_accept_invite_returns_none_for_expired_invite(self) -> None:
        _, root, manager = self.make_user_manager()
        invite = manager.create_invite("user", ["default"], "user_guardian")
        invite_path = root / "invites" / f"{invite.invite_code}.json"
        payload = json.loads(invite_path.read_text(encoding="utf-8"))
        payload["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        invite_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        created = manager.accept_invite(invite.invite_code, "Alice")
        updated = manager.get_invite(invite.invite_code)

        self.assertIsNone(created)
        self.assertEqual(updated.status, "expired")

    def test_accept_invite_returns_none_for_already_accepted_invite(self) -> None:
        _, _, manager = self.make_user_manager()
        invite = manager.create_invite("user", ["default"], "user_guardian")
        first = manager.accept_invite(invite.invite_code, "Alice")
        second = manager.accept_invite(invite.invite_code, "Bob")

        self.assertIsNotNone(first)
        self.assertIsNone(second)

    def test_list_invites_returns_all_records(self) -> None:
        _, _, manager = self.make_user_manager()
        manager.create_invite("user", ["default"], "user_guardian")
        manager.create_invite("operator", ["work"], "user_guardian")

        invites = manager.list_invites()

        self.assertEqual(len(invites), 2)

    def test_list_invites_filters_by_status(self) -> None:
        _, _, manager = self.make_user_manager()
        pending = manager.create_invite("user", ["default"], "user_guardian")
        accepted = manager.create_invite("user", ["default"], "user_guardian")
        manager.accept_invite(accepted.invite_code, "Alice")

        invites = manager.list_invites(status="pending")

        self.assertEqual(len(invites), 1)
        self.assertEqual(invites[0].invite_code, pending.invite_code)

    def test_expire_old_invites_marks_past_expiry_records(self) -> None:
        _, root, manager = self.make_user_manager()
        invite = manager.create_invite("user", ["default"], "user_guardian")
        invite_path = root / "invites" / f"{invite.invite_code}.json"
        payload = json.loads(invite_path.read_text(encoding="utf-8"))
        payload["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        invite_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        count = manager.expire_old_invites()
        updated = manager.get_invite(invite.invite_code)

        self.assertEqual(count, 1)
        self.assertEqual(updated.status, "expired")


if __name__ == "__main__":
    unittest.main()

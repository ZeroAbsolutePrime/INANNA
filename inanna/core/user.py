from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class UserRecord:
    user_id: str
    display_name: str
    role: str
    assigned_realms: list[str]
    created_at: str = field(default_factory=utc_now)
    created_by: str = "system"
    status: str = "active"


def can_access_realm(user_record: UserRecord | None, realm_name: str) -> bool:
    if user_record is None:
        return False
    assigned = {realm.strip().lower() for realm in user_record.assigned_realms if realm.strip()}
    target = realm_name.strip().lower()
    return "all" in assigned or target in assigned


def check_privilege(
    active_user: UserRecord | None,
    user_manager: "UserManager",
    privilege: str,
) -> tuple[bool, str]:
    if active_user is None:
        return False, "No active session."
    ok = user_manager.has_privilege(active_user.user_id, privilege)
    if ok:
        return True, ""
    return (
        False,
        (
            f"Insufficient privileges. "
            f"{active_user.display_name} ({active_user.role}) does not have: {privilege}"
        ),
    )


def ensure_guardian_exists(user_manager: "UserManager") -> UserRecord:
    for record in user_manager.list_users():
        if record.role == "guardian":
            return record
    return user_manager.create_user(
        display_name="ZAERA",
        role="guardian",
        assigned_realms=["all"],
        created_by="system",
    )


class UserManager:
    def __init__(self, data_root: Path, roles_config_path: Path) -> None:
        self.data_root = data_root
        self.users_dir = data_root / "users"
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.roles_config_path = roles_config_path
        self.roles = self._load_roles()

    def create_user(
        self,
        display_name: str,
        role: str,
        assigned_realms: list[str],
        created_by: str,
    ) -> UserRecord:
        normalized_role = role.strip().lower()
        if normalized_role not in self.roles:
            raise ValueError(f"Unknown role: {role}")
        user_id = self._generate_user_id()
        record = UserRecord(
            user_id=user_id,
            display_name=display_name.strip(),
            role=normalized_role,
            assigned_realms=self._normalize_realms(assigned_realms),
            created_by=created_by,
        )
        self._write_user(record)
        return record

    def get_user(self, user_id: str) -> UserRecord | None:
        path = self._user_path_for(user_id)
        if not path.exists():
            return None
        return self._read_user(path)

    def get_user_by_display_name(self, display_name: str) -> UserRecord | None:
        target = display_name.strip().lower()
        for record in self.list_users():
            if record.display_name.strip().lower() == target:
                return record
        return None

    def list_users(self) -> list[UserRecord]:
        return [self._read_user(path) for path in sorted(self.users_dir.glob("user_*.json"))]

    def list_users_by_realm(self, realm: str) -> list[UserRecord]:
        target = realm.strip().lower()
        return [
            record
            for record in self.list_users()
            if "all" in {value.lower() for value in record.assigned_realms}
            or target in {value.lower() for value in record.assigned_realms}
        ]

    def suspend_user(self, user_id: str) -> bool:
        record = self.get_user(user_id)
        if record is None:
            return False
        record.status = "suspended"
        self._write_user(record)
        return True

    def activate_user(self, user_id: str) -> bool:
        record = self.get_user(user_id)
        if record is None:
            return False
        record.status = "active"
        self._write_user(record)
        return True

    def get_role_privileges(self, role: str) -> list[str]:
        normalized_role = role.strip().lower()
        role_record = self.roles.get(normalized_role, {})
        privileges = role_record.get("privileges", [])
        return [str(privilege) for privilege in privileges]

    def has_privilege(self, user_id: str, privilege: str) -> bool:
        record = self.get_user(user_id)
        if record is None or record.status != "active":
            return False
        privileges = self.get_role_privileges(record.role)
        return "all" in privileges or privilege in privileges

    def assign_realm(self, user_id: str, realm_name: str) -> bool:
        record = self.get_user(user_id)
        if record is None:
            return False
        normalized_realm = realm_name.strip()
        lowered = {value.lower() for value in record.assigned_realms}
        if normalized_realm.lower() in lowered or "all" in lowered:
            return False
        record.assigned_realms.append(normalized_realm)
        self._write_user(record)
        return True

    def unassign_realm(self, user_id: str, realm_name: str) -> bool:
        record = self.get_user(user_id)
        if record is None:
            return False
        lowered = [value.lower() for value in record.assigned_realms]
        if "all" in lowered or len(record.assigned_realms) <= 1:
            return False
        target = realm_name.strip().lower()
        if target not in lowered:
            return False
        record.assigned_realms = [
            value for value in record.assigned_realms if value.strip().lower() != target
        ]
        self._write_user(record)
        return True

    def _generate_user_id(self) -> str:
        while True:
            user_id = f"user_{uuid.uuid4().hex[:8]}"
            if not self._user_path_for(user_id).exists():
                return user_id

    def _normalize_realms(self, assigned_realms: list[str]) -> list[str]:
        cleaned: list[str] = []
        for realm in assigned_realms:
            value = realm.strip()
            if value and value.lower() not in {item.lower() for item in cleaned}:
                cleaned.append(value)
        return cleaned or ["default"]

    def _user_path_for(self, user_id: str) -> Path:
        return self.users_dir / f"{user_id}.json"

    def _write_user(self, record: UserRecord) -> None:
        self._user_path_for(record.user_id).write_text(
            json.dumps(asdict(record), indent=2),
            encoding="utf-8",
        )

    def _read_user(self, path: Path) -> UserRecord:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return UserRecord(**payload)

    def _load_roles(self) -> dict[str, dict]:
        payload = json.loads(self.roles_config_path.read_text(encoding="utf-8"))
        roles = payload.get("roles", {})
        return {str(name).lower(): dict(config) for name, config in roles.items()}

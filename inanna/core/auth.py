from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from dataclasses import dataclass
from pathlib import Path


PBKDF2_ITERATIONS = 260000


def _hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        str(salt).encode("utf-8"),
        iterations=PBKDF2_ITERATIONS,
    )
    return digest.hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(32)
    return f"{salt}:{_hash_password(password, salt)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = str(stored).split(":", 1)
    except ValueError:
        return False
    actual = _hash_password(password, salt)
    return hmac.compare_digest(actual, expected)


@dataclass
class AuthRecord:
    user_id: str
    username: str
    password_hash: str
    role: str


class AuthStore:
    """
    Stores hashed passwords separately from the user/token system.
    File: data/realms/{realm}/auth.json
    """

    def __init__(self, data_dir: Path) -> None:
        self.path = Path(data_dir) / "auth.json"
        self._records: dict[str, AuthRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict):
            return
        loaded: dict[str, AuthRecord] = {}
        for user_id, raw in payload.items():
            if not isinstance(raw, dict):
                continue
            try:
                record = AuthRecord(
                    user_id=str(raw["user_id"]),
                    username=str(raw["username"]),
                    password_hash=str(raw["password_hash"]),
                    role=str(raw["role"]),
                )
            except KeyError:
                continue
            loaded[str(user_id)] = record
        self._records = loaded

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            user_id: {
                "user_id": record.user_id,
                "username": record.username,
                "password_hash": record.password_hash,
                "role": record.role,
            }
            for user_id, record in self._records.items()
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def seed_user(
        self,
        user_id: str,
        username: str,
        password: str,
        role: str,
    ) -> AuthRecord:
        existing = self._records.get(str(user_id))
        if existing is not None:
            return existing
        record = AuthRecord(
            user_id=str(user_id),
            username=str(username),
            password_hash=hash_password(password),
            role=str(role),
        )
        self._records[record.user_id] = record
        self._save()
        return record

    def create_user(
        self,
        username: str,
        password: str,
        role: str,
    ) -> AuthRecord:
        user_id = uuid.uuid4().hex[:8]
        while user_id in self._records:
            user_id = uuid.uuid4().hex[:8]
        return self.seed_user(user_id, username, password, role)

    def authenticate(self, username: str, password: str) -> AuthRecord | None:
        target = self.get_by_username(username)
        if target is None:
            return None
        if verify_password(password, target.password_hash):
            return target
        return None

    def get_by_username(self, username: str) -> AuthRecord | None:
        lowered = str(username or "").strip().lower()
        if not lowered:
            return None
        for record in self._records.values():
            if record.username.strip().lower() == lowered:
                return record
        return None

    def get_by_id(self, user_id: str) -> AuthRecord | None:
        return self._records.get(str(user_id))

    def list_users(self) -> list[AuthRecord]:
        return list(self._records.values())

    def change_password(self, user_id: str, new_password: str) -> bool:
        record = self._records.get(str(user_id))
        if record is None:
            return False
        record.password_hash = hash_password(new_password)
        self._save()
        return True

    def delete_user(self, user_id: str) -> bool:
        normalized = str(user_id)
        if normalized not in self._records:
            return False
        del self._records[normalized]
        self._save()
        return True

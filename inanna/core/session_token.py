from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


SESSION_HOURS = 8


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SessionToken:
    token: str
    user_id: str
    display_name: str
    role: str
    issued_at: str
    expires_at: str
    active: bool = True


class TokenStore:
    def __init__(self) -> None:
        self._tokens: dict[str, SessionToken] = {}

    def issue(self, user_id: str, display_name: str, role: str) -> SessionToken:
        issued_at = datetime.now(timezone.utc)
        record = SessionToken(
            token=str(uuid.uuid4()),
            user_id=user_id,
            display_name=display_name,
            role=role,
            issued_at=issued_at.isoformat(),
            expires_at=(issued_at + timedelta(hours=SESSION_HOURS)).isoformat(),
            active=True,
        )
        self._tokens[record.token] = record
        return record

    def validate(self, token: str) -> SessionToken | None:
        record = self._tokens.get(token)
        if record is None or not record.active:
            return None
        if datetime.fromisoformat(record.expires_at) <= datetime.now(timezone.utc):
            record.active = False
            return None
        return record

    def revoke(self, token: str) -> bool:
        record = self._tokens.get(token)
        if record is None or not record.active:
            return False
        record.active = False
        return True

    def active_tokens(self) -> list[SessionToken]:
        active: list[SessionToken] = []
        for record in self._tokens.values():
            validated = self.validate(record.token)
            if validated is not None:
                active.append(validated)
        return active

    def revoke_all_for_user(self, user_id: str) -> int:
        count = 0
        for record in self._tokens.values():
            if record.user_id == user_id and record.active:
                record.active = False
                count += 1
        return count

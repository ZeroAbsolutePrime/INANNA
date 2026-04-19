from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from core.session_token import SESSION_HOURS, SessionToken, TokenStore


class SessionTokenTests(unittest.TestCase):
    def test_session_token_can_be_instantiated(self) -> None:
        token = SessionToken(
            token="1234",
            user_id="user_abc12345",
            display_name="ZAERA",
            role="guardian",
            issued_at="2026-04-19T12:00:00+00:00",
            expires_at="2026-04-19T20:00:00+00:00",
            active=True,
        )

        self.assertEqual(token.display_name, "ZAERA")
        self.assertTrue(token.active)

    def test_issue_returns_uuid_session_token(self) -> None:
        store = TokenStore()

        token = store.issue("user_abc12345", "ZAERA", "guardian")

        self.assertIsInstance(token, SessionToken)
        self.assertEqual(token.user_id, "user_abc12345")
        self.assertEqual(token.display_name, "ZAERA")
        self.assertEqual(token.role, "guardian")
        self.assertEqual(token.active, True)
        self.assertEqual(
            datetime_delta_hours(token.issued_at, token.expires_at),
            SESSION_HOURS,
        )
        uuid.UUID(token.token)

    def test_validate_returns_token_for_known_active_token(self) -> None:
        store = TokenStore()
        token = store.issue("user_abc12345", "ZAERA", "guardian")

        validated = store.validate(token.token)

        self.assertIsNotNone(validated)
        self.assertEqual(validated.token, token.token)

    def test_validate_returns_none_for_unknown_token(self) -> None:
        self.assertIsNone(TokenStore().validate("missing"))

    def test_validate_returns_none_for_revoked_token(self) -> None:
        store = TokenStore()
        token = store.issue("user_abc12345", "ZAERA", "guardian")
        store.revoke(token.token)

        self.assertIsNone(store.validate(token.token))

    def test_validate_returns_none_for_expired_token(self) -> None:
        with patch("core.session_token.SESSION_HOURS", 0):
            store = TokenStore()
            token = store.issue("user_abc12345", "ZAERA", "guardian")

        self.assertIsNone(store.validate(token.token))
        self.assertFalse(token.active)

    def test_revoke_deactivates_token(self) -> None:
        store = TokenStore()
        token = store.issue("user_abc12345", "ZAERA", "guardian")

        revoked = store.revoke(token.token)

        self.assertTrue(revoked)
        self.assertFalse(token.active)

    def test_active_tokens_returns_only_active_records(self) -> None:
        store = TokenStore()
        first = store.issue("user_abc12345", "ZAERA", "guardian")
        second = store.issue("user_def67890", "Alice", "user")
        store.revoke(second.token)

        active = store.active_tokens()

        self.assertEqual([record.token for record in active], [first.token])

    def test_revoke_all_for_user_revokes_all_matching_tokens(self) -> None:
        store = TokenStore()
        first = store.issue("user_abc12345", "ZAERA", "guardian")
        second = store.issue("user_abc12345", "ZAERA", "guardian")
        third = store.issue("user_def67890", "Alice", "user")

        count = store.revoke_all_for_user("user_abc12345")

        self.assertEqual(count, 2)
        self.assertFalse(first.active)
        self.assertFalse(second.active)
        self.assertTrue(third.active)


def datetime_delta_hours(issued_at: str, expires_at: str) -> int:
    from datetime import datetime

    issued = datetime.fromisoformat(issued_at)
    expires = datetime.fromisoformat(expires_at)
    return int((expires - issued).total_seconds() / 3600)


if __name__ == "__main__":
    unittest.main()

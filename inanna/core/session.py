from __future__ import annotations

import json
import unittest
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib import error, request


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Session:
    session_id: str
    session_path: Path
    context_summary: list[str]
    started_at: str = field(default_factory=utc_now)
    events: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def create(cls, session_dir: Path, context_summary: list[str]) -> "Session":
        session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        session_id = f"{session_id}-{uuid.uuid4().hex[:8]}"
        session_path = session_dir / f"{session_id}.json"
        session = cls(
            session_id=session_id,
            session_path=session_path,
            context_summary=context_summary,
        )
        session.persist()
        return session

    def add_event(self, role: str, content: str) -> None:
        self.events.append(
            {
                "timestamp": utc_now(),
                "role": role,
                "content": content,
            }
        )
        self.persist()

    def persist(self) -> None:
        payload = {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "context_summary": self.context_summary,
            "events": self.events,
        }
        self.session_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )


class Engine:
    # Phase 2 policy: LM Studio is the explicit local model provider and uses
    # its OpenAI-compatible endpoint at the configured URL.
    # Phase 2 policy: approve and reject always resolve the oldest pending
    # proposal first; that rule is enforced in Proposal.resolve_next.
    def __init__(
        self,
        model_url: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model_url = (model_url or "").strip()
        self.model_name = (model_name or "").strip()
        self.api_key = (api_key or "").strip()
        self.fallback_mode = not (self.model_url and self.model_name)

    def verify_connection(self) -> bool:
        if not (self.model_url and self.model_name):
            self.fallback_mode = True
            return False

        try:
            self._call_openai_compatible(
                [{"role": "user", "content": "Connection check. Reply with ok."}]
            )
        except (OSError, ValueError, error.URLError):
            self.fallback_mode = True
            return False

        self.fallback_mode = False
        return True

    def respond(
        self,
        context_summary: list[str],
        conversation: list[dict[str, str]],
    ) -> str:
        latest_user = self._latest_user_message(conversation)
        if self.fallback_mode or not (self.model_url and self.model_name):
            return self._fallback_response(
                latest_user=latest_user,
                context_summary=context_summary,
                conversation=conversation,
            )

        messages = self._build_messages(context_summary, conversation)
        try:
            return self._call_openai_compatible(messages)
        except (OSError, ValueError, error.URLError) as exc:
            self.fallback_mode = True
            return self._fallback_response(
                latest_user=latest_user,
                context_summary=context_summary,
                conversation=conversation,
                note=f"Model call failed, so fallback mode continued safely: {exc}",
            )

    def _latest_user_message(self, conversation: list[dict[str, str]]) -> str:
        for event in reversed(conversation):
            if event.get("role") == "user":
                return event.get("content", "")
        return ""

    def _build_messages(
        self,
        context_summary: list[str],
        conversation: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        system_lines = [
            "You are the Phase 2 real voice companion.",
            "Keep responses clear, brief, and grounded in readable truth.",
            "Do not claim abilities beyond this session.",
        ]

        if context_summary:
            system_lines.append("Prior context:")
            system_lines.extend(context_summary)

        messages = [{"role": "system", "content": "\n".join(system_lines)}]
        for event in conversation:
            messages.append(
                {
                    "role": event["role"],
                    "content": event["content"],
                }
            )
        return messages

    def _call_openai_compatible(self, messages: list[dict[str, str]]) -> str:
        endpoint = self.model_url.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/chat/completions"

        payload = json.dumps(
            {
                "model": self.model_name,
                "messages": messages,
            }
        ).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = request.urlopen(
            request.Request(endpoint, data=payload, headers=headers, method="POST")
        )
        body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()

    def _fallback_response(
        self,
        latest_user: str,
        context_summary: list[str],
        conversation: list[dict[str, str]],
        note: str | None = None,
    ) -> str:
        parts = [
            "Phase 2 fallback mode is active.",
            f"I heard: {latest_user}",
        ]
        if context_summary:
            parts.append(
                f"I am carrying {len(context_summary)} line(s) of prior context into this session."
            )
        if len(conversation) > 1:
            parts.append("This turn has been logged into the session history.")
        if note:
            parts.append(note)
        return " ".join(parts)


# Phase 2 policy: tests remain inside component modules until Phase 3 creates a
# dedicated test layout.
class SessionComponentTests(unittest.TestCase):
    def test_session_persists_context_and_events(self) -> None:
        with TemporaryDirectory() as temp_dir:
            session_dir = Path(temp_dir)
            session = Session.create(session_dir, ["memory line"])
            session.add_event("user", "hello")
            payload = json.loads(session.session_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["context_summary"], ["memory line"])
        self.assertEqual(payload["events"][0]["role"], "user")
        self.assertEqual(payload["events"][0]["content"], "hello")

    def test_engine_fallback_responds_without_configuration(self) -> None:
        engine = Engine()
        reply = engine.respond(
            context_summary=["old memory"],
            conversation=[{"role": "user", "content": "Is anyone there?"}],
        )

        self.assertIn("Phase 2 fallback mode is active.", reply)
        self.assertIn("Is anyone there?", reply)
        self.assertIn("prior context", reply)

    def test_verify_connection_enables_model_mode_on_success(self) -> None:
        engine = Engine(
            model_url="http://localhost:1234/v1",
            model_name="local-model",
        )

        with patch.object(engine, "_call_openai_compatible", return_value="ok"):
            connected = engine.verify_connection()

        self.assertTrue(connected)
        self.assertFalse(engine.fallback_mode)

    def test_verify_connection_falls_back_when_model_is_unreachable(self) -> None:
        engine = Engine(
            model_url="http://localhost:1234/v1",
            model_name="local-model",
        )

        with patch.object(engine, "_call_openai_compatible", side_effect=OSError("down")):
            connected = engine.verify_connection()

        self.assertFalse(connected)
        self.assertTrue(engine.fallback_mode)


if __name__ == "__main__":
    unittest.main()

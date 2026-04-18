from __future__ import annotations

import json
import os
import unittest
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
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
    # DECISION POINT: The phase document requires a local or API-based model
    # but does not define the provider, so this engine uses an
    # OpenAI-compatible endpoint when configured and a deterministic local
    # fallback otherwise.
    def __init__(
        self,
        model_url: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model_url = (model_url or os.getenv("INANNA_MODEL_URL", "")).strip()
        self.model_name = (model_name or os.getenv("INANNA_MODEL_NAME", "")).strip()
        self.api_key = (api_key or os.getenv("INANNA_API_KEY", "")).strip()

    def respond(
        self,
        context_summary: list[str],
        conversation: list[dict[str, str]],
    ) -> str:
        latest_user = self._latest_user_message(conversation)
        messages = self._build_messages(context_summary, conversation)

        if self.model_url and self.model_name:
            try:
                return self._call_openai_compatible(messages)
            except (OSError, ValueError, error.URLError) as exc:
                return self._fallback_response(
                    latest_user=latest_user,
                    context_summary=context_summary,
                    conversation=conversation,
                    note=f"Model call failed, so fallback mode continued safely: {exc}",
                )

        return self._fallback_response(
            latest_user=latest_user,
            context_summary=context_summary,
            conversation=conversation,
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
            "You are the Phase 1 living loop companion.",
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
            "Phase 1 fallback mode is active.",
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


# DECISION POINT: CURRENT_PHASE.md requires unit tests to pass but only lists
# component file locations, so the basic tests live inside the component module.
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

        self.assertIn("Phase 1 fallback mode is active.", reply)
        self.assertIn("Is anyone there?", reply)
        self.assertIn("prior context", reply)


if __name__ == "__main__":
    unittest.main()

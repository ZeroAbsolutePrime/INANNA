from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request

from identity import build_system_prompt


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
    # Phase 2 policy, still active in Phase 4: LM Studio is the explicit local
    # model provider and uses its OpenAI-compatible endpoint at the configured
    # URL.
    # Phase 2 policy, still active in Phase 4: approve and reject always
    # resolve the oldest pending proposal first; that rule is enforced in
    # Proposal.resolve_next.
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
        self._connected = False

    @property
    def mode(self) -> str:
        return "connected" if self._connected else "fallback"

    def verify_connection(self) -> bool:
        if not (self.model_url and self.model_name):
            self.fallback_mode = True
            self._connected = False
            return False

        try:
            self._call_openai_compatible(
                [{"role": "user", "content": "Connection check. Reply with ok."}]
            )
        except (OSError, ValueError, error.URLError):
            self.fallback_mode = True
            self._connected = False
            return False

        self.fallback_mode = False
        self._connected = True
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
            self._connected = False
            return self._fallback_response(
                latest_user=latest_user,
                context_summary=context_summary,
                conversation=conversation,
                note=f"Model call failed, so fallback mode continued safely: {exc}",
            )

    def reflect(self, context_summary: list[str]) -> str:
        if not context_summary:
            return "I hold no approved memory of our prior conversations yet."
        messages = [
            {
                "role": "system",
                "content": build_system_prompt(),
            },
            {
                "role": "user",
                "content": (
                    "Please reflect on what you currently remember about me "
                    "and our conversation history, based only on your approved memory. "
                    "Speak honestly about what you know and what you do not know."
                ),
            },
        ]
        if context_summary:
            memory_block = "\n".join(context_summary)
            messages.insert(
                1,
                {
                    "role": "assistant",
                    "content": f"From my approved memory:\n{memory_block}",
                },
            )
        if self.model_url and self.model_name and self._connected:
            try:
                return self._call_openai_compatible(messages)
            except Exception:
                pass
        return "From my approved memory I hold these lines:\n" + "\n".join(
            f"  {line}" for line in context_summary
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
        system_prompt = build_system_prompt()
        if context_summary:
            system_prompt = f"{system_prompt}\n\nPrior context:\n" + "\n".join(
                context_summary
            )

        messages = [{"role": "system", "content": system_prompt}]
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
            "Phase 3 fallback mode is active.",
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

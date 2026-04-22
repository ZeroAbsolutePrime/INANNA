from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from urllib import error, request

from identity import build_analyst_prompt, build_system_prompt, phase_banner

if TYPE_CHECKING:
    from core.realm import RealmConfig


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
    # LM Studio is the explicit local model provider and uses its
    # OpenAI-compatible endpoint at the configured URL.
    def __init__(
        self,
        model_url: str | None = None,
        model_name: str | None = None,
        api_key: str | None = None,
        realm: "RealmConfig | None" = None,
        grounding_prefix: str = "",
    ) -> None:
        self.model_url = (model_url or "").strip()
        self.model_name = (model_name or "").strip()
        self.api_key = (api_key or "").strip()
        self.realm = realm
        self.grounding_prefix = grounding_prefix.strip()
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
                [{"role": "user", "content": "hi"}],
                timeout=2,
            )
        except Exception:
            self.fallback_mode = True
            self._connected = False
            return False

        self.fallback_mode = False
        self._connected = True
        return True

    def respond(
        self,
        context_summary: list[str | dict[str, str]],
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

    def reflect(
        self,
        context_summary: list[str | dict[str, str]],
    ) -> tuple[str, str]:
        if not context_summary:
            return ("fallback", "I hold no approved memory of our prior conversations yet.")
        messages = self._build_reflection_messages(context_summary)
        if self.model_url and self.model_name and self._connected:
            try:
                return ("live", self._call_openai_compatible(messages))
            except Exception:
                pass
        return (
            "fallback",
            "From my approved memory:\n"
            + "\n".join(
                f"  {i + 1}. {self._format_grounding_line(line)}"
                for i, line in enumerate(context_summary)
            ),
        )

    def speak_audit(
        self,
        history: dict,
        memory_log: dict,
        context_summary: list[str | dict[str, str]],
    ) -> tuple[str, str]:
        messages = [
            {"role": "system", "content": build_system_prompt(self.realm)},
            {
                "role": "assistant",
                "content": self._build_audit_context(history, memory_log),
            },
            {
                "role": "user",
                "content": (
                    "Please describe your proposal history and approved memory "
                    "records in your own voice. Be specific and honest about "
                    "what has been approved, what is pending, and what you "
                    "currently carry into this session."
                ),
            },
        ]
        if self.model_url and self.model_name and self._connected:
            try:
                return ("live", self._call_openai_compatible(messages))
            except Exception:
                pass
        return ("fallback", self._build_audit_context(history, memory_log))

    def _latest_user_message(self, conversation: list[dict[str, str]]) -> str:
        for event in reversed(conversation):
            if event.get("role") == "user":
                return event.get("content", "")
        return ""

    def _build_messages(
        self,
        context_summary: list[str | dict[str, str]],
        conversation: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": build_system_prompt(self.realm)}]
        messages.append(self._build_grounding_turn(context_summary))

        for event in conversation:
            messages.append(
                {
                    "role": event["role"],
                    "content": event["content"],
                }
            )
        return messages

    def _build_reflection_messages(
        self,
        context_summary: list[str | dict[str, str]],
    ) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": build_system_prompt(self.realm)}]
        messages.append(self._build_grounding_turn(context_summary))

        messages.append(
            {
                "role": "user",
                "content": (
                    "Please reflect on what you currently remember about me "
                    "and our conversation history, based only on your approved memory. "
                    "Speak honestly about what you know and what you do not know."
                ),
            }
        )
        return messages

    def _build_audit_context(self, history: dict, memory_log: dict) -> str:
        lines = [
            f"My proposal history: {history['total']} total, "
            f"{history['approved']} approved, "
            f"{history['rejected']} rejected, "
            f"{history['pending']} pending.",
        ]
        for record in history["records"]:
            lines.append(f"  [{record['status']}] {record['proposal_id']}: {record['what']}")
        lines.append(f"My approved memory records: {memory_log['total']} total.")
        for record in memory_log["records"]:
            summary = ", ".join(record.get("summary_lines", [])[:2])
            lines.append(
                f"  [{record['memory_id']}] session {record['session_id']}: {summary}"
            )
        return "\n".join(lines)

    def _build_grounding_turn(
        self,
        context_summary: list[str | dict[str, str]],
    ) -> dict[str, str]:
        prefix = f"{self.grounding_prefix}\n" if self.grounding_prefix else ""
        if not context_summary:
            return {
                "role": "assistant",
                "content": (
                    prefix
                    + "I hold no approved memory of prior conversations yet.\n"
                    "I will not invent or infer anything about this person.\n"
                    "I will respond only to what they tell me now."
                ),
            }

        grounding_lines = "\n".join(
            f"  {i + 1}. {self._format_grounding_line(line)}"
            for i, line in enumerate(context_summary)
        )
        return {
            "role": "assistant",
            "content": (
                prefix
                + "From my approved memory of our prior conversations:\n"
                + grounding_lines
                + "\n\nI will ground my responses in this approved memory.\n"
                + "I will not add, invent, or infer anything beyond these lines.\n"
                + "If I do not know something about this person, I will say so directly."
            ),
        }

    def _context_text(self, item: str | dict[str, str]) -> str:
        if isinstance(item, dict):
            return item.get("text", "").strip()
        return item.strip()

    def _context_realm(self, item: str | dict[str, str]) -> str:
        if isinstance(item, dict):
            return item.get("realm_name", "").strip()
        return ""

    def _format_grounding_line(self, item: str | dict[str, str]) -> str:
        text = self._context_text(item)
        realm_name = self._context_realm(item)
        active_realm_name = self.realm.name if self.realm else ""
        if realm_name and active_realm_name and realm_name != active_realm_name:
            return f"{text} (from realm: {realm_name})"
        return text

    def _call_openai_compatible(
        self,
        messages: list[dict[str, str]],
        timeout: float | None = None,
    ) -> str:
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
            request.Request(endpoint, data=payload, headers=headers, method="POST"),
            timeout=timeout,
        )
        body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()

    def _fallback_response(
        self,
        latest_user: str,
        context_summary: list[str | dict[str, str]],
        conversation: list[dict[str, str]],
        note: str | None = None,
    ) -> str:
        parts = [
            f"{phase_banner()} — fallback mode is active.",
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


class AnalystFaculty(Engine):
    def analyse(
        self,
        question: str,
        context: list[str | dict[str, str]],
    ) -> tuple[str, str]:
        cleaned_question = question.strip()
        if not cleaned_question:
            return ("fallback", "Please provide a question to analyse.")

        messages = self._build_analysis_messages(cleaned_question, context)
        if self.model_url and self.model_name and self._connected:
            try:
                return ("live", self._call_openai_compatible(messages))
            except (OSError, ValueError, error.URLError) as exc:
                self.fallback_mode = True
                self._connected = False
                return (
                    "fallback",
                    self._fallback_analysis(
                        question=cleaned_question,
                        context=context,
                        note=f"Model call failed, so fallback analysis continued safely: {exc}",
                    ),
                )

        return ("fallback", self._fallback_analysis(cleaned_question, context))

    def _build_analysis_messages(
        self,
        question: str,
        context: list[str | dict[str, str]],
    ) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": build_analyst_prompt()}]
        if context:
            context_lines = "\n".join(
                f"  {index + 1}. {self._format_grounding_line(line)}"
                for index, line in enumerate(context)
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": (
                        "Approved context available for this analysis:\n"
                        f"{context_lines}"
                    ),
                }
            )
        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": "No approved context is available for this analysis yet.",
                }
            )

        messages.append({"role": "user", "content": question})
        return messages

    def _fallback_analysis(
        self,
        question: str,
        context: list[str | dict[str, str]],
        note: str | None = None,
    ) -> str:
        lines = [
            "Structured analysis fallback:",
            f"Question: {question}",
            f"Approved context lines: {len(context)}",
        ]
        for index, line in enumerate(context, start=1):
            lines.append(f"  {index}. {self._format_grounding_line(line)}")
        if not context:
            lines.append("No approved context is available yet.")
        lines.append("Model connection is unavailable, so this is a bounded analytical summary.")
        if note:
            lines.append(note)
        return "\n".join(lines)

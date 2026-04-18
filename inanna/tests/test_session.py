from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.session import Engine, Session
from identity import build_system_prompt, phase_banner


class SessionTests(unittest.TestCase):
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

        self.assertIn(f"{phase_banner()} — fallback mode is active.", reply)
        self.assertIn("Is anyone there?", reply)
        self.assertIn("prior context", reply)
        self.assertEqual(engine.mode, "fallback")

    def test_verify_connection_enables_model_mode_on_success(self) -> None:
        engine = Engine(
            model_url="http://localhost:1234/v1",
            model_name="local-model",
        )

        with patch.object(engine, "_call_openai_compatible", return_value="ok"):
            connected = engine.verify_connection()

        self.assertTrue(connected)
        self.assertEqual(engine.mode, "connected")

    def test_verify_connection_falls_back_when_model_is_unreachable(self) -> None:
        engine = Engine(
            model_url="http://localhost:1234/v1",
            model_name="local-model",
        )

        with patch.object(engine, "_call_openai_compatible", side_effect=OSError("down")):
            connected = engine.verify_connection()

        self.assertFalse(connected)
        self.assertEqual(engine.mode, "fallback")

    def test_engine_uses_inanna_identity_prompt(self) -> None:
        engine = Engine()
        messages = engine._build_messages(
            context_summary=[],
            conversation=[{"role": "user", "content": "who are you?"}],
        )

        self.assertEqual(messages[0]["content"], build_system_prompt())
        self.assertEqual(messages[0]["role"], "system")
        self.assertNotIn("DeepSeek Coder", messages[0]["content"])

    def test_grounding_is_injected_when_context_is_empty(self) -> None:
        engine = Engine()
        messages = engine._build_messages(
            context_summary=[],
            conversation=[{"role": "user", "content": "hello"}],
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertIn("no approved memory", messages[1]["content"])
        self.assertEqual(messages[2]["role"], "user")

    def test_grounding_is_injected_as_assistant_turn_before_user(self) -> None:
        engine = Engine()
        messages = engine._build_messages(
            context_summary=["user: What do you value most?", "assistant: As INANNA I value..."],
            conversation=[{"role": "user", "content": "tell me more"}],
        )

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertIn("approved memory", messages[1]["content"])
        self.assertIn("I will not add, invent, or infer", messages[1]["content"])
        self.assertEqual(messages[2]["role"], "user")
        self.assertEqual(messages[2]["content"], "tell me more")

    def test_reflect_uses_grounding_and_returns_live_tuple_when_connected(self) -> None:
        engine = Engine(
            model_url="http://localhost:1234/v1",
            model_name="local-model",
        )
        engine._connected = True

        with patch.object(engine, "_call_openai_compatible", return_value="grounded reflection") as mocked_call:
            mode, text = engine.reflect(["user: hello", "assistant: welcome back"])

        messages = mocked_call.call_args.args[0]
        self.assertEqual(mode, "live")
        self.assertEqual(text, "grounded reflection")
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertIn("approved memory", messages[1]["content"])
        self.assertIn("I will not add, invent, or infer", messages[1]["content"])
        self.assertEqual(messages[2]["role"], "user")

    def test_reflect_fallback_returns_numbered_memory_lines(self) -> None:
        engine = Engine()

        mode, text = engine.reflect(["user: hello", "assistant: welcome back"])

        self.assertEqual(mode, "fallback")
        self.assertIn("From my approved memory:", text)
        self.assertIn("1. user: hello", text)
        self.assertIn("2. assistant: welcome back", text)

    def test_speak_audit_uses_audit_context_and_returns_live_tuple_when_connected(self) -> None:
        engine = Engine(
            model_url="http://localhost:1234/v1",
            model_name="local-model",
        )
        engine._connected = True
        history = {
            "total": 2,
            "approved": 1,
            "rejected": 0,
            "pending": 1,
            "records": [
                {
                    "status": "approved",
                    "proposal_id": "proposal-a",
                    "what": "Update memory",
                },
                {
                    "status": "pending",
                    "proposal_id": "proposal-b",
                    "what": "Update memory again",
                },
            ],
        }
        memory_log = {
            "total": 1,
            "records": [
                {
                    "memory_id": "proposal-a",
                    "session_id": "session-1",
                    "summary_lines": ["user: hello", "assistant: welcome back"],
                }
            ],
        }

        with patch.object(engine, "_call_openai_compatible", return_value="audit voice") as mocked_call:
            mode, text = engine.speak_audit(history, memory_log, ["user: hello"])

        messages = mocked_call.call_args.args[0]
        self.assertEqual(mode, "live")
        self.assertEqual(text, "audit voice")
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "assistant")
        self.assertIn("My proposal history: 2 total, 1 approved, 0 rejected, 1 pending.", messages[1]["content"])
        self.assertIn("[proposal-a] session session-1: user: hello, assistant: welcome back", messages[1]["content"])
        self.assertEqual(messages[2]["role"], "user")

    def test_speak_audit_fallback_returns_formatted_audit_context(self) -> None:
        engine = Engine()
        history = {
            "total": 1,
            "approved": 1,
            "rejected": 0,
            "pending": 0,
            "records": [
                {
                    "status": "approved",
                    "proposal_id": "proposal-a",
                    "what": "Update memory",
                }
            ],
        }
        memory_log = {
            "total": 1,
            "records": [
                {
                    "memory_id": "proposal-a",
                    "session_id": "session-1",
                    "summary_lines": ["user: hello"],
                }
            ],
        }

        mode, text = engine.speak_audit(history, memory_log, ["user: hello"])

        self.assertEqual(mode, "fallback")
        self.assertIn("My proposal history: 1 total, 1 approved, 0 rejected, 0 pending.", text)
        self.assertIn("[approved] proposal-a: Update memory", text)
        self.assertIn("My approved memory records: 1 total.", text)


if __name__ == "__main__":
    unittest.main()

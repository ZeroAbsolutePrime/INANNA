from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.session import Engine, Session
from identity import build_system_prompt


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

        self.assertIn("Phase 3 fallback mode is active.", reply)
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
            context_summary=["user: hello"],
            conversation=[{"role": "user", "content": "who are you?"}],
        )

        self.assertTrue(messages[0]["content"].startswith(build_system_prompt()))
        self.assertIn("you are INANNA", messages[0]["content"])
        self.assertNotIn("DeepSeek Coder", messages[0]["content"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import io
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from core.session import Engine
from main import _extract_intent_with_timeout, extract_email_tool_request
from ui.server import InterfaceServer
import ui_main


class StartupTests(unittest.TestCase):
    def test_verify_connection_uses_two_second_timeout(self) -> None:
        engine = Engine(model_url="http://localhost:1234", model_name="test-model")

        with patch.object(engine, "_call_openai_compatible", return_value="ok") as call_mock:
            connected = engine.verify_connection()

        self.assertTrue(connected)
        self.assertTrue(engine._connected)
        self.assertEqual(call_mock.call_args.kwargs["timeout"], 2)

    def test_interface_server_init_completes_with_mocked_verify_connection(self) -> None:
        with patch("ui.server.Engine.verify_connection", return_value=False), patch(
            "ui.server.sync_profile_grounding"
        ) as sync_mock:
            t0 = time.monotonic()
            server = InterfaceServer()
            elapsed = time.monotonic() - t0

        self.assertLess(elapsed, 5.0)
        self.assertFalse(server.engine._connected)
        sync_mock.assert_not_called()

    def test_threaded_intent_timeout_returns_none_quickly(self) -> None:
        def slow_extract(user_input: str, conversation_context=None):  # type: ignore[no-untyped-def]
            del user_input, conversation_context
            time.sleep(0.2)
            return Mock()

        with patch("main.extract_intent", side_effect=slow_extract):
            t0 = time.monotonic()
            result = _extract_intent_with_timeout("anything from Matxalen?", timeout_s=0.01)
            elapsed = time.monotonic() - t0

        self.assertIsNone(result)
        self.assertLess(elapsed, 0.1)

    def test_extract_email_tool_request_returns_regex_result_quickly_for_anything_from(self) -> None:
        with patch("main._extract_intent_with_timeout", return_value=None):
            t0 = time.monotonic()
            result = extract_email_tool_request("anything from Matxalen?")
            elapsed = time.monotonic() - t0

        self.assertLess(elapsed, 0.1)
        self.assertIsNotNone(result)
        self.assertEqual(result["tool"], "email_search")
        self.assertEqual(result["params"]["query"], "matxalen")

    def test_extract_email_tool_request_returns_regex_result_quickly_for_urgentes(self) -> None:
        with patch("main._extract_intent_with_timeout", return_value=None):
            t0 = time.monotonic()
            result = extract_email_tool_request("urgentes?")
            elapsed = time.monotonic() - t0

        self.assertLess(elapsed, 0.1)
        self.assertIsNotNone(result)
        self.assertEqual(result["tool"], "email_read_inbox")
        self.assertTrue(result["params"]["urgency_only"])

    def test_ui_main_prints_startup_measurement(self) -> None:
        fake_server = Mock()
        fake_server.engine._connected = False
        output = io.StringIO()
        with patch("ui_main.InterfaceServer", return_value=fake_server), patch(
            "ui_main.run_http_server"
        ), patch("ui_main.webbrowser.open"), patch("ui_main.asyncio.run"), redirect_stdout(output):
            ui_main.main()

        printed = output.getvalue()
        self.assertIn("INANNA NYX ready in", printed)
        self.assertIn("Model: fallback mode", printed)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import time
import unittest
from unittest.mock import patch

from core.nammu_intent import (
    IntentResult,
    NAMMU_UNIVERSAL_PROMPT,
    _classify_domain_fast,
    extract_intent_universal,
)
from identity import CURRENT_PHASE
from main import (
    extract_browser_tool_request,
    extract_calendar_tool_request,
    extract_document_tool_request,
    extract_email_tool_request,
    nammu_first_routing,
)


class IntentEngineTests(unittest.TestCase):
    def test_intent_result_domain_defaults_to_empty_string(self) -> None:
        self.assertEqual("", IntentResult(intent="none").domain)

    def test_extract_intent_universal_uses_universal_prompt(self) -> None:
        success = IntentResult(intent="email_search", confidence=0.97, domain="email")
        with patch("core.nammu_intent._call_llm", side_effect=[success]) as call_llm:
            extract_intent_universal("anything from Matxalen?")

        self.assertEqual(NAMMU_UNIVERSAL_PROMPT, call_llm.call_args.kwargs["prompt"])

    def test_classify_domain_fast_returns_email_for_check_my_email(self) -> None:
        self.assertEqual("email", _classify_domain_fast("check my email"))

    def test_classify_domain_fast_returns_document_for_pdf_path(self) -> None:
        self.assertEqual("document", _classify_domain_fast("read ~/report.pdf"))

    def test_classify_domain_fast_returns_browser_for_search_web(self) -> None:
        self.assertEqual("browser", _classify_domain_fast("search the web for NixOS"))

    def test_classify_domain_fast_returns_calendar_for_calendar_question(self) -> None:
        self.assertEqual("calendar", _classify_domain_fast("what's on my calendar"))

    def test_classify_domain_fast_returns_desktop_for_open_firefox(self) -> None:
        self.assertEqual("desktop", _classify_domain_fast("open firefox"))

    def test_classify_domain_fast_returns_filesystem_for_list_documents(self) -> None:
        self.assertEqual("filesystem", _classify_domain_fast("list my documents"))

    def test_classify_domain_fast_returns_none_for_plain_conversation(self) -> None:
        self.assertEqual("none", _classify_domain_fast("hello how are you"))

    def test_classify_domain_fast_returns_email_for_urgentes(self) -> None:
        self.assertEqual("email", _classify_domain_fast("urgentes?"))

    def test_classify_domain_fast_returns_network_for_ping(self) -> None:
        self.assertEqual("network", _classify_domain_fast("ping google.com"))

    def test_nammu_first_routing_returns_none_for_none_domain(self) -> None:
        with patch("main._classify_domain_fast", return_value="none"):
            self.assertIsNone(nammu_first_routing("hello how are you"))

    def test_nammu_first_routing_returns_none_when_llm_times_out(self) -> None:
        def slow_intent(*args, **kwargs):
            time.sleep(3.2)
            return IntentResult(intent="email_search", params={"query": "Matxalen"}, confidence=0.97, domain="email")

        with patch("main._classify_domain_fast", return_value="email"), patch(
            "main.extract_intent_universal",
            side_effect=slow_intent,
        ):
            self.assertIsNone(nammu_first_routing("anything from Matxalen?"))

    def test_nammu_first_routing_returns_tool_request_when_confident(self) -> None:
        result = IntentResult(
            intent="email_search",
            params={"query": "Matxalen", "app": "thunderbird"},
            confidence=0.97,
            domain="email",
        )
        with patch("main._classify_domain_fast", return_value="email"), patch(
            "main.extract_intent_universal",
            return_value=result,
        ):
            request = nammu_first_routing("anything from Matxalen?")

        self.assertIsNotNone(request)
        self.assertEqual("email_search", request["tool"])
        self.assertEqual("email", request["domain"])

    def test_nammu_first_routing_returns_none_when_low_confidence(self) -> None:
        result = IntentResult(
            intent="email_search",
            params={"query": "Matxalen"},
            confidence=0.5,
            domain="email",
        )
        with patch("main._classify_domain_fast", return_value="email"), patch(
            "main.extract_intent_universal",
            return_value=result,
        ):
            self.assertIsNone(nammu_first_routing("anything from Matxalen?"))

    def test_universal_prompt_contains_all_eleven_domains(self) -> None:
        for name in (
            "EMAIL:",
            "COMMUNICATION:",
            "DOCUMENT:",
            "BROWSER:",
            "CALENDAR:",
            "DESKTOP:",
            "FILESYSTEM:",
            "PROCESS:",
            "PACKAGE:",
            "NETWORK:",
            "INFORMATION:",
        ):
            self.assertIn(name, NAMMU_UNIVERSAL_PROMPT)

    def test_universal_prompt_contains_example_json_outputs(self) -> None:
        self.assertIn('{"intent":"email_search"', NAMMU_UNIVERSAL_PROMPT)
        self.assertIn('{"intent":"none"', NAMMU_UNIVERSAL_PROMPT)

    def test_to_tool_request_includes_domain(self) -> None:
        result = IntentResult(
            intent="email_search",
            params={"query": "Matxalen"},
            confidence=0.97,
            domain="email",
        )

        request = result.to_tool_request()

        self.assertEqual("email", request["domain"])
        self.assertIn("domain=email", request["reason"])

    def test_email_regex_fallback_still_routes_anything_from(self) -> None:
        request = extract_email_tool_request("anything from Matxalen?")

        self.assertIsNotNone(request)
        self.assertEqual("email_search", request["tool"])

    def test_document_regex_fallback_routes_read_pdf(self) -> None:
        request = extract_document_tool_request("read ~/report.pdf")

        self.assertIsNotNone(request)
        self.assertEqual("doc_read", request["tool"])

    def test_browser_regex_fallback_routes_fetch_url(self) -> None:
        request = extract_browser_tool_request("fetch https://example.com")

        self.assertIsNotNone(request)
        self.assertEqual("browser_read", request["tool"])

    def test_calendar_regex_fallback_routes_today_question(self) -> None:
        request = extract_calendar_tool_request("what do I have today")

        self.assertIsNotNone(request)
        self.assertEqual("calendar_today", request["tool"])

    def test_extract_intent_universal_returns_llm_result_with_domain(self) -> None:
        result = IntentResult(intent="browser_search", params={"query": "NixOS"}, confidence=0.98, domain="browser")
        with patch("core.nammu_intent._call_llm", side_effect=[result]):
            parsed = extract_intent_universal("search the web for NixOS")

        self.assertEqual("browser", parsed.domain)
        self.assertEqual("browser_search", parsed.intent)

    def test_suite_discovery_count_is_at_least_621(self) -> None:
        suite = unittest.TestLoader().discover("tests")

        self.assertGreaterEqual(suite.countTestCases(), 621)

    def test_phase_identity_contains_cycle9_phase5(self) -> None:
        self.assertIn("9.5", CURRENT_PHASE)


if __name__ == "__main__":
    unittest.main()

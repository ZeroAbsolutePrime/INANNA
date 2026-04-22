from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

from core.email_workflows import EmailRecord
from core.nammu_intent import (
    URGENCY_KEYWORDS,
    EmailComprehension,
    IntentResult,
    NAMMU_UNIVERSAL_PROMPT,
    _classify_domain_fast,
    _call_llm,
    build_comprehension,
    extract_intent,
)
from main import _has_email_comm_signal


class NammuIntentTests(unittest.TestCase):
    def test_intent_result_instantiates_correctly(self) -> None:
        result = IntentResult(
            intent="email_search",
            params={"query": "Matxalen"},
            confidence=0.97,
            domain="email",
        )

        self.assertEqual(result.intent, "email_search")
        self.assertEqual(result.params["query"], "Matxalen")
        self.assertAlmostEqual(result.confidence, 0.97)
        self.assertEqual(result.domain, "email")

    def test_intent_result_success_true_for_non_none_intent(self) -> None:
        self.assertTrue(IntentResult(intent="email_read_inbox").success)

    def test_intent_result_success_false_for_none_intent(self) -> None:
        self.assertFalse(IntentResult(intent="none").success)

    def test_to_tool_request_returns_dict_for_valid_intent(self) -> None:
        result = IntentResult(intent="email_search", params={"query": "Matxalen"}, confidence=0.9)

        request = result.to_tool_request()

        self.assertEqual(request["tool"], "email_search")
        self.assertEqual(request["params"]["query"], "Matxalen")
        self.assertIn("confidence=0.90", request["reason"])

    def test_to_tool_request_returns_none_for_none_intent(self) -> None:
        self.assertIsNone(IntentResult(intent="none").to_tool_request())

    def test_call_llm_returns_error_on_connection_fail(self) -> None:
        with patch("core.nammu_intent.urllib.request.urlopen", side_effect=OSError("down")):
            result = _call_llm("check my email", "model", 1, None)

        self.assertEqual(result.intent, "none")
        self.assertIn("down", str(result.error))

    def test_extract_intent_returns_none_on_empty_input(self) -> None:
        result = extract_intent("   ")

        self.assertEqual(result.intent, "none")
        self.assertIn("empty input", str(result.error))

    def test_extract_intent_returns_none_on_llm_failure(self) -> None:
        with patch("core.nammu_intent._call_llm", return_value=IntentResult(intent="none", error="fail")):
            result = extract_intent("anything urgent?")

        self.assertEqual(result.intent, "none")
        self.assertIn("falling back", str(result.error))

    def test_email_comprehension_defaults(self) -> None:
        comprehension = EmailComprehension()

        self.assertEqual(comprehension.total, 0)
        self.assertEqual(comprehension.urgent, [])
        self.assertEqual(comprehension.by_contact, {})

    def test_build_comprehension_returns_total_count(self) -> None:
        emails = [
            EmailRecord(sender="Matxalen", subject="Hello"),
            EmailRecord(sender="Anthropic", subject="Receipt"),
        ]

        comprehension = build_comprehension(emails)

        self.assertEqual(comprehension.total, 2)

    def test_build_comprehension_detects_urgency_keywords(self) -> None:
        emails = [EmailRecord(sender="Matxalen", subject="Urgent proposal review")]

        comprehension = build_comprehension(emails)

        self.assertEqual(len(comprehension.urgent), 1)
        self.assertEqual(comprehension.urgent[0]["from"], "Matxalen")

    def test_build_comprehension_groups_by_contact(self) -> None:
        emails = [
            EmailRecord(sender="Matxalen", subject="First"),
            EmailRecord(sender="Matxalen", subject="Second"),
        ]

        comprehension = build_comprehension(emails)

        self.assertEqual(comprehension.by_contact["Matxalen"]["count"], 2)
        self.assertEqual(comprehension.by_contact["Matxalen"]["latest"], "Second")

    def test_to_crown_context_includes_total_count(self) -> None:
        comprehension = build_comprehension([EmailRecord(sender="A", subject="Hello")], period="today")

        context = comprehension.to_crown_context()

        self.assertIn("Total: 1 emails, 0 unread", context)

    def test_to_crown_context_includes_urgent_section_when_present(self) -> None:
        comprehension = build_comprehension([EmailRecord(sender="A", subject="urgent ask")])

        context = comprehension.to_crown_context()

        self.assertIn("URGENT:", context)

    def test_build_comprehension_does_not_hallucinate(self) -> None:
        emails = [EmailRecord(sender="Matxalen", subject="Proposal follow-up", preview="Can you review it?")]

        context = build_comprehension(emails).to_crown_context()

        self.assertIn("Matxalen", context)
        self.assertIn("Proposal follow-up", context)
        self.assertNotIn("Anthropic", context)

    def test_urgency_keywords_contains_english_and_spanish_markers(self) -> None:
        self.assertIn("urgent", URGENCY_KEYWORDS)
        self.assertIn("urgente", URGENCY_KEYWORDS)

    def test_has_email_comm_signal_detects_check_my_email(self) -> None:
        self.assertTrue(_has_email_comm_signal("check my email"))

    def test_has_email_comm_signal_false_for_hello_world(self) -> None:
        self.assertFalse(_has_email_comm_signal("hello world"))

    def test_has_email_comm_signal_true_for_spanish(self) -> None:
        self.assertTrue(_has_email_comm_signal("correo urgente"))

    def test_call_llm_parses_json_payload(self) -> None:
        payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "intent": "email_search",
                                "params": {"query": "Matxalen", "app": "thunderbird"},
                                "confidence": 0.96,
                            }
                        )
                    }
                }
            ]
        }
        response = Mock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch("core.nammu_intent.urllib.request.urlopen", return_value=response):
            result = _call_llm("anything from Matxalen?", "model", 1, None)

        self.assertEqual(result.intent, "email_search")
        self.assertEqual(result.params["query"], "Matxalen")
        self.assertEqual(result.model_used, "model")

    def test_extract_intent_uses_primary_success_result(self) -> None:
        primary = IntentResult(intent="email_read_inbox", params={"urgency_only": True}, confidence=0.95)
        with patch("core.nammu_intent._call_llm", side_effect=[primary]):
            result = extract_intent("anything urgent?")

        self.assertEqual(result.intent, "email_read_inbox")
        self.assertTrue(result.params["urgency_only"])

    def test_classify_domain_fast_identifies_email_urgency(self) -> None:
        self.assertEqual("email", _classify_domain_fast("urgentes?"))

    def test_universal_prompt_names_information_and_package_domains(self) -> None:
        self.assertIn("INFORMATION:", NAMMU_UNIVERSAL_PROMPT)
        self.assertIn("PACKAGE:", NAMMU_UNIVERSAL_PROMPT)


if __name__ == "__main__":
    unittest.main()

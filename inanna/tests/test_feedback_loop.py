from __future__ import annotations

import unittest
from pathlib import Path

from core.nammu_profile import OperatorProfile, RoutingCorrection, analyse_routing_log
from main import parse_nammu_correction_params
from ui.server import InterfaceServer, MISROUTE_SIGNALS


class FeedbackLoopTests(unittest.TestCase):
    def test_detect_misroute_returns_true_for_english_signal(self) -> None:
        server = InterfaceServer.__new__(InterfaceServer)
        self.assertTrue(server._detect_misroute("no that's not right"))

    def test_detect_misroute_returns_true_for_spanish_signal(self) -> None:
        server = InterfaceServer.__new__(InterfaceServer)
        self.assertTrue(server._detect_misroute("no era eso"))

    def test_detect_misroute_returns_false_for_hello_world(self) -> None:
        server = InterfaceServer.__new__(InterfaceServer)
        self.assertFalse(server._detect_misroute("hello world"))

    def test_detect_misroute_returns_false_for_normal_query(self) -> None:
        server = InterfaceServer.__new__(InterfaceServer)
        self.assertFalse(server._detect_misroute("anything from Matxalen?"))

    def test_misroute_signals_contains_i_meant(self) -> None:
        self.assertIn("i meant", MISROUTE_SIGNALS)

    def test_misroute_signals_contains_no_era_eso(self) -> None:
        self.assertIn("no era eso", MISROUTE_SIGNALS)

    def test_parse_nammu_correction_params_plain_query_becomes_query_dict(self) -> None:
        self.assertEqual({"query": "Matxalen"}, parse_nammu_correction_params("Matxalen"))

    def test_parse_nammu_correction_params_json_dict_parses(self) -> None:
        self.assertEqual(
            {"query": "Matxalen", "app": "thunderbird"},
            parse_nammu_correction_params('{"query": "Matxalen", "app": "thunderbird"}'),
        )

    def test_parse_nammu_correction_params_invalid_json_falls_back_to_query(self) -> None:
        self.assertEqual({"query": "{bad json"}, parse_nammu_correction_params("{bad json"))

    def test_analyse_routing_log_returns_total_routings_count(self) -> None:
        profile = OperatorProfile()
        stats = analyse_routing_log(
            [{"route": "email_search"}, {"route": "calendar_today"}],
            profile,
        )
        self.assertEqual(2, stats["total_routings"])

    def test_analyse_routing_log_returns_top_domains_dict(self) -> None:
        profile = OperatorProfile()
        stats = analyse_routing_log(
            [{"route": "email_search"}, {"route": "email_read_inbox"}, {"route": "calendar_today"}],
            profile,
        )
        self.assertEqual({"email": 2, "calendar": 1}, stats["top_domains"])

    def test_analyse_routing_log_returns_correction_count_from_profile(self) -> None:
        profile = OperatorProfile()
        profile.record_correction("mtx replied?", "none", "email_search", {"query": "Matxalen"})
        stats = analyse_routing_log([], profile)
        self.assertEqual(1, stats["correction_count"])

    def test_analyse_routing_log_handles_empty_routing_log(self) -> None:
        stats = analyse_routing_log([], OperatorProfile())
        self.assertEqual(0, stats["total_routings"])
        self.assertEqual({}, stats["top_domains"])

    def test_operator_profile_record_correction_stores_timestamp(self) -> None:
        profile = OperatorProfile()
        profile.record_correction("mtx replied?", "none", "email_search", {"query": "Matxalen"})
        self.assertTrue(profile.routing_corrections[0]["timestamp"])

    def test_operator_profile_routing_corrections_max_20_entries(self) -> None:
        profile = OperatorProfile()
        for index in range(25):
            profile.record_correction(f"q{index}", "none", "email_search", {"query": str(index)})
        self.assertEqual(20, len(profile.routing_corrections))

    def test_routing_correction_to_example_line_includes_original_text(self) -> None:
        correction = RoutingCorrection(original_text="mtx replied?", correct_intent="email_search")
        self.assertIn("mtx replied?", correction.to_example_line())

    def test_routing_correction_to_example_line_includes_correct_intent(self) -> None:
        correction = RoutingCorrection(original_text="mtx replied?", correct_intent="email_search")
        self.assertIn("email_search", correction.to_example_line())

    def test_interface_server_source_initializes_last_nammu_input_as_empty_string(self) -> None:
        source = Path(__file__).resolve().parent.parent / "ui" / "server.py"
        text = source.read_text(encoding="utf-8")
        self.assertIn('self._last_nammu_input = ""', text)

    def test_interface_server_source_initializes_session_correction_count_as_zero(self) -> None:
        source = Path(__file__).resolve().parent.parent / "ui" / "server.py"
        text = source.read_text(encoding="utf-8")
        self.assertIn("self._session_correction_count = 0", text)

    def test_operator_profile_with_three_corrections_produces_three_example_lines(self) -> None:
        profile = OperatorProfile()
        for index in range(3):
            profile.record_correction(
                f"phrase {index}",
                "none",
                "email_search",
                {"query": f"Matxalen {index}"},
            )
        context = profile.to_nammu_context()
        self.assertEqual(3, context.count('-> {"intent":"email_search"'))


if __name__ == "__main__":
    unittest.main()

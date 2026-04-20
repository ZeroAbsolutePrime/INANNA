from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from core.governance import GovernanceLayer
from core.governance import GovernanceResult
from core.nammu import IntentClassifier
from core.session import Engine


def signal_list(value: str | None = None) -> list[str]:
    if value is None:
        return []
    return [value]


def signal_payload(analyst_signal: str | None = None) -> dict[str, list[str]]:
    return {
        "memory_signals": signal_list(),
        "identity_signals": signal_list(),
        "sensitive_signals": signal_list(),
        "tool_signals": signal_list(),
        "analyst_signals": signal_list(analyst_signal),
        "domain_hints": {},
    }


def faculties_payload(active_names: set[str] | None = None) -> dict[str, object]:
    active_names = active_names or {"crown", "analyst"}
    return {
        "faculties": {
            "crown": {
                "active": "crown" in active_names,
                "domain": "general",
                "description": "General conversation",
            },
            "analyst": {
                "active": "analyst" in active_names,
                "domain": "reasoning",
                "description": "Analysis and reasoning",
            },
            "sentinel": {
                "active": "sentinel" in active_names,
                "domain": "security",
                "description": "Security and vulnerability analysis",
            },
        }
    }


class IntentClassifierTests(unittest.TestCase):
    def test_classify_returns_named_route(self) -> None:
        with TemporaryDirectory() as temp_dir:
            faculties_path = Path(temp_dir) / "faculties.json"
            faculties_path.write_text(
                json.dumps(faculties_payload({"crown", "analyst"})),
                encoding="utf-8",
            )
            engine = Engine(model_url="http://localhost:1234/v1", model_name="local-model")
            engine._connected = True
            classifier = IntentClassifier(engine, faculties_path=faculties_path)

            with patch.object(engine, "_call_openai_compatible", return_value="ANALYST"):
                route = classifier.classify("Explain the relationship between law and governance")

        self.assertIn(route, {"crown", "analyst"})
        self.assertEqual(route, "analyst")

    def test_route_returns_governance_result(self) -> None:
        classifier = IntentClassifier(Engine())

        result = classifier.route("hello")

        self.assertIsInstance(result, GovernanceResult)
        self.assertEqual(result.decision, "allow")
        self.assertEqual(result.faculty, "crown")

    def test_classifier_loads_active_faculties_from_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            faculties_path = Path(temp_dir) / "faculties.json"
            faculties_path.write_text(
                json.dumps(faculties_payload({"crown", "analyst", "sentinel"})),
                encoding="utf-8",
            )

            classifier = IntentClassifier(Engine(), faculties_path=faculties_path)

        self.assertEqual(set(classifier.faculties.keys()), {"crown", "analyst", "sentinel"})

    def test_build_classification_prompt_includes_all_active_faculty_names(self) -> None:
        with TemporaryDirectory() as temp_dir:
            faculties_path = Path(temp_dir) / "faculties.json"
            faculties_path.write_text(
                json.dumps(faculties_payload({"crown", "analyst", "sentinel"})),
                encoding="utf-8",
            )
            classifier = IntentClassifier(Engine(), faculties_path=faculties_path)

            prompt = classifier._build_classification_prompt("Check the attack surface")

        self.assertIn("crown:", prompt)
        self.assertIn("analyst:", prompt)
        self.assertIn("sentinel:", prompt)
        self.assertIn("Input: Check the attack surface", prompt)

    def test_missing_faculties_json_falls_back_to_builtin_routes(self) -> None:
        missing_path = Path("C:/tmp/does-not-exist/faculties.json")

        classifier = IntentClassifier(Engine(), faculties_path=missing_path)

        self.assertEqual(set(classifier.faculties.keys()), {"crown", "analyst"})

    def test_unknown_faculty_name_falls_back_to_crown(self) -> None:
        with TemporaryDirectory() as temp_dir:
            faculties_path = Path(temp_dir) / "faculties.json"
            faculties_path.write_text(
                json.dumps(faculties_payload({"crown", "analyst"})),
                encoding="utf-8",
            )
            engine = Engine(model_url="http://localhost:1234/v1", model_name="local-model")
            engine._connected = True
            classifier = IntentClassifier(engine, faculties_path=faculties_path)

            with patch.object(engine, "_call_openai_compatible", return_value="ORACLE"):
                route = classifier.classify("hello")

        self.assertEqual(route, "crown")

    def test_heuristic_classify_reads_analyst_signal_from_governance_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            analyst_signal = f"analyst-{uuid4().hex}"
            config_path = Path(temp_dir) / "signals.json"
            faculties_path = Path(temp_dir) / "faculties.json"
            config_path.write_text(
                json.dumps(signal_payload(analyst_signal)),
                encoding="utf-8",
            )
            faculties_path.write_text(
                json.dumps(faculties_payload({"crown", "analyst"})),
                encoding="utf-8",
            )
            governance = GovernanceLayer(config_path=config_path)
            classifier = IntentClassifier(
                Engine(),
                governance=governance,
                faculties_path=faculties_path,
                signals_path=config_path,
            )

            self.assertEqual(
                classifier._heuristic_classify(f"{analyst_signal} sobre esto"),
                "analyst",
            )

    def test_heuristic_classify_no_longer_uses_hardcoded_analyst_list(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "signals.json"
            faculties_path = Path(temp_dir) / "faculties.json"
            config_path.write_text(
                json.dumps(signal_payload(f"analyst-{uuid4().hex}")),
                encoding="utf-8",
            )
            faculties_path.write_text(
                json.dumps(faculties_payload({"crown", "analyst"})),
                encoding="utf-8",
            )
            governance = GovernanceLayer(config_path=config_path)
            classifier = IntentClassifier(
                Engine(),
                governance=governance,
                faculties_path=faculties_path,
                signals_path=config_path,
            )

            self.assertEqual(classifier._heuristic_classify("analyse this"), "crown")
            self.assertEqual(classifier._heuristic_classify("hello"), "crown")

    def test_existing_routing_behavior_is_unchanged_when_only_crown_and_analyst_are_active(self) -> None:
        with TemporaryDirectory() as temp_dir:
            faculties_path = Path(temp_dir) / "faculties.json"
            faculties_path.write_text(
                json.dumps(faculties_payload({"crown", "analyst"})),
                encoding="utf-8",
            )
            classifier = IntentClassifier(Engine(), faculties_path=faculties_path)

            self.assertEqual(classifier._heuristic_classify("hello"), "crown")
            self.assertEqual(classifier._heuristic_classify("analyze this carefully"), "analyst")


if __name__ == "__main__":
    unittest.main()

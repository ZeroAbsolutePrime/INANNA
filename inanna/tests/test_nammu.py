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
    }


class IntentClassifierTests(unittest.TestCase):
    def test_classify_returns_named_route(self) -> None:
        engine = Engine(model_url="http://localhost:1234/v1", model_name="local-model")
        engine._connected = True
        classifier = IntentClassifier(engine)

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

    def test_heuristic_classify_reads_analyst_signal_from_governance_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            analyst_signal = f"analyst-{uuid4().hex}"
            config_path = Path(temp_dir) / "signals.json"
            config_path.write_text(
                json.dumps(signal_payload(analyst_signal)),
                encoding="utf-8",
            )
            governance = GovernanceLayer(config_path=config_path)
            classifier = IntentClassifier(Engine(), governance=governance)

            self.assertEqual(
                classifier._heuristic_classify(f"{analyst_signal} sobre esto"),
                "analyst",
            )

    def test_heuristic_classify_no_longer_uses_hardcoded_analyst_list(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "signals.json"
            config_path.write_text(
                json.dumps(signal_payload(f"analyst-{uuid4().hex}")),
                encoding="utf-8",
            )
            governance = GovernanceLayer(config_path=config_path)
            classifier = IntentClassifier(Engine(), governance=governance)

            self.assertEqual(classifier._heuristic_classify("analyse this"), "crown")
            self.assertEqual(classifier._heuristic_classify("hello"), "crown")


if __name__ == "__main__":
    unittest.main()

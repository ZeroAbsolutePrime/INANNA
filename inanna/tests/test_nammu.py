from __future__ import annotations

import unittest
from unittest.mock import patch

from core.governance import GovernanceResult
from core.nammu import IntentClassifier
from core.session import Engine


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

    def test_heuristic_classify_returns_analyst_for_analyse_this(self) -> None:
        classifier = IntentClassifier(Engine())

        self.assertEqual(classifier._heuristic_classify("analyse this"), "analyst")

    def test_heuristic_classify_returns_analyst_for_explain_why(self) -> None:
        classifier = IntentClassifier(Engine())

        self.assertEqual(classifier._heuristic_classify("explain why"), "analyst")

    def test_heuristic_classify_returns_crown_for_hello(self) -> None:
        classifier = IntentClassifier(Engine())

        self.assertEqual(classifier._heuristic_classify("hello"), "crown")

    def test_heuristic_classify_returns_crown_for_i_am_zaera(self) -> None:
        classifier = IntentClassifier(Engine())

        self.assertEqual(classifier._heuristic_classify("I am ZAERA"), "crown")


if __name__ == "__main__":
    unittest.main()

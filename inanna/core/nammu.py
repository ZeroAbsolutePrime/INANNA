from __future__ import annotations

from identity import build_nammu_prompt


CLASSIFICATION_PROMPT = build_nammu_prompt()


class IntentClassifier:
    def __init__(self, engine) -> None:
        self.engine = engine

    def classify(self, user_input: str) -> str:
        messages = [
            {"role": "system", "content": CLASSIFICATION_PROMPT},
            {"role": "user", "content": user_input},
        ]
        if not self.engine._connected:
            return self._heuristic_classify(user_input)
        try:
            result = self.engine._call_openai_compatible(messages)
            route = result.strip().upper()
            if "ANALYST" in route:
                return "analyst"
            return "crown"
        except Exception:
            return self._heuristic_classify(user_input)

    def _heuristic_classify(self, text: str) -> str:
        analyst_signals = [
            "analyse",
            "analyze",
            "explain",
            "why does",
            "how does",
            "what is the relationship",
            "compare",
            "examine",
            "breakdown",
            "structured",
            "reasoning",
            "implications",
            "technical",
        ]
        lower = text.lower()
        if any(signal in lower for signal in analyst_signals):
            return "analyst"
        return "crown"

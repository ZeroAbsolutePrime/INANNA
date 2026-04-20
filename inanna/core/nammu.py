from __future__ import annotations

import json
from pathlib import Path

from core.governance import CONFIG_PATH as GOVERNANCE_SIGNALS_PATH
from core.governance import GovernanceLayer, GovernanceResult


FACULTIES_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "faculties.json"

DEFAULT_ACTIVE_FACULTIES = {
    "crown": {"domain": "general", "description": "General conversation"},
    "analyst": {"domain": "reasoning", "description": "Analysis and reasoning"},
}


class IntentClassifier:
    def __init__(
        self,
        engine,
        governance=None,
        faculties_path: Path = FACULTIES_CONFIG_PATH,
        signals_path: Path = GOVERNANCE_SIGNALS_PATH,
    ) -> None:
        self.engine = engine
        self.governance = governance or GovernanceLayer(engine=engine)
        self.faculties = self._load_active_faculties(faculties_path)
        self.domain_hints = self._load_domain_hints(signals_path)

    def _load_active_faculties(self, path: Path) -> dict[str, dict[str, str]]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            faculties = {
                name: {
                    "domain": str(cfg.get("domain", "general")).strip() or "general",
                    "description": str(cfg.get("description", "")).strip(),
                }
                for name, cfg in data.get("faculties", {}).items()
                if isinstance(name, str)
                and isinstance(cfg, dict)
                and bool(cfg.get("active", False))
            }
            return faculties or dict(DEFAULT_ACTIVE_FACULTIES)
        except Exception:
            return dict(DEFAULT_ACTIVE_FACULTIES)

    def _load_domain_hints(self, path: Path) -> dict[str, list[str]]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

        raw_hints = data.get("domain_hints", {})
        if not isinstance(raw_hints, dict):
            return {}

        hints: dict[str, list[str]] = {}
        for domain, values in raw_hints.items():
            if not isinstance(domain, str) or not isinstance(values, list):
                continue
            hints[domain] = [value for value in values if isinstance(value, str)]
        return hints

    def _build_classification_prompt(self, user_input: str) -> str:
        faculty_lines = "\n".join(
            f"  {name}: {cfg.get('domain', 'general')} - {cfg.get('description', '')}"
            for name, cfg in self.faculties.items()
        )
        hint_lines = []
        for name, cfg in self.faculties.items():
            domain = str(cfg.get("domain", "general")).strip()
            hints = self.domain_hints.get(domain, [])
            if hints:
                hint_lines.append(
                    f"  {name} hints ({domain}): " + ", ".join(hints)
                )
        hints_block = ""
        if hint_lines:
            hints_block = "\n\nDomain hints:\n" + "\n".join(hint_lines)
        return (
            "Route this input to exactly one Faculty.\n\n"
            f"Available Faculties:\n{faculty_lines}"
            f"{hints_block}\n\n"
            f"Input: {user_input}\n\n"
            "Reply with exactly one Faculty name from the list above. "
            "No explanation. No punctuation. Just the name."
        )

    def _normalize_route(self, raw_response: str) -> str:
        lowered = str(raw_response or "").strip().lower()
        if lowered in self.faculties:
            return lowered
        token = lowered.split()[0].strip(".,:;!?()[]{}\"'") if lowered else ""
        if token in self.faculties:
            return token
        for faculty_name in self.faculties:
            if faculty_name in lowered:
                return faculty_name
        return "crown"

    def classify(self, user_input: str) -> str:
        if not self.engine._connected:
            return self._heuristic_classify(user_input)
        messages = [
            {"role": "system", "content": self._build_classification_prompt(user_input)},
        ]
        try:
            result = self.engine._call_openai_compatible(messages)
            return self._normalize_route(result)
        except Exception:
            return self._heuristic_classify(user_input)

    def route(self, user_input: str) -> GovernanceResult:
        nammu_route = self.classify(user_input)
        return self.governance.check(user_input, nammu_route)

    def _heuristic_classify(self, text: str) -> str:
        lower = text.lower()
        for name, cfg in self.faculties.items():
            if name == "crown":
                continue
            hints: list[str] = []
            if name == "analyst" and self.governance:
                hints.extend(self.governance.analyst_signals)
            domain = str(cfg.get("domain", "general")).strip()
            hints.extend(self.domain_hints.get(domain, []))
            if any(hint.lower() in lower for hint in hints):
                return name
        return "crown"

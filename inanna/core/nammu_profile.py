from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RoutingCorrection:
    """A correction NAMMU received from the operator."""

    timestamp: str = ""
    original_text: str = ""
    misrouted_to: str = ""
    correct_intent: str = ""
    correct_params: dict[str, Any] = field(default_factory=dict)

    def to_example_line(self) -> str:
        params_str = json.dumps(self.correct_params, ensure_ascii=False)
        return (
            f'"{self.original_text}" '
            f'-> {{"intent":"{self.correct_intent}","params":{params_str}}}'
        )


@dataclass
class OperatorProfile:
    """NAMMU's learned model of an operator's communication style."""

    user_id: str = ""
    display_name: str = ""
    last_updated: str = ""
    language_patterns: dict[str, list[str]] = field(default_factory=dict)
    primary_language: str = "en"
    known_shorthands: dict[str, str] = field(default_factory=dict)
    domain_weights: dict[str, float] = field(default_factory=dict)
    urgency_markers: list[str] = field(default_factory=list)
    routing_corrections: list[dict[str, Any]] = field(default_factory=list)
    recurring_topics: list[str] = field(default_factory=list)
    communication_style: str = ""
    preferred_length: str = "short"

    def to_nammu_context(self) -> str:
        lines = ["[OPERATOR CONTEXT]"]
        if self.display_name:
            lines.append(f"Operator: {self.display_name}")

        if self.language_patterns:
            lang_desc: list[str] = []
            for lang, contexts in self.language_patterns.items():
                if contexts:
                    lang_desc.append(f"{lang} ({', '.join(contexts[:2])})")
                else:
                    lang_desc.append(lang)
            lines.append(f"Languages: {' | '.join(lang_desc)}")
        elif self.primary_language:
            lines.append(f"Primary language: {self.primary_language}")

        if self.known_shorthands:
            shorthand_text = ", ".join(
                f'"{key}"={value}'
                for key, value in list(self.known_shorthands.items())[:8]
            )
            lines.append(f"Shorthands: {shorthand_text}")

        if self.communication_style:
            style = self.communication_style
            if self.preferred_length == "short":
                style = f"{style}; prefers short, direct responses"
            lines.append(f"Style: {style}")
        elif self.preferred_length == "short":
            lines.append("Style: prefers short, direct responses")

        if self.domain_weights:
            top_domains = sorted(
                self.domain_weights.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:4]
            lines.append(f"Most used: {', '.join(domain for domain, _ in top_domains)}")

        if self.routing_corrections:
            lines.append("Recent corrections:")
            for entry in self.routing_corrections[-3:]:
                try:
                    correction = RoutingCorrection(**entry)
                except TypeError:
                    continue
                lines.append(f"  {correction.to_example_line()}")

        lines.append("[END CONTEXT]")
        return "\n".join(lines)

    def record_shorthand(self, abbreviation: str, full_meaning: str) -> None:
        cleaned = str(abbreviation or "").strip().lower()
        meaning = str(full_meaning or "").strip()
        if not cleaned or not meaning:
            return
        self.known_shorthands[cleaned] = meaning
        self.last_updated = _utc_now()

    def record_correction(
        self,
        original_text: str,
        misrouted_to: str,
        correct_intent: str,
        correct_params: dict[str, Any],
    ) -> None:
        correction = RoutingCorrection(
            timestamp=_utc_now(),
            original_text=str(original_text or ""),
            misrouted_to=str(misrouted_to or ""),
            correct_intent=str(correct_intent or ""),
            correct_params=dict(correct_params or {}),
        )
        self.routing_corrections.append(asdict(correction))
        if len(self.routing_corrections) > 20:
            self.routing_corrections = self.routing_corrections[-20:]
        self.last_updated = _utc_now()

    def record_routing(self, domain: str) -> None:
        cleaned = str(domain or "").strip().lower()
        if not cleaned:
            return
        current = float(self.domain_weights.get(cleaned, 0.0) or 0.0)
        self.domain_weights[cleaned] = min(1.0, current + 0.05)
        self.last_updated = _utc_now()

    def detect_language(self, text: str) -> str:
        lowered = str(text or "").lower()
        for language in ("ca", "pt", "es", "eu"):
            markers = _LANGUAGE_MARKERS.get(language, [])
            if any(marker in lowered for marker in markers):
                return language
        return "en"

    def update_language_pattern(self, text: str, domain: str) -> None:
        language = self.detect_language(text)
        context = str(domain or "").strip().lower() or "conversation"
        self.language_patterns.setdefault(language, [])
        if context not in self.language_patterns[language]:
            self.language_patterns[language].append(context)
        counts = {
            lang: len(contexts) if contexts else 1
            for lang, contexts in self.language_patterns.items()
        }
        if counts:
            self.primary_language = max(counts, key=counts.get)
        self.last_updated = _utc_now()


def _profile_path(nammu_dir: Path, user_id: str) -> Path:
    return nammu_dir / "operator_profiles" / f"{user_id}.json"


def load_operator_profile(nammu_dir: Path, user_id: str) -> OperatorProfile:
    path = _profile_path(nammu_dir, user_id)
    if not path.exists():
        return OperatorProfile(user_id=user_id, last_updated=_utc_now())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Operator profile payload was not a dict.")
        filtered = {
            key: value
            for key, value in payload.items()
            if key in OperatorProfile.__dataclass_fields__
        }
        filtered.setdefault("user_id", user_id)
        filtered.setdefault("last_updated", _utc_now())
        return OperatorProfile(**filtered)
    except Exception:
        return OperatorProfile(user_id=user_id, last_updated=_utc_now())


def save_operator_profile(nammu_dir: Path, profile: OperatorProfile) -> None:
    path = _profile_path(nammu_dir, profile.user_id)
    try:
        profile.last_updated = _utc_now()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(profile), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def build_profile_from_user_profile(user_profile: Any, nammu_dir: Path) -> OperatorProfile:
    user_id = str(getattr(user_profile, "user_id", "") or "")
    profile = load_operator_profile(nammu_dir, user_id)
    profile.user_id = user_id
    profile.display_name = (
        str(getattr(user_profile, "preferred_name", "") or "").strip()
        or str(getattr(user_profile, "display_name", "") or "").strip()
        or user_id
    )
    profile.communication_style = str(
        getattr(user_profile, "communication_style", "") or ""
    ).strip()
    preferred_length = str(getattr(user_profile, "preferred_length", "") or "").strip()
    if preferred_length:
        profile.preferred_length = preferred_length

    languages = [
        str(item).strip()
        for item in list(getattr(user_profile, "languages", []) or [])
        if str(item).strip()
    ]
    if languages:
        profile.primary_language = languages[0]
        for language in languages:
            profile.language_patterns.setdefault(language, [])

    recurring_topics = [
        str(item).strip().lower()
        for item in list(getattr(user_profile, "recurring_topics", []) or [])
        if str(item).strip()
    ]
    if recurring_topics:
        profile.recurring_topics = list(
            dict.fromkeys(list(profile.recurring_topics) + recurring_topics)
        )[-20:]
        for topic in recurring_topics:
            profile.domain_weights.setdefault(topic, 0.3)

    return profile


_SHORTHAND_PATTERN = re.compile(r"\b([a-z]{2,4})\b")
_STOP_WORDS = {
    "the",
    "and",
    "for",
    "not",
    "but",
    "can",
    "any",
    "all",
    "my",
    "you",
    "me",
    "do",
    "it",
    "is",
    "en",
    "de",
    "la",
    "el",
    "que",
    "los",
    "las",
    "una",
    "por",
    "con",
    "he",
    "she",
    "we",
    "ok",
    "hi",
    "yes",
    "no",
    "go",
    "get",
}


_LANGUAGE_MARKERS: dict[str, list[str]] = {
    "ca": [
        "gracies",
        "gràcies",
        "avui",
        "dema",
        "demà",
        "correus",
        "correu",
        "resumeix",
        "missatge",
        "missatges",
        "tinc",
        "tens",
        "puc",
        "pots",
        "que tens",
        "calendari",
        "reunio",
        "reunió",
    ],
    "pt": [
        "obrigado",
        "obrigada",
        "bom dia",
        "boa tarde",
        "boa noite",
        "hoje",
        "amanha",
        "amanhã",
        "email",
        "mensagem",
        "tenho",
        "quero",
        "posso",
        "pode",
        "calendario",
        "resumo",
    ],
    "es": [
        "gracias",
        "hola",
        "correo",
        "hoy",
        "manana",
        "mañana",
        "urgentes",
        "urgente",
        "resumen",
        "tienes",
        "tengo",
        "mensajes",
        "mensaje",
        "calendario",
        "reunión",
        "que tengo",
        "tengo emails",
        "correos de",
        "correos",
    ],
    "eu": [
        "eskerrik asko",
        "kaixo",
        "bihar",
        "gaur",
    ],
}


def extract_potential_shorthands(
    text: str,
    known_shorthands: dict[str, str],
) -> list[str]:
    candidates: list[str] = []
    for match in _SHORTHAND_PATTERN.finditer(str(text or "").lower()):
        word = match.group(1)
        if word in known_shorthands or word in _STOP_WORDS:
            continue
        candidates.append(word)
    return candidates


def analyse_routing_log(
    routing_log: list[dict[str, Any]],
    profile: OperatorProfile,
) -> dict[str, Any]:
    """Return deterministic routing statistics for the last routing records."""

    routes = [str(entry.get("route", "")).strip() for entry in routing_log if str(entry.get("route", "")).strip()]
    domain_counts = Counter(
        route.split("_", 1)[0]
        for route in routes
        if "_" in route
    )
    return {
        "total_routings": len(routes),
        "top_domains": dict(domain_counts.most_common(5)),
        "correction_count": len(profile.routing_corrections),
        "known_shorthands": len(profile.known_shorthands),
    }

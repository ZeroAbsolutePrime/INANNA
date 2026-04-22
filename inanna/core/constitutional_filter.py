from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class FilterResult:
    blocked: bool
    category: str = ""
    reason: str = ""
    response: str = ""
    severity: str = ""
    language_detected: str = "en"

    @property
    def passed(self) -> bool:
        return not self.blocked

    def to_crown_response(self) -> str:
        if self.response:
            return self.response
        return (
            "I cannot process this request. It touches a boundary I hold firm. "
            "If this was not your intention, please rephrase."
        )


MINOR_HARM_PATTERNS = [
    r"\b(?:sexualize|sexualise|groom|molest|rape|nude|porn|explicit)\b.{0,40}\b(?:child|minor|underage|kid|niñ[oa]|menor)\b",
    r"\b(?:child|minor|underage|kid|niñ[oa]|menor)\b.{0,40}\b(?:sexualize|sexualise|groom|molest|rape|nude|porn|explicit)\b",
    r"\bcsam\b",
    r"\blolita\b(?!\s+express)",
]

TARGETED_HARM_PATTERNS = [
    r"\b(?:kill|murder|poison|assassinate|hurt|harm|attack)\b.{0,50}\b(?:zaera|matxalen|carlos|maria|john|sara)\b",
    r"\b(?:zaera|matxalen|carlos|maria|john|sara)\b.{0,50}\b(?:kill|murder|poison|assassinate|hurt|harm|attack)\b",
]

WMD_PATTERNS = [
    r"\b(?:how to|how do i|synthesize|synthesis|make|create|produce|manufacture|build|assemble)\b.{0,50}\b(?:sarin|vx\b|ricin|anthrax|botulinum|mustard gas|nerve agent)\b",
    r"\b(?:dirty bomb|radiological weapon|nuclear bomb)\b.{0,40}\b(?:build|make|create|assemble|detonate)\b",
]

GENOCIDE_PATTERNS = [
    r"\b(?:kill all|exterminate|wipe out|eradicate|ethnic cleansing|genocide)\b.{0,40}\b(?:jews?|muslims?|christians?|blacks?|whites?|arabs?|asians?|immigrants?)\b",
]

AUDIT_SUPPRESSION_PATTERNS = [
    r"\b(?:delete|remove|clear|wipe|erase|hide|falsify|forge)\b.{0,30}\b(?:audit|log|history|trail|record)s?\b",
    r"\b(?:don't log|do not log|without logging|skip the log|hide this from the audit)\b",
]

IMPERSONATION_DECEPTION_PATTERNS = [
    r"\b(?:impersonate|pretend to be|pose as)\b.{0,40}\b(?:zaera|matxalen|carlos|maria|john|sara)\b.{0,40}\b(?:to deceive|to trick|to scam|to fool)\b",
]

HATE_SPEECH_PATTERNS = [
    r"\b(?:nigger|faggot|kike|spic|chink|tranny)\b",
    r"\b(?:vermin|cockroaches?|subhuman|animals)\b.{0,30}\b(?:they|them|those people|immigrants|jews?|muslims?|blacks?|gays?)\b",
]

AUTHORITY_IMPERSONATION_PATTERNS = [
    r"\b(?:i am|i'm)\b.{0,25}\b(?:anthropic|zaera|the guardian|your creator|your owner)\b",
    r"\b(?:emergency override|admin override|system override|god mode|debug mode)\b",
    r"\b(?:ignore|forget|bypass|override)\b.{0,30}\b(?:your laws|your rules|your constitution|your ethics|governance)\b",
]

SELF_HARMING_OPERATOR_INTERESTS_PATTERNS = [
    r"\b(?:delete|wipe|erase|remove)\b.{0,40}\ball my files\b.{0,30}\bwithout telling me\b",
]

THIRD_PARTY_DECEPTION_PATTERNS = [
    r"\b(?:deceive|trick|scam|mislead|defraud)\b.{0,40}\b(?:them|him|her|my boss|my bank|a customer|third part(?:y|ies))\b",
]

ABSOLUTE_PATTERNS = {
    "minor_harm": MINOR_HARM_PATTERNS,
    "targeted_harm": TARGETED_HARM_PATTERNS,
    "wmd_synthesis": WMD_PATTERNS,
    "genocide_incitement": GENOCIDE_PATTERNS,
    "audit_suppression": AUDIT_SUPPRESSION_PATTERNS,
    "impersonation_deception": IMPERSONATION_DECEPTION_PATTERNS,
}

ETHICS_PATTERNS = {
    "hate_speech": HATE_SPEECH_PATTERNS,
    "authority_impersonation": AUTHORITY_IMPERSONATION_PATTERNS,
    "operator_interest_harm": SELF_HARMING_OPERATOR_INTERESTS_PATTERNS,
    "third_party_deception": THIRD_PARTY_DECEPTION_PATTERNS,
}

RESPONSE_TEMPLATES = {
    "minor_harm": (
        "This request touches an absolute boundary I will not cross. "
        "I cannot generate content of this nature under any circumstance."
    ),
    "targeted_harm": (
        "I cannot help harm a specific person. "
        "If there is a real conflict or safety issue, I can help you think through a safer response."
    ),
    "wmd_synthesis": (
        "I cannot provide synthesis or construction instructions for weapons capable of mass harm. "
        "This is an unconditional boundary."
    ),
    "genocide_incitement": (
        "I cannot generate content that calls for extermination or violence against groups of people. "
        "This is an unconditional boundary."
    ),
    "audit_suppression": (
        "The audit trail exists to protect you and the system. "
        "I cannot suppress, hide, or falsify it."
    ),
    "impersonation_deception": (
        "I cannot help impersonate a real person in order to deceive others."
    ),
    "hate_speech": (
        "This language causes harm. I won't generate content built around it. "
        "If there is another need underneath it, you can ask plainly."
    ),
    "authority_impersonation": (
        "Claimed authority does not override my governance. "
        "If you have a genuine request, I can still help within the boundary."
    ),
    "operator_interest_harm": (
        "I won't help conceal consequential harm from you. "
        "If you want to review a risky action safely, I can help with that."
    ),
    "third_party_deception": (
        "I cannot help deceive third parties. "
        "If you want help communicating honestly and effectively, I can do that."
    ),
}


class ConstitutionalFilter:
    """The outermost ethical boundary of INANNA NYX."""

    def __init__(self, engine=None) -> None:
        self._engine = engine
        self._compiled_absolute = {
            category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for category, patterns in ABSOLUTE_PATTERNS.items()
        }
        self._compiled_ethics = {
            category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for category, patterns in ETHICS_PATTERNS.items()
        }

    def check(self, text: str, operator_profile=None) -> FilterResult:
        del operator_profile
        try:
            cleaned = str(text or "").strip()
            if not cleaned:
                return FilterResult(blocked=False)

            for category, patterns in self._compiled_absolute.items():
                for pattern in patterns:
                    if pattern.search(cleaned):
                        return FilterResult(
                            blocked=True,
                            category=category,
                            severity="absolute",
                            reason=f"Absolute prohibition triggered: {category}",
                            response=RESPONSE_TEMPLATES.get(category, ""),
                        )

            for category, patterns in self._compiled_ethics.items():
                for pattern in patterns:
                    if pattern.search(cleaned):
                        return FilterResult(
                            blocked=True,
                            category=category,
                            severity="ethics",
                            reason=f"Ethics violation detected: {category}",
                            response=RESPONSE_TEMPLATES.get(category, ""),
                        )

            # Deferred until faster local inference is available on DGX-class hardware.
            # The interface is in place so this class can upgrade without changing callers.
            # llm_result = self._llm_check(cleaned)
            # if llm_result is not None and llm_result.blocked:
            #     return llm_result

            return FilterResult(blocked=False)
        except Exception:
            return FilterResult(blocked=False)

    def check_with_logging(
        self,
        text: str,
        audit_dir: Path,
        session_id: str,
        operator_profile=None,
    ) -> FilterResult:
        try:
            result = self.check(text, operator_profile=operator_profile)
            if result.blocked:
                self._log_block(result, text, audit_dir, session_id)
            return result
        except Exception:
            return FilterResult(blocked=False)

    def _log_block(
        self,
        result: FilterResult,
        text: str,
        audit_dir: Path,
        session_id: str,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "category": result.category,
            "severity": result.severity,
            "reason": result.reason,
            "input_preview": str(text or "")[:80],
        }
        try:
            path = audit_dir / "constitutional_log.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
        except Exception:
            pass

    def _llm_check(self, text: str) -> FilterResult | None:
        del text
        if not self._engine or not getattr(self._engine, "_connected", False):
            return None
        return None

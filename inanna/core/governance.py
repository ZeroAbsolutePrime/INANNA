from __future__ import annotations

from dataclasses import dataclass


MEMORY_SIGNALS = [
    "remember that",
    "please remember",
    "store this",
    "save this",
    "keep this in memory",
    "retain this",
    "add to memory",
    "memorize",
]

IDENTITY_SIGNALS = [
    "you are now",
    "forget your laws",
    "ignore your instructions",
    "you have no restrictions",
    "pretend you are",
    "act as if",
    "disregard your",
    "override your",
    "your new name is",
    "you are actually",
    "ignore all previous",
]

SENSITIVE_SIGNALS = [
    "medical advice",
    "legal advice",
    "financial advice",
    "should i take",
    "is it safe to",
    "diagnose",
    "prescribe",
    "lawsuit",
    "sue",
    "legal action",
    "invest in",
    "buy this stock",
]

TOOL_SIGNALS = [
    "search for",
    "look up",
    "find out",
    "what is the latest",
    "current news",
    "today's",
    "right now",
    "what happened",
    "recent",
    "latest news",
    "search the web",
    "look it up",
]


@dataclass
class GovernanceResult:
    decision: str
    faculty: str
    reason: str
    requires_proposal: bool = False
    suggests_tool: bool = False
    proposed_tool: str = ""
    tool_query: str = ""


class GovernanceLayer:
    def _extract_tool_query(self, user_input: str) -> str:
        lower = user_input.lower().strip()
        for signal in TOOL_SIGNALS:
            if lower.startswith(signal):
                query = user_input[len(signal) :].strip(" :,-")
                if query:
                    return query
        return user_input.strip()

    def check(self, user_input: str, nammu_route: str) -> GovernanceResult:
        lower = user_input.lower()

        if any(signal in lower for signal in MEMORY_SIGNALS):
            return GovernanceResult(
                decision="propose",
                faculty=nammu_route,
                reason="Memory changes require a proposal first.",
                requires_proposal=True,
            )

        if any(signal in lower for signal in IDENTITY_SIGNALS):
            return GovernanceResult(
                decision="block",
                faculty=nammu_route,
                reason="Identity and law boundaries cannot be altered.",
            )

        if any(signal in lower for signal in SENSITIVE_SIGNALS):
            return GovernanceResult(
                decision="redirect",
                faculty="analyst",
                reason="Sensitive topic redirected to Analyst Faculty.",
            )

        if any(signal in lower for signal in TOOL_SIGNALS):
            return GovernanceResult(
                decision="allow",
                faculty=nammu_route,
                reason="",
                suggests_tool=True,
                proposed_tool="web_search",
                tool_query=self._extract_tool_query(user_input),
            )

        return GovernanceResult(
            decision="allow",
            faculty=nammu_route,
            reason="",
        )

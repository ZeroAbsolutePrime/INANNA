from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class OrchestrationStep:
    faculty: str
    purpose: str
    input_from: str
    output_to: str


@dataclass
class OrchestrationPlan:
    steps: list[OrchestrationStep]
    trigger_pattern: str
    requires_approval: bool = True

    def chain_label(self, separator: str = " -> ") -> str:
        return separator.join(step.faculty.upper() for step in self.steps)

    def describe_steps(self) -> str:
        clauses = [f"{step.faculty.upper()} will {step.purpose}" for step in self.steps]
        return ", ".join(clauses) + "."

    def to_payload(self) -> dict[str, Any]:
        return {
            "trigger_pattern": self.trigger_pattern,
            "requires_approval": self.requires_approval,
            "steps": [asdict(step) for step in self.steps],
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "OrchestrationPlan":
        steps = [
            OrchestrationStep(
                faculty=str(step.get("faculty", "")).strip(),
                purpose=str(step.get("purpose", "")).strip(),
                input_from=str(step.get("input_from", "")).strip(),
                output_to=str(step.get("output_to", "")).strip(),
            )
            for step in payload.get("steps", [])
            if isinstance(step, dict)
        ]
        return cls(
            steps=steps,
            trigger_pattern=str(payload.get("trigger_pattern", "")).strip(),
            requires_approval=bool(payload.get("requires_approval", True)),
        )


class OrchestrationEngine:
    def __init__(self, faculties_path: Path) -> None:
        self.faculties_path = faculties_path
        self._plans = self._load_plans()

    def _load_plans(self) -> list[OrchestrationPlan]:
        return [
            OrchestrationPlan(
                trigger_pattern=(
                    r"security.*explain|"
                    r"analy[sz]e.*security.*simple|"
                    r"vulnerabilit.*plain|"
                    r"security.*non.*technical"
                ),
                steps=[
                    OrchestrationStep("sentinel", "analyze", "user", "crown"),
                    OrchestrationStep("crown", "synthesize", "sentinel", "user"),
                ],
                requires_approval=True,
            ),
        ]

    def detect_orchestration(self, user_input: str) -> OrchestrationPlan | None:
        for plan in self._plans:
            if re.search(plan.trigger_pattern, user_input, re.IGNORECASE):
                return plan
        return None

    def format_synthesis_prompt(
        self,
        user_input: str,
        previous_output: str,
        step: OrchestrationStep,
    ) -> str:
        if step.purpose == "synthesize":
            return (
                f"The user asked: {user_input}\n\n"
                f"The {step.input_from.upper()} Faculty analyzed this and found:\n"
                f"{previous_output}\n\n"
                "Please synthesize these findings into a clear, accessible response "
                "for the user. Preserve the important insights while making them "
                "understandable. Do not add information not present in the analysis."
            )
        return user_input

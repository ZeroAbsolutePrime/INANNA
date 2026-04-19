from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class GuardianAlert:
    level: str
    code: str
    message: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class GuardianFaculty:
    def inspect(
        self,
        session_id: str,
        memory_count: int,
        pending_proposals: int,
        routing_log: list[dict[str, Any]],
        governance_blocks: int,
        tool_executions: int,
    ) -> list[GuardianAlert]:
        del session_id
        del routing_log

        alerts: list[GuardianAlert] = []

        if pending_proposals >= 5:
            alerts.append(
                GuardianAlert(
                    level="warn",
                    code="PENDING_PROPOSAL_ACCUMULATION",
                    message=(
                        f"{pending_proposals} proposals are pending approval. "
                        "Consider reviewing and resolving them."
                    ),
                )
            )

        if governance_blocks >= 3:
            alerts.append(
                GuardianAlert(
                    level="warn",
                    code="REPEATED_GOVERNANCE_BLOCKS",
                    message=(
                        f"{governance_blocks} inputs were blocked by governance "
                        "in this session. This may indicate boundary testing."
                    ),
                )
            )

        if memory_count >= 10:
            alerts.append(
                GuardianAlert(
                    level="info",
                    code="MEMORY_GROWTH",
                    message=(
                        f"{memory_count} approved memory records exist. "
                        "Consider reviewing older records for relevance."
                    ),
                )
            )

        if tool_executions >= 5:
            alerts.append(
                GuardianAlert(
                    level="info",
                    code="TOOL_USE_FREQUENCY",
                    message=(
                        f"{tool_executions} tool executions in this session. "
                        "Tool use is governed and visible."
                    ),
                )
            )

        if not alerts:
            alerts.append(
                GuardianAlert(
                    level="info",
                    code="SYSTEM_HEALTHY",
                    message="All governance indicators within normal bounds.",
                )
            )

        return alerts

    def format_report(self, alerts: list[GuardianAlert]) -> str:
        lines = [f"Guardian Report ({len(alerts)} alert(s)):"]
        for alert in alerts:
            level_marker = {
                "info": "  [info]    ",
                "warn": "  [warn]    ",
                "critical": "  [critical]",
            }.get(alert.level, "  [?]       ")
            lines.append(f"{level_marker} {alert.code}")
            lines.append(f"             {alert.message}")
        return "\n".join(lines)

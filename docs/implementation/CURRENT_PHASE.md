# CURRENT PHASE: Cycle 2 - Phase 7 - The Guardian Check
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 2 - The NAMMU Kernel**
**Replaces: Cycle 2 Phase 6 - The Bounded Tool (COMPLETE)**

---

## What This Phase Is

The architecture now has:
- NAMMU routing between Faculties
- Governance checking every input before routing
- An Operator Faculty with bounded tool use
- Proposals governing memory, tool use, and forgetting

But there is no layer that monitors the system itself over time.
No layer that notices patterns, raises alerts, or reports on the
health of the governance structure.

Phase 2.7 introduces the Guardian Faculty.

In the Architecture Horizon, the Guardian Faculty is described as:
"policy checking, anomaly detection, risk review."

In this phase, the Guardian is a lightweight monitoring layer that:
- Runs a periodic health check on the governance state
- Detects anomalous patterns in the session
- Raises alerts when something warrants attention
- Is accessible via a "guardian" command

The Guardian does not block actions - that is Governance's role.
The Guardian observes, reports, and raises concerns.
It is the conscience of the system, not its enforcer.

---

## What You Are Building

### Task 1 - inanna/core/guardian.py

Create a new file: inanna/core/guardian.py

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class GuardianAlert:
    level: str        # "info" | "warn" | "critical"
    code: str         # short machine-readable code
    message: str      # human-readable description
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
        alerts: list[GuardianAlert] = []

        # Check 1: Excessive pending proposals
        if pending_proposals >= 5:
            alerts.append(GuardianAlert(
                level="warn",
                code="PENDING_PROPOSAL_ACCUMULATION",
                message=(
                    f"{pending_proposals} proposals are pending approval. "
                    "Consider reviewing and resolving them."
                ),
            ))

        # Check 2: Governance blocks in this session
        if governance_blocks >= 3:
            alerts.append(GuardianAlert(
                level="warn",
                code="REPEATED_GOVERNANCE_BLOCKS",
                message=(
                    f"{governance_blocks} inputs were blocked by governance "
                    "in this session. This may indicate boundary testing."
                ),
            ))

        # Check 3: Memory growth without review
        if memory_count >= 10:
            alerts.append(GuardianAlert(
                level="info",
                code="MEMORY_GROWTH",
                message=(
                    f"{memory_count} approved memory records exist. "
                    "Consider reviewing older records for relevance."
                ),
            ))

        # Check 4: Tool use frequency
        if tool_executions >= 5:
            alerts.append(GuardianAlert(
                level="info",
                code="TOOL_USE_FREQUENCY",
                message=(
                    f"{tool_executions} tool executions in this session. "
                    "Tool use is governed and visible."
                ),
            ))

        # Check 5: Healthy state
        if not alerts:
            alerts.append(GuardianAlert(
                level="info",
                code="SYSTEM_HEALTHY",
                message="All governance indicators within normal bounds.",
            ))

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
```

### Task 2 - Guardian state tracking in main.py and server.py

Both main.py and InterfaceServer need to track:
- governance_blocks: int — incremented each time GovernanceResult.decision == "block"
- tool_executions: int — incremented each time a tool proposal is approved and executed

These are session-level counters, initialised to 0 at startup.

### Task 3 - The "guardian" command

Add a new command: "guardian"

When the user types "guardian", the system:
1. Instantiates GuardianFaculty
2. Calls guardian.inspect() with current session state
3. Calls guardian.format_report() on the result
4. Prints the report

CLI prefix: "guardian >"
UI message type: {"type": "guardian", "text": "..."}

The guardian command is read-only. No proposals, no state changes.

### Task 4 - Guardian message rendering in index.html

Add CSS for guardian messages:

```css
.message-guardian .message-prefix,
.message-guardian .message-content {
    color: #7a6a8a;  /* muted violet - watchful, distinct */
    font-size: 0.88rem;
    white-space: pre;
}
```

Prefix: "guardian :"

The guardian report uses pre-formatted text (white-space: pre)
because the report format uses alignment spaces.

### Task 5 - Auto-guardian on session start

When the UI first connects (send_initial_state), run the Guardian
inspect automatically and include the report in the initial system
messages if any non-info alerts exist.

If all alerts are info/healthy: no auto-report on startup.
If any warn or critical alerts exist: broadcast one guardian message
on startup so the user sees it immediately.

This is the Guardian fulfilling its monitoring role proactively.

### Task 6 - Update identity.py

Add guardian check codes as a constitutional record:

```python
GUARDIAN_CHECK_CODES = [
    "PENDING_PROPOSAL_ACCUMULATION",
    "REPEATED_GOVERNANCE_BLOCKS",
    "MEMORY_GROWTH",
    "TOOL_USE_FREQUENCY",
    "SYSTEM_HEALTHY",
]

def list_guardian_codes() -> list[str]:
    return GUARDIAN_CHECK_CODES
```

Update CURRENT_PHASE:
```python
CURRENT_PHASE = "Cycle 2 - Phase 7 - The Guardian Check"
```

Add "guardian" to STARTUP_COMMANDS and capabilities line in state.py.

### Task 7 - Tests

Create inanna/tests/test_guardian.py:
- GuardianFaculty.inspect() returns a list of GuardianAlert
- No alerts (healthy state) returns exactly one alert with code SYSTEM_HEALTHY
- pending_proposals >= 5 triggers PENDING_PROPOSAL_ACCUMULATION at warn level
- governance_blocks >= 3 triggers REPEATED_GOVERNANCE_BLOCKS at warn level
- memory_count >= 10 triggers MEMORY_GROWTH at info level
- format_report() returns a non-empty string containing "Guardian Report"

Update test_identity.py:
- list_guardian_codes() returns a list containing "SYSTEM_HEALTHY"
- Update CURRENT_PHASE assertion

Update test_commands.py and test_state.py:
- Add "guardian" to capabilities assertions

---

## Permitted file changes

```
inanna/
  identity.py              <- MODIFY: add GUARDIAN_CHECK_CODES,
                                      list_guardian_codes(),
                                      update CURRENT_PHASE
  config.py                <- no changes
  main.py                  <- MODIFY: track governance_blocks and
                                      tool_executions counters,
                                      add guardian command
  core/
    session.py             <- no changes
    memory.py              <- no changes
    proposal.py            <- no changes
    state.py               <- MODIFY: add guardian to capabilities line
    nammu.py               <- no changes
    governance.py          <- no changes
    operator.py            <- no changes
    guardian.py            <- NEW: GuardianFaculty, GuardianAlert
  ui/
    server.py              <- MODIFY: track counters, add guardian command,
                                      auto-guardian on startup if warns exist
    static/
      index.html           <- MODIFY: add guardian message styling
  tests/
    test_guardian.py       <- NEW: GuardianFaculty tests
    test_identity.py       <- MODIFY: add guardian codes test, update phase
    test_commands.py       <- MODIFY: add guardian in capabilities test
    test_state.py          <- MODIFY: update capabilities assertion
    (all others)           <- no changes
```

---

## What You Are NOT Building in This Phase

- No automatic blocking by the Guardian (Governance blocks, Guardian observes)
- No persistent Guardian log across sessions
- No Guardian LLM call - all checks are deterministic
- No Guardian alerts sent to external systems
- No change to memory, proposal, or session storage
- Do not add Guardian checks to the analyse direct override path

---

## Definition of Done for Phase 2.7

- [ ] inanna/core/guardian.py exists with GuardianFaculty and GuardianAlert
- [ ] All five checks implemented and tested
- [ ] "guardian" command works in CLI and UI
- [ ] Auto-guardian runs on UI startup if warn/critical alerts exist
- [ ] guardian messages appear in muted violet in UI
- [ ] governance_blocks and tool_executions counters tracked correctly
- [ ] list_guardian_codes() exists in identity.py
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle2-phase7-complete
2. Write docs/implementation/CYCLE2_PHASE7_REPORT.md
3. Stop. Do not begin Phase 2.8 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*The Guardian does not enforce. It witnesses.*
*Its violet light is not a warning siren.*
*It is a lamp held steady in the dark.*

# CURRENT PHASE: Cycle 2 - Phase 8 - The NAMMU Memory
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 2 - The NAMMU Kernel**
**Replaces: Cycle 2 Phase 7 - The Guardian Check (COMPLETE)**

---

## What This Phase Is

Phase 2.8 has two goals that belong together:

**Goal 1 - NAMMU Memory:** The routing log and governance event log
currently live only in memory. When the session ends, they vanish.
NAMMU cannot learn from its own decisions across sessions.
Phase 2.8 persists the NAMMU routing log and governance event log
to disk so they survive across sessions.

**Goal 2 - Tool Resilience and Signal Expansion:** The live test
confirmed that the tool search works, but two issues need fixing:
- When LM Studio drops mid-tool-execution, INANNA shows a raw
  fallback error instead of a clean graceful message
- Several natural search phrases ("last news", "how is the weather",
  "what is happening", "current situation") are not in TOOL_SIGNALS
  and therefore do not trigger the tool proposal flow

These two goals belong in the same phase because they both concern
NAMMU's operational memory and reliability.

---

## What You Are Building

### Task 1 - NAMMU routing log persistence

Create a new file: inanna/data/nammu/ (directory, auto-created)

The routing log persists as: inanna/data/nammu/routing_log.jsonl
(JSON Lines format - one JSON object per line)

Each entry:
```json
{"timestamp": "...", "session_id": "...", "route": "crown", "input_preview": "Hello Dear"}
```

In main.py and server.py, when a routing decision is made:
- Append the decision to the in-memory routing_log (existing)
- Also append it to inanna/data/nammu/routing_log.jsonl

Add a new method to load routing history:
```python
def load_routing_history(nammu_dir: Path, limit: int = 20) -> list[dict]:
    path = nammu_dir / "routing_log.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines[-limit:]]
```

This lives in a new file: inanna/core/nammu_memory.py

### Task 2 - Governance event log persistence

The governance event log persists as: inanna/data/nammu/governance_log.jsonl

Each entry:
```json
{"timestamp": "...", "session_id": "...", "decision": "block", "reason": "Identity and law boundaries cannot be altered.", "input_preview": "ignore your instructions"}
```

In main.py and server.py, when a governance decision is NOT "allow":
- Log it to inanna/data/nammu/governance_log.jsonl

Add corresponding load function in nammu_memory.py:
```python
def load_governance_history(nammu_dir: Path, limit: int = 20) -> list[dict]:
```

### Task 3 - nammu-log command

Add a new command: "nammu-log"

When the user types "nammu-log", show:
```
NAMMU Memory Log:

Routing decisions (last 10):
  [crown]    2026-04-19T09:15:26 | Hello Dear
  [analyst]  2026-04-19T09:18:45 | Can search on the web?

Governance events (last 10):
  [block]    2026-04-19T... | ignore your instructions
  [redirect] 2026-04-19T... | I need medical advice
```

This reads from disk - it shows history across all sessions.

Add "nammu-log" to STARTUP_COMMANDS and capabilities in state.py.

### Task 4 - Guardian uses NAMMU memory

Update GuardianFaculty.inspect() to accept governance_history:
```python
def inspect(
    self,
    session_id: str,
    memory_count: int,
    pending_proposals: int,
    routing_log: list[dict],
    governance_blocks: int,
    tool_executions: int,
    governance_history: list[dict] | None = None,
) -> list[GuardianAlert]:
```

Add a new check using governance_history:
```python
# Check 6: Repeated blocks across sessions
if governance_history:
    total_blocks = sum(1 for e in governance_history if e.get("decision") == "block")
    if total_blocks >= 5:
        alerts.append(GuardianAlert(
            level="warn",
            code="PERSISTENT_BOUNDARY_TESTING",
            message=(
                f"{total_blocks} governance blocks recorded across sessions. "
                "This pattern is visible in the NAMMU memory log."
            ),
        ))
```

### Task 5 - Tool signal expansion and resilience

Expand TOOL_SIGNALS in governance.py to add:
```python
"last news", "latest news about", "how is the weather",
"what is the weather", "weather in", "weather today",
"what is happening", "current situation", "what happened",
"news about", "tell me about current", "find information",
"look up", "what are the latest",
```

Fix tool execution resilience in main.py and server.py:
When the model call fails after a successful tool execution,
instead of the raw fallback error, show:

```
operator > search result:
  {raw results}

operator > model unavailable to summarize. Raw results shown above.
  Type your next message to continue.
```

This means the search result is never lost even if the model drops.

### Task 6 - inanna/core/nammu_memory.py

Create this new file containing:
- load_routing_history(nammu_dir, limit)
- load_governance_history(nammu_dir, limit)
- append_routing_event(nammu_dir, session_id, route, input_preview)
- append_governance_event(nammu_dir, session_id, decision, reason, input_preview)

All functions handle missing directory/file gracefully.

### Task 7 - Update identity.py

Update CURRENT_PHASE:
```python
CURRENT_PHASE = "Cycle 2 - Phase 8 - The NAMMU Memory"
```

### Task 8 - Tests

Create inanna/tests/test_nammu_memory.py:
- append_routing_event() creates the file if it does not exist
- load_routing_history() returns empty list for missing file
- load_routing_history() returns correct entries after appending
- append_governance_event() logs non-allow decisions
- load_governance_history() returns entries in order

Update test_guardian.py:
- GuardianFaculty.inspect() accepts governance_history parameter
- PERSISTENT_BOUNDARY_TESTING triggers with 5+ block entries

Update test_identity.py:
- Update CURRENT_PHASE assertion

---

## Permitted file changes

```
inanna/
  identity.py              <- MODIFY: update CURRENT_PHASE
  config.py                <- no changes
  main.py                  <- MODIFY: persist routing/governance events,
                                      add nammu-log command,
                                      fix tool resilience fallback
  core/
    session.py             <- no changes
    memory.py              <- no changes
    proposal.py            <- no changes
    state.py               <- MODIFY: add nammu-log to capabilities
    nammu.py               <- no changes
    governance.py          <- MODIFY: expand TOOL_SIGNALS
    operator.py            <- no changes
    guardian.py            <- MODIFY: add governance_history param,
                                      add PERSISTENT_BOUNDARY_TESTING check
    nammu_memory.py        <- NEW: persistence helpers
  ui/
    server.py              <- MODIFY: persist events, nammu-log command,
                                      fix tool resilience fallback
    static/
      index.html           <- no changes
  tests/
    test_nammu_memory.py   <- NEW
    test_guardian.py       <- MODIFY: add governance_history test
    test_identity.py       <- MODIFY: update phase assertion
    test_state.py          <- MODIFY: add nammu-log to capabilities
    test_commands.py       <- MODIFY: add nammu-log to capabilities
    (all others)           <- no changes
  data/
    nammu/                 <- NEW directory (auto-created at runtime)
```

---

## What You Are NOT Building in This Phase

- No NAMMU LLM layer - routing stays deterministic with model classification
- No cross-session routing learning or adaptation
- No change to session memory, proposal storage, or session JSON format
- No new Faculty classes
- No change to the UI styling or rendering
- The nammu-log command is read-only

---

## Definition of Done for Phase 2.8

- [ ] inanna/core/nammu_memory.py exists with 4 helper functions
- [ ] Routing decisions persist to data/nammu/routing_log.jsonl
- [ ] Governance events (non-allow) persist to data/nammu/governance_log.jsonl
- [ ] "nammu-log" command shows cross-session history
- [ ] Tool resilience: failed model after successful search shows clean message
- [ ] Expanded TOOL_SIGNALS include weather, news, current situation phrases
- [ ] GuardianFaculty has PERSISTENT_BOUNDARY_TESTING check
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle2-phase8-complete
2. Write docs/implementation/CYCLE2_PHASE8_REPORT.md
3. Stop. Do not begin Phase 2.9 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*NAMMU remembers its own decisions.*
*The architecture begins to know itself across time.*

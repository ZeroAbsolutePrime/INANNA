# CURRENT PHASE: Cycle 9 - Phase 9.5 - The Feedback Loop
**Status: ACTIVE**
**Authorized by: INANNA NAMMU (Guardian) + Claude (Command Center)**
**Date: 2026-04-22**
**Cycle: 9 — NAMMU Reborn: The Living Interpreter**
**Replaces: Cycle 9 Phase 9.4 - The Comprehension Layer (COMPLETE)**

---

## MANDATORY READING — in this exact order

1. docs/nammu_vision.md              ← Dimension I: The Feedback Loop
2. docs/cycle9_master_plan.md
3. docs/implementation/CURRENT_PHASE.md (this file)
4. CODEX_DOCTRINE.md
5. ABSOLUTE_PROTOCOL.md

---

## What Already Exists (audited before writing this phase)

From Phase 9.2, OperatorProfile has:
  record_correction(original_text, misrouted_to,
                    correct_intent, correct_params)
  routing_corrections: list[dict] — stores up to 20 corrections
  to_nammu_context() — includes corrections as few-shot examples

From Phase 9.2, server.py has:
  nammu-correct command (records correction manually)
  nammu-learn command (records shorthands manually)
  profile saved after every tool execution

The routing_log.jsonl records every routing decision.
724 tests passing.

---

## What Is Missing

The correction mechanism exists but is PASSIVE.
The operator must explicitly type `nammu-correct` to teach NAMMU.

Phase 9.5 makes the feedback loop ACTIVE:

1. NAMMU detects when it routed incorrectly
   (operator rephrases immediately after, asks something related,
   or explicitly says "no, I meant...")

2. NAMMU asks for confirmation before recording a correction

3. Every correction immediately enriches the operator profile
   for the NEXT routing call — the profile is used live

4. The routing log is analysed periodically to surface patterns:
   "You've corrected this 3 times — shall I learn this permanently?"

---

## What Phase 9.5 Builds

### The Three Feedback Mechanisms

**Mechanism 1 — Explicit correction (already exists, enhance)**
`nammu-correct <intent> [query]`
Already records to OperatorProfile.routing_corrections.
Enhancement: parse query parameter from the command.

**Mechanism 2 — Implicit misroute detection**
After NAMMU routes to a tool and the operator immediately says
something like "no", "that's wrong", "I meant X", "not what I asked"
— NAMMU detects this, records the session context, and asks:
"Should I remember that '[original phrase]' means [X]?"

**Mechanism 3 — Pattern surfacing**
After 5+ corrections in a session, NAMMU surfaces a summary:
"I've been corrected 5 times today. The most common pattern:
[X] → [Y]. Shall I add this as a permanent learning?"

---

## What You Are Building

### Task 1 — Enhance nammu-correct command in server.py

Current: `nammu-correct <intent>`
Enhanced: `nammu-correct <intent> [query_or_params]`

```python
elif command_name == "nammu-correct":
    parts = raw_cmd.strip().split(None, 2)
    if len(parts) >= 2:
        correct_intent = parts[1].strip()
        # Optional: extract query/params from parts[2]
        correct_params = {}
        if len(parts) == 3:
            param_str = parts[2].strip()
            # Try to parse as JSON first
            try:
                correct_params = json.loads(param_str)
            except (json.JSONDecodeError, ValueError):
                # Treat as a plain query string
                correct_params = {"query": param_str}

        original = getattr(self, '_last_nammu_input', '') or ""
        misrouted = getattr(self, '_last_nammu_route', 'unknown')

        self.nammu_profile.record_correction(
            original_text=original,
            misrouted_to=misrouted,
            correct_intent=correct_intent,
            correct_params=correct_params,
        )
        save_operator_profile(self.nammu_dir, self.nammu_profile)

        # Confirmation message
        example = RoutingCorrection(
            original_text=original,
            correct_intent=correct_intent,
            correct_params=correct_params,
        ).to_example_line()
        await self.broadcast({
            "type": "system",
            "text": (
                f"nammu > correction recorded\n"
                f"  learned: {example}\n"
                f"  total corrections: {len(self.nammu_profile.routing_corrections)}"
            )
        })
```

### Task 2 — Track last routing input/result in server.py

Add two instance variables that store the last NAMMU input
and route so nammu-correct can reference them:

```python
# In InterfaceServer.__init__:
self._last_nammu_input: str = ""
self._last_nammu_route: str = ""

# In _run_routed_turn() after nammu_first_routing:
self._last_nammu_input = text
if tool_request:
    self._last_nammu_route = str(tool_request.get("tool", ""))
else:
    self._last_nammu_route = "conversation"
```

### Task 3 — Implicit misroute detection

Add misroute signal detection in _run_routed_turn().
When CROWN responds to a message, check if the NEXT message
contains misroute signals:

```python
MISROUTE_SIGNALS = [
    "no that", "not what i", "i meant", "wrong",
    "that's not", "thats not", "not right",
    "no no", "wait no", "actually i",
    "no eso no", "no era eso",  # Spanish
    "no no", "equivocado",
]

def _detect_misroute(self, text: str) -> bool:
    """Returns True if this message suggests the previous route was wrong."""
    lower = text.lower().strip()
    return any(sig in lower for sig in MISROUTE_SIGNALS)
```

When misroute is detected:
```python
if self._detect_misroute(text) and self._last_nammu_input:
    # Surface a gentle correction prompt
    await self.broadcast({
        "type": "system",
        "text": (
            f"nammu > did I misroute '{self._last_nammu_input[:40]}'?\n"
            f"  type: nammu-correct <intent> [query] to teach me\n"
            f"  or continue — I'll try to understand your new message"
        )
    })
```

This is INFORMATIONAL only — does not block the new message.

### Task 4 — Pattern surfacing (session-level)

Add a correction counter and surface a summary
after every 5th correction in a session:

```python
# In InterfaceServer.__init__:
self._session_correction_count: int = 0

# After recording any correction:
self._session_correction_count += 1
if self._session_correction_count % 5 == 0:
    # Surface pattern summary
    recent = self.nammu_profile.routing_corrections[-5:]
    if recent:
        patterns = [
            f"  '{c['original_text'][:30]}' → {c['correct_intent']}"
            for c in recent
        ]
        await self.broadcast({
            "type": "system",
            "text": (
                f"nammu > {self._session_correction_count} corrections this session\n"
                + "\n".join(patterns) + "\n"
                f"  These are saved and will improve future routing."
            )
        })
```

### Task 5 — Routing log analysis utility

Add a function to nammu_profile.py that analyses the
routing log and surfaces patterns:

```python
def analyse_routing_log(
    routing_log: list[dict],
    profile: OperatorProfile,
) -> dict:
    """
    Analyse routing history to surface patterns.
    Returns a summary of routing statistics.
    No LLM. Deterministic.
    """
    from collections import Counter
    routes = [e.get("route", "") for e in routing_log if e.get("route")]
    domain_counts = Counter(
        r.split("_")[0] for r in routes if "_" in r
    )
    total = len(routes)
    return {
        "total_routings": total,
        "top_domains": dict(domain_counts.most_common(5)),
        "correction_count": len(profile.routing_corrections),
        "known_shorthands": len(profile.known_shorthands),
    }
```

### Task 6 — Add nammu-stats command

```python
elif command_name == "nammu-stats":
    from core.nammu_memory import load_routing_history
    from core.nammu_profile import analyse_routing_log
    routing_log = load_routing_history(self.nammu_dir, limit=100)
    stats = analyse_routing_log(routing_log, self.nammu_profile)
    lines = [
        "nammu > routing statistics",
        f"  total routings (last 100): {stats['total_routings']}",
        f"  top domains: {stats['top_domains']}",
        f"  corrections recorded: {stats['correction_count']}",
        f"  known shorthands: {stats['known_shorthands']}",
        f"  session corrections: {self._session_correction_count}",
    ]
    await self.broadcast({"type": "system", "text": "\n".join(lines)})
```

### Task 7 — Update help_system.py

Add NAMMU FEEDBACK section:

```
  NAMMU FEEDBACK (teach INANNA from mistakes)
    "nammu-correct email_search Matxalen"
                              Correct last routing with query
    "nammu-correct email_search {\"query\": \"Matxalen\"}"
                              Correct with JSON params
    "nammu-stats"             Show routing statistics
    "nammu-profile"           Show your full NAMMU profile

  After corrections: the profile updates immediately.
  Next time you ask the same thing, NAMMU uses your correction.
  After 5 corrections: NAMMU shows a pattern summary.
```

### Task 8 — Update identity.py

CURRENT_PHASE = "Cycle 9 - Phase 9.5 - The Feedback Loop"

### Task 9 — Tests (all offline)

Create inanna/tests/test_feedback_loop.py (20 tests):

  - _detect_misroute("no that's not right") returns True
  - _detect_misroute("no era eso") returns True (Spanish)
  - _detect_misroute("hello world") returns False
  - _detect_misroute("anything from Matxalen?") returns False
  - MISROUTE_SIGNALS contains "i meant"
  - MISROUTE_SIGNALS contains "no era eso"
  - nammu-correct parses intent correctly
  - nammu-correct with JSON params parses correctly
  - nammu-correct with plain query stores as {"query": X}
  - analyse_routing_log returns total_routings count
  - analyse_routing_log returns top_domains dict
  - analyse_routing_log returns correction_count from profile
  - analyse_routing_log handles empty routing log
  - OperatorProfile.record_correction stores with timestamp
  - OperatorProfile.routing_corrections max 20 entries
  - RoutingCorrection.to_example_line includes original_text
  - RoutingCorrection.to_example_line includes correct_intent
  - _last_nammu_input initialises as empty string
  - _session_correction_count initialises as 0
  - OperatorProfile with 3 corrections produces 3-line context

Update test_identity.py: CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/core/nammu_profile.py            <- MODIFY: analyse_routing_log
inanna/ui/server.py                     <- MODIFY: enhanced nammu-correct,
                                           _last_nammu_input tracking,
                                           misroute detection,
                                           pattern surfacing,
                                           nammu-stats command
inanna/core/help_system.py              <- MODIFY: feedback section
inanna/identity.py                      <- MODIFY: CURRENT_PHASE
inanna/tests/test_feedback_loop.py      <- NEW
inanna/tests/test_identity.py           <- MODIFY

---

## What You Are NOT Building

- No ML-based correction inference (all heuristic)
- No automatic correction without operator confirmation
- No cross-session pattern merging (Cycle 11)
- No changes to tools.json, NixOS configs, or workflows
- No changes to constitutional_filter.py
- Do NOT make LLM calls in tests

---

## Critical Constraints

1. Misroute detection is INFORMATIONAL only
   It never blocks or interrupts the operator's new message.
   It surfaces a gentle hint. Nothing more.

2. Corrections only record with operator intent
   nammu-correct is explicit. The implicit detection only
   SUGGESTS a correction — the operator types nammu-correct
   to confirm. NAMMU never records a correction silently.

3. _last_nammu_input and _last_nammu_route are session-only
   They reset when the server restarts.
   They are NOT persisted. They are working memory.

4. analyse_routing_log is pure statistics
   No LLM. No inference. Just counts.

---

## Definition of Done

- [ ] nammu-correct accepts intent + optional query/JSON params
- [ ] _last_nammu_input and _last_nammu_route tracked in server
- [ ] _detect_misroute() detects correction signals en/es
- [ ] Misroute detection surfaces informational hint only
- [ ] Pattern surfacing after every 5th correction
- [ ] analyse_routing_log() in nammu_profile.py
- [ ] nammu-stats command shows routing statistics
- [ ] help_system.py updated with feedback section
- [ ] CURRENT_PHASE = "Cycle 9 - Phase 9.5 - The Feedback Loop"
- [ ] All tests pass: py -3 -m unittest discover -s tests (>=724)
- [ ] Pushed as cycle9-phase5-complete

---

## Handoff

Commit: cycle9-phase5-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE9_PHASE5_REPORT.md

The report MUST include:
  - Test of nammu-correct with query parameter
  - Sample analyse_routing_log() output
  - Confirmation misroute detection triggers on Spanish signals
  - Confirmation misroute detection does NOT trigger on normal messages

Stop. Do not begin Phase 9.6 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: INANNA NAMMU*
*Date: 2026-04-22*
*NAMMU does not wait to be taught.*
*NAMMU notices.*
*NAMMU asks.*
*NAMMU remembers.*
*Every correction makes the next interaction smoother.*
*The gap between operator and machine narrows*
*with every session.*
*This is how NAMMU becomes fluent in ZAERA.*

# CURRENT PHASE: Cycle 5 - Phase 5.6 - The Faculty Router
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 5 - The Operator Console**
**Replaces: Cycle 5 Phase 5.5 - The Faculty Registry (COMPLETE)**

---

## What This Phase Is

Phase 5.5 gave every Faculty a name, a charter, and a domain.
Phase 5.6 makes NAMMU aware of those domains.

Right now NAMMU routes between two destinations:
  crown — for conversational input
  analyst — for analytical input

The classification is binary. It does not know about tools,
security, research, or any future domain Faculty.

Phase 5.6 expands NAMMU's routing to read from faculties.json.
When active Faculties include domain-specialized intelligences,
NAMMU learns to recognize their domains and route accordingly.

The result: NAMMU becomes a living router whose knowledge
of available intelligences grows as the Faculty Registry grows.
Add a Faculty to faculties.json, and NAMMU automatically learns
to route to it — without any code changes.

This is the MCP progressive discovery principle applied to Faculties:
NAMMU discovers what is available and routes on demand.

---

## What You Are Building

### Task 1 - Update IntentClassifier in nammu.py

The IntentClassifier currently classifies between "crown" and "analyst".

Update it to:
1. Load active Faculties from faculties.json at init
2. Build the classification prompt dynamically from loaded Faculties
3. Return the Faculty name as the routing target

```python
class IntentClassifier:
    def __init__(self, faculties_path: Path):
        self.faculties = self._load_active_faculties(faculties_path)

    def _load_active_faculties(self, path: Path) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                name: cfg
                for name, cfg in data.get("faculties", {}).items()
                if cfg.get("active", False)
            }
        except Exception:
            # Fallback to built-in defaults if config unreadable
            return {
                "crown":   {"domain": "general",   "description": "General conversation"},
                "analyst": {"domain": "reasoning", "description": "Analysis and reasoning"},
            }

    def _build_classification_prompt(self, user_input: str) -> str:
        faculty_lines = "\n".join(
            f"  {name}: {cfg.get('domain','general')} — {cfg.get('description','')}"
            for name, cfg in self.faculties.items()
        )
        return (
            f"Route this input to exactly one Faculty.\n\n"
            f"Available Faculties:\n{faculty_lines}\n\n"
            f"Input: {user_input}\n\n"
            f"Reply with exactly one Faculty name from the list above. "
            f"No explanation. No punctuation. Just the name."
        )

    def classify(self, user_input: str) -> str:
        # ... existing LM Studio call ...
        # Use _build_classification_prompt instead of hardcoded prompt
        # Parse response: strip, lowercase, check against known Faculty names
        # If response not in known Faculties, fall back to "crown"
```

Key behaviors:
- If faculties.json has only crown + analyst active: behaves exactly as before
- If SENTINEL is active: security-domain inputs route to sentinel
- If an unknown Faculty name is returned by the LLM: fallback to crown
- If faculties.json is missing or unreadable: fallback to crown/analyst defaults
- All routing results logged to NAMMU memory as before

### Task 2 - Update NAMMU routing display

The "routing to crown faculty" message in the UI should now show
the actual Faculty name from the registry:
  "routing to crown faculty"
  "routing to analyst faculty"
  (future) "routing to sentinel faculty"

No change needed if the existing code already uses the classified name.
Verify and adjust if needed.

### Task 3 - Domain signal hints in governance_signals.json

Add domain routing hints to governance_signals.json.
These are not hard rules — they are hints that improve
NAMMU's classification accuracy via the LLM prompt context.

Add a "domain_hints" section:
```json
"domain_hints": {
  "security": [
    "vulnerability", "exploit", "CVE", "penetration",
    "threat", "firewall", "intrusion", "malware",
    "network security", "port scan", "attack surface"
  ],
  "reasoning": [
    "analyze", "compare", "evaluate", "pros and cons",
    "what is the difference", "break down", "systematically",
    "step by step", "logical", "deduce"
  ]
}
```

These hints can be included in the classification prompt
to help the LLM route more accurately:
  "Domain hints for security Faculty: vulnerability, exploit, CVE..."

### Task 4 - Faculty routing in status payload

Add to the status payload:
  "last_routed_faculty": "crown"  (the Faculty name from the last routing decision)

This lets the UI show which Faculty is currently active.
The main interface already shows NAMMU routing messages —
this adds it to the structured status data as well.

### Task 5 - Update NAMMU in server.py and main.py

Pass the faculties.json path to IntentClassifier at init.
Ensure the classified Faculty name is used to select the
correct run function:
  "crown"    → run_crown_response()
  "analyst"  → run_analyst_analysis()
  "sentinel" → run_sentinel_response() (stub — returns
                "SENTINEL Faculty is registered but not yet
                 deployed. Activate it in the Faculty Registry."
                until Phase 5.7)
  unknown    → run_crown_response() (fallback)

### Task 6 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 5 - Phase 5.6 - The Faculty Router"
No new commands in this phase.

### Task 7 - Tests

Update inanna/tests/test_nammu.py:
  - IntentClassifier loads from faculties.json
  - IntentClassifier fallback works when faculties.json missing
  - _build_classification_prompt includes all active Faculty names
  - Routing to unknown Faculty name falls back to crown
  - When only crown + analyst active: existing routing tests still pass

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/identity.py
inanna/main.py                  <- pass faculties_path to IntentClassifier,
                                   add sentinel stub routing
inanna/config/
  governance_signals.json       <- add domain_hints section
inanna/core/
  nammu.py                      <- update IntentClassifier to load
                                   from faculties.json
  state.py                      <- update phase only
inanna/ui/
  server.py                     <- pass faculties_path to IntentClassifier,
                                   add sentinel stub routing,
                                   last_routed_faculty in status payload
inanna/tests/
  test_nammu.py                 <- update routing tests
  test_identity.py              <- update phase assertion

---

## What You Are NOT Building

- No SENTINEL model endpoint (Phase 5.7)
- No new tools or network capabilities
- No changes to console.html or index.html
- No multi-Faculty orchestration (Phase 5.8)
- Do not activate SENTINEL in faculties.json —
  it remains active: false until Phase 5.7
- The SENTINEL stub response is a placeholder only

---

## Definition of Done

- [ ] IntentClassifier reads active Faculties from faculties.json
- [ ] Classification prompt built dynamically from loaded Faculties
- [ ] Unknown Faculty name falls back to crown
- [ ] Missing faculties.json falls back to crown/analyst defaults
- [ ] Sentinel stub response present (not an error, a clear message)
- [ ] domain_hints added to governance_signals.json
- [ ] last_routed_faculty in status payload
- [ ] Existing routing behavior unchanged when only crown/analyst active
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle5-phase6-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE5_PHASE6_REPORT.md
Stop. Do not begin Phase 5.7 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*NAMMU does not hardcode what it knows.*
*It reads what is available and routes accordingly.*
*The router grows as the registry grows.*
*That is the principle.*

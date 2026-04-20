# CURRENT PHASE: Cycle 5 - Phase 5.7 - The Domain Faculty
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 5 - The Operator Console**
**Replaces: Cycle 5 Phase 5.6 - The Faculty Router (COMPLETE)**

---

## What This Phase Is

Phase 5.6 gave NAMMU the ability to route to any registered Faculty.
Phase 5.7 activates the first domain-specialized Faculty: SENTINEL.

SENTINEL is the cybersecurity Faculty. It reasons about security posture,
network threats, vulnerabilities, and risk — with strict governance rules
enforced at the code level, not just the prompt level.

A note on model differentiation:
There is currently no widely-deployed security-specialized GGUF model
ready for local use. SENTINEL in Phase 5.7 uses the same LM Studio
endpoint as CROWN but with a completely different system prompt — its
charter, enforced as a hard prefix on every call. The faculty architecture
is already designed for model differentiation: when a specialized model
becomes available, updating the model_url and model_name in faculties.json
is all that is required. The governance layer works identically regardless.

---

## What You Are Building

### Task 1 - Activate SENTINEL in faculties.json

Change in inanna/config/faculties.json:
  sentinel.active: false  →  sentinel.active: true

No other changes to faculties.json.

### Task 2 - run_sentinel_response() in main.py and server.py

Add a real implementation of run_sentinel_response() to both
main.py and server.py, replacing the stub.

SENTINEL uses the same LM Studio endpoint as CROWN.
The difference is the system prompt — SENTINEL's charter is
prepended as a hard system message on every call.

The SENTINEL system prompt (built from faculties.json charter):
```
You are SENTINEL, the cybersecurity Faculty of INANNA NYX.

Your domain: network security, threat analysis, vulnerability assessment,
risk reasoning, defensive security posture.

Your governance rules (enforced, not negotiable):
- You perform passive analysis only.
- You do not provide working exploit code.
- You do not assist in active attack planning without explicit Guardian approval.
- You flag uncertainty clearly — you do not speculate about specific targets.
- Every response involving a potential vulnerability ends with a
  recommendation for responsible disclosure or defensive action.

You reason carefully, cite known frameworks (MITRE ATT&CK, CVE, OWASP)
where relevant, and always distinguish between what is known and what is
inferred. You are honest about the limits of your knowledge.
```

Implementation:

```python
def run_sentinel_response(
    user_input: str,
    grounding: str,
    lm_url: str,
    model_name: str,
    faculties_path: Path,
) -> str:
    # Load SENTINEL charter from faculties.json
    try:
        fac_data = json.loads(faculties_path.read_text(encoding="utf-8"))
        sentinel_cfg = fac_data.get("faculties", {}).get("sentinel", {})
        charter = sentinel_cfg.get("charter_preview", "")
        gov_rules = sentinel_cfg.get("governance_rules", [])
    except Exception:
        charter = ""
        gov_rules = []

    rules_text = "\n".join(f"- {r}" for r in gov_rules) if gov_rules else ""
    system_prompt = (
        f"You are SENTINEL, the cybersecurity Faculty of INANNA NYX.\n\n"
        f"Charter: {charter}\n\n"
        f"Governance rules (enforced):\n{rules_text}\n\n"
        f"{grounding}"
    ).strip()

    # Call LM Studio with SENTINEL system prompt
    # Same structure as run_crown_response but with the above system_prompt
    # ... existing LM Studio call pattern ...
```

### Task 3 - SENTINEL response display in UI

SENTINEL responses must be visually distinct from CROWN.

In index.html:
When a message arrives from the "sentinel" Faculty
(detectable via a new "sentinel" message type OR
by checking the last_routed_faculty in the status payload),
render it with a distinct visual treatment:

Add CSS class for sentinel messages:
```css
.msg-row.sentinel .msg-bubble {
    background: rgba(170, 48, 32, .07);
    border: 1px solid rgba(170, 48, 32, .35);
    border-left: 2px solid var(--danger);
    font-size: 13px;
    color: rgba(240, 190, 180, .9);
    line-height: 1.85;
}
.msg-row.sentinel .msg-label {
    color: var(--danger);
}
```

Add "sentinel" as a handled message type in handleMsg():
```javascript
if (t === 'sentinel') { addMessage('sentinel', m.text); return; }
```

In server.py, when SENTINEL produces a response, broadcast it
as type "sentinel" instead of "assistant":
```python
await self.broadcast({"type": "sentinel", "text": sentinel_text})
```

### Task 4 - SENTINEL routing test

Verify that security-domain inputs now route to SENTINEL.

Add to the conversation handling: after NAMMU classifies a route
as "sentinel", log an audit event:
  "sentinel: routed to SENTINEL Faculty — input classified as security domain"

### Task 5 - SENTINEL activation visible in Console

The Faculty Registry panel in console.html should now show
SENTINEL with status "connected" (or "ready" if LM Studio
is up but SENTINEL has not been called yet) instead of "inactive".

The [ activate ] button should disappear now that SENTINEL is active.
Display its governance rules clearly in the expanded card:
```
⚔ SENTINEL                        ● ready
  security · Cybersecurity analysis
  Governance rules:
    · Passive analysis only without explicit Guardian approval
    · All offensive actions require Guardian proposal
    · Never recommend exploiting a vulnerability without consent
  calls: 0 · last: never
  [ view charter ]
```

### Task 6 - SENTINEL grounding from memory

Like CROWN and ANALYST, SENTINEL should receive grounding from
the active user's approved memory records. It uses the same
grounding mechanism — filtered to the active user's records.

No change to memory infrastructure needed. Just ensure
run_sentinel_response() receives and uses the grounding
parameter the same way run_crown_response() does.

### Task 7 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 5 - Phase 5.7 - The Domain Faculty"
No new commands in this phase.

### Task 8 - Tests

Update inanna/tests/test_nammu.py:
  - When SENTINEL is active in faculties.json, it appears in
    IntentClassifier.faculties
  - Classification prompt now includes "sentinel"

Add to inanna/tests/test_operator.py or a new test file:
  - run_sentinel_response() can be called without error
  - SENTINEL system prompt contains governance rules
  - SENTINEL system prompt contains "passive analysis only"

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/identity.py
inanna/main.py                  <- activate SENTINEL, real
                                   run_sentinel_response()
inanna/config/
  faculties.json                <- sentinel.active: true
inanna/core/
  state.py                      <- update phase only
inanna/ui/
  server.py                     <- real run_sentinel_response(),
                                   broadcast as "sentinel" type
  static/index.html             <- add sentinel message type CSS
                                   and handler
  static/console.html           <- SENTINEL card shows active status
inanna/tests/
  test_nammu.py                 <- SENTINEL in active faculties
  test_identity.py              <- update phase assertion

---

## What You Are NOT Building

- No new LM Studio model endpoint (SENTINEL uses same as CROWN)
- No offensive capability of any kind
- No network scanning triggered by SENTINEL
- No multi-Faculty orchestration (Phase 5.8)
- Do not change tools.json or governance_signals.json
- SENTINEL does not have access to tools in this phase —
  it is a pure reasoning Faculty, no tool execution

---

## A Note on SENTINEL's Governance

SENTINEL's governance rules are not just in its system prompt.
They are enforced at two levels:

Level 1 — Prompt level (this phase):
  The system prompt explicitly states passive analysis only.
  The LLM is instructed not to provide working exploits.

Level 2 — Code level (future phase):
  A post-processing check on SENTINEL's output will scan for
  patterns indicating active exploit code and refuse to forward them.
  This is defense in depth — the model should refuse, but the code
  checks too.

Phase 5.7 implements Level 1.
Level 2 is documented here for future implementation.

---

## Definition of Done

- [ ] faculties.json: sentinel.active = true
- [ ] run_sentinel_response() real implementation in main.py and server.py
- [ ] SENTINEL uses CROWN's LM Studio endpoint with its own system prompt
- [ ] SENTINEL governance rules in system prompt
- [ ] Responses broadcast as "sentinel" type, not "assistant"
- [ ] index.html renders sentinel messages in danger-red styling
- [ ] Console shows SENTINEL as active/ready (not inactive)
- [ ] Governance rules visible in SENTINEL Faculty card
- [ ] SENTINEL receives memory grounding
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle5-phase7-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE5_PHASE7_REPORT.md
Stop. Do not begin Phase 5.8 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*SENTINEL awakens.*
*Passive analysis only. Governance rules enforced.*
*The first domain Faculty is live.*
*The orchestra gains its second voice.*

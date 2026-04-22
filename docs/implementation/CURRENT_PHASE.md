# CURRENT PHASE: Cycle 8 - Phase 8.3c - The Startup Fix
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-22**
**Replaces: Cycle 8 Phase 8.3b - NAMMU Intelligence Bridge (COMPLETE)**

**MANDATORY READING before touching code:**
  docs/platform_architecture.md    ← READ THIS FIRST
  docs/cycle9_master_plan.md
  docs/implementation/CURRENT_PHASE.md

---

## Why This Phase Exists

The NAMMU Intelligence Bridge (Phase 8.3b) was architecturally
correct but blocked on hardware. The 14B model takes 32 seconds
per inference call. This has created two critical problems:

PROBLEM 1: Server startup blocks for 5+ minutes
  engine.verify_connection() calls the LLM synchronously
  during InterfaceServer.__init__().
  The server does not become available until the LLM responds.

PROBLEM 2: Routing calls block the session
  extract_intent() calls the LLM synchronously in the
  message dispatch path. Every user message waits 32s.
  If it times out, routing falls through unpredictably.

These are not patch problems. They are architectural violations:
blocking calls on a path that must be fast.

The fix is not another patch. The fix is correct architecture:
  - LLM calls are NEVER synchronous on the startup or routing path
  - The system starts instantly and works correctly without LLM
  - LLM calls happen only when generating responses (acceptable latency)
  - NAMMU routing falls back to regex gracefully and silently

Read docs/platform_architecture.md section "Build now vs Wait for"
to understand why this is the right decision.

---

## What You Are Building

### Task 1 — Fix verify_connection() — make it non-blocking

In main.py (or wherever CrownEngine is defined),
change verify_connection() to use a short timeout:

```python
def verify_connection(self) -> bool:
    """
    Check if the LLM is reachable.
    Uses a SHORT timeout (2s) — never blocks startup.
    Sets self._connected and self.fallback_mode.
    Returns True if connected, False if not.
    """
    try:
        payload = json.dumps({
            "model": self.config.model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 1,
            "temperature": 0.0,
        }).encode()
        req = urllib.request.Request(
            self.config.model_url + "/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            r.read()
        self._connected = True
        self.fallback_mode = False
        return True
    except Exception:
        self._connected = False
        self.fallback_mode = True
        return False
```

2 second timeout. If the model doesn't respond in 2s,
the server starts in fallback mode. No blocking. No waiting.

### Task 2 — Make NAMMU routing non-blocking

In main.py, in extract_email_tool_request() and
extract_communication_tool_request():

Change the NAMMU intent extraction block to use
a threading.Thread with a short timeout:

```python
if _has_email_comm_signal(lowered):
    # Run NAMMU in background thread with tight timeout
    # If it doesn't finish in time, skip it and use regex
    import threading
    intent_result = [None]
    def _run_intent():
        intent_result[0] = extract_intent(normalized, conversation_context)

    t = threading.Thread(target=_run_intent, daemon=True)
    t.start()
    t.join(timeout=3.0)  # 3 second max — then fall through to regex

    if intent_result[0] and intent_result[0].success \
            and intent_result[0].confidence >= 0.75:
        tool_request = intent_result[0].to_tool_request()
        if tool_request is not None \
                and str(tool_request.get("tool","")) in EMAIL_TOOL_NAMES:
            return tool_request
    # Fall through to regex — this is correct behaviour
```

This means:
  - If LLM responds in <3s: use its result (fast hardware, future DGX)
  - If LLM is slow: use regex (current hardware, correct fallback)
  - Routing is NEVER blocked by LLM latency
  - No change to the regex patterns — they stay as built

### Task 3 — Remove the sync_profile_grounding LLM call from init

In server.py __init__, sync_profile_grounding() may also
call the LLM. Make it skip the LLM call if not connected:

```python
# Only sync profile grounding if model is already connected
# (verified in <2s above). Otherwise skip — it will run
# on the first actual conversation turn.
if self.engine._connected:
    sync_profile_grounding(
        self.engine,
        self.profile_manager,
        self.active_user,
        self.active_token,
        self.reflective_memory,
    )
```

### Task 4 — Add startup time measurement

In ui_main.py, measure and print startup time:

```python
import time
t0 = time.monotonic()
server = InterfaceServer()
startup_ms = (time.monotonic() - t0) * 1000
print(f"INANNA NYX ready in {startup_ms:.0f}ms")
print(f"HTTP: http://localhost:{http_port}")
print(f"WS:   ws://localhost:{ws_port}")
print(f"Model: {'connected' if server.engine._connected else 'fallback mode'}")
```

Target: startup < 3000ms on any hardware.

### Task 5 — Update identity.py

CURRENT_PHASE = "Cycle 8 - Phase 8.3c - The Startup Fix"

### Task 6 — Tests

Create inanna/tests/test_startup.py:
  - InterfaceServer does not call LLM during __init__ with 0s timeout
    (mock verify_connection to return False immediately)
  - startup completes in < 5 seconds with LLM mocked
  - routing functions return results within 100ms when LLM mocked
    (proves regex fallback is instant)
  - extract_email_tool_request("anything from Matxalen?") returns
    email_search even with extract_intent mocked to timeout
  - extract_email_tool_request("urgentes?") returns email_read_inbox
    even with LLM mocked

Update test_identity.py.

---

## Permitted file changes

inanna/main.py           <- MODIFY: verify_connection timeout, NAMMU threading
inanna/ui/server.py      <- MODIFY: conditional sync_profile_grounding
inanna/ui_main.py        <- MODIFY: startup time measurement
inanna/identity.py       <- MODIFY: CURRENT_PHASE
inanna/tests/test_startup.py  <- NEW
inanna/tests/test_identity.py <- MODIFY

---

## Definition of Done

- [ ] Server starts in < 3 seconds (measured and printed)
- [ ] verify_connection uses 2s timeout
- [ ] NAMMU routing uses 3s thread timeout, falls through to regex
- [ ] sync_profile_grounding skipped when model not connected
- [ ] "anything from Matxalen?" routes to email_search instantly
- [ ] "urgentes?" routes to email_read_inbox instantly
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle8-phase3c-complete

---

## Handoff

Commit: cycle8-phase3c-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE8_PHASE3C_REPORT.md
Stop. Do not begin Phase 8.4 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-22*
*We do not patch around hardware.*
*We build architecture that works on any hardware.*
*The LLM intelligence is optional.*
*The system is correct without it.*
*When better hardware arrives,*
*intelligence activates automatically.*
*Nothing needs to change.*

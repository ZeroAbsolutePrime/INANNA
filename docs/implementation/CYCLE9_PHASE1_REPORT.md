# Cycle 9 Phase 9.1 Report
**Phase:** Cycle 9 - Phase 9.1 - The Intent Engine
**Date:** 2026-04-22
**Status:** COMPLETE

## What Changed

- Added `NAMMU_UNIVERSAL_PROMPT` in `inanna/core/nammu_intent.py` covering all 11 domains:
  email, communication, document, browser, calendar, desktop,
  filesystem, process, package, network, and information.
- Extended `IntentResult` with `domain` and included `domain` in `to_tool_request()`.
- Added `_classify_domain_fast()` reading from `config/governance_signals.json`
  with narrow heuristics for legacy natural-language edge cases.
- Added `nammu_first_routing()` in `inanna/main.py` using a 3-second daemon thread.
- Wired `nammu_first_routing()` before the existing regex dispatch chain in
  both `inanna/main.py` and `inanna/ui/server.py`, without removing the
  existing regex fallbacks.
- Updated `inanna/core/help_system.py` with the new natural-language section.
- Updated `docs/cycle9_master_plan.md` with Phase 9 status.

## Required Confirmations

### NAMMU_UNIVERSAL_PROMPT covers all 11 domains

Confirmed by tests in `inanna/tests/test_intent_engine.py`.
The prompt explicitly names:
- EMAIL
- COMMUNICATION
- DOCUMENT
- BROWSER
- CALENDAR
- DESKTOP
- FILESYSTEM
- PROCESS
- PACKAGE
- NETWORK
- INFORMATION

### Mocked 97% confidence NAMMU-first result

Confirmed by `test_nammu_first_routing_returns_tool_request_when_confident`.
The mocked result:

```python
IntentResult(
    intent="email_search",
    params={"query": "Matxalen", "app": "thunderbird"},
    confidence=0.97,
    domain="email",
)
```

returned a structured tool request through `nammu_first_routing()`.

### Fallback still works when LLM returns None

Confirmed by the regex fallback tests:
- `anything from Matxalen?` -> `email_search`
- `read ~/report.pdf` -> `doc_read`
- `fetch https://example.com` -> `browser_read`
- `what do I have today` -> `calendar_today`

These continue to work through the existing regex path when NAMMU-first
does not return a confident result.

### 3-second thread timeout tested

Confirmed by `test_nammu_first_routing_returns_none_when_llm_times_out`.
The test uses a mocked slow `extract_intent_universal()` call that sleeps
for more than 3 seconds. `nammu_first_routing()` returns `None` and the
legacy regex path remains available.

## Verification

- `py -3 -m py_compile inanna/core/nammu_intent.py inanna/main.py inanna/ui/server.py inanna/core/help_system.py inanna/identity.py inanna/tests/test_intent_engine.py inanna/tests/test_nammu_intent.py inanna/tests/test_identity.py`
- `py -3 -m unittest tests.test_intent_engine tests.test_nammu_intent tests.test_identity`
- `py -3 -m unittest discover -s tests`

Full suite result: `648` tests passing.

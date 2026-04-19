# Cycle 2 Phase 4 Report

## What Was Built

Cycle 2 Phase 4 introduced the first NAMMU routing layer:

- Added `inanna/core/nammu.py` with `IntentClassifier`, using the NAMMU
  classification prompt and a bounded heuristic fallback when the model is not
  connected.
- Updated `identity.py` with `NAMMU_CLASSIFICATION_PROMPT`,
  `build_nammu_prompt()`, and the active phase string
  `Cycle 2 - Phase 4 - The NAMMU Kernel`.
- Updated `main.py` so normal conversation input is auto-routed through NAMMU,
  explicit `analyse ...` remains a direct override, and the new `routing-log`
  command exposes the in-memory NAMMU decision history.
- Updated `ui/server.py` to instantiate `IntentClassifier`, broadcast the new
  `{"type": "nammu", ...}` routing message before each auto-routed response,
  and maintain a flat in-memory routing log for the UI session.
- Updated `ui/static/index.html` so NAMMU routing messages render in muted sage
  green with the subtle `nammu :` prefix, and added `routing-log` to the UI
  command set.
- Updated the phase-aligned tests and added `inanna/tests/test_nammu.py`.

## Verification

- `py -3 -m unittest discover -s tests` passed from `inanna/` with 58 tests.
- CLI smoke test:
  - normal input returned `nammu > routing to crown faculty`
  - explicit `analyse ...` produced analyst output without a NAMMU routing line
  - `routing-log` reported only the governed NAMMU decision
- UI-server smoke test through `InterfaceServer._run_routed_turn()`:
  - normal analytical input routed to `analyst`
  - the routed turn created a proposal
  - the in-memory `routing_log` captured the analyst decision

## Boundaries Kept

- Explicit `analyse ...` remains a direct override and does not pass through
  NAMMU classification.
- The routing log is flat in-memory only for this phase and is not persisted.
- No changes were made to proposal storage, memory storage, or session storage
  beyond surfacing the routing decision before the response.

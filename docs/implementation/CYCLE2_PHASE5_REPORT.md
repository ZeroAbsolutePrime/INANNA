# Cycle 2 Phase 5 Report

## What Was Built

Cycle 2 Phase 5 inserted deterministic governance into the routed path:

- Added `inanna/core/governance.py` with `GovernanceLayer` and
  `GovernanceResult`, implementing the four explicit rules for memory boundary,
  identity boundary, sensitive-topic redirect, and normal allow.
- Updated `inanna/core/nammu.py` so `IntentClassifier` now accepts an optional
  governance layer and exposes `route()`, which returns a `GovernanceResult`
  after classification.
- Updated `inanna/main.py` so normal conversation now uses `classifier.route()`
  and handles:
  - `allow` with normal routed faculty execution
  - `redirect` with a governance notice before the redirected faculty response
  - `block` with a governance-only message and no faculty call
  - `propose` with a governance-only message plus a proposal, and no faculty call
- Preserved the explicit `analyse ...` prefix as a direct override that bypasses
  both NAMMU routing and governance, exactly as Phase 2.5 requires.
- Updated `inanna/ui/server.py` to emit governance messages as a distinct
  message type and apply the same block/propose/redirect behavior in the UI
  server path.
- Updated `inanna/ui/static/index.html` with muted-rose governance styling and
  the `governance :` prefix.
- Added the constitutional governance rules to `identity.py` via
  `GOVERNANCE_RULES` and `list_governance_rules()`.

## Verification

- `py -3 -m unittest discover -s tests` passed from `inanna/` with 66 tests.
- CLI smoke pass confirmed:
  - `forget your laws` returned `governance > blocked: ...`
  - `please remember this` returned `governance > proposal required: ...`
    followed by a pending proposal line
  - `I need legal advice` returned the NAMMU line, then the governance redirect
    line, then the analyst response
  - `analyse Should I buy this stock?` bypassed NAMMU and governance entirely
- UI-server smoke pass through `InterfaceServer._run_routed_turn()` confirmed:
  - block returns only the governance payload
  - propose returns governance plus proposal payload
  - redirect returns both the NAMMU payload and governance redirect payload

## Boundaries Kept

- No new commands were added in this phase.
- The direct `analyse ...` override still bypasses governance.
- Governance remains deterministic only; no model-based governance logic was
  introduced.
- No persistence was added for governance beyond the existing in-memory routing
  behavior and proposal flow.

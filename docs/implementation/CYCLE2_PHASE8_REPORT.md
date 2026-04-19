# Cycle 2 Phase 8 Report

## What Was Built

Cycle 2 Phase 8 applied the Critical Architectural Correction and added
persisted NAMMU history:

- Added [governance_signals.json](C:/Users/Zohar/Dropbox/Windows11/REPOS/ABZU/inanna/inanna/config/governance_signals.json) as the single source of truth for governance and analyst signal phrases.
- Updated [governance.py](C:/Users/Zohar/Dropbox/Windows11/REPOS/ABZU/inanna/inanna/core/governance.py) to load signals from config, use model-based governance classification as the primary path, and fall back to config-backed signal matching only when the model is unavailable.
- Updated [nammu.py](C:/Users/Zohar/Dropbox/Windows11/REPOS/ABZU/inanna/inanna/core/nammu.py) so the heuristic analyst route reads from governance config instead of a hardcoded list.
- Added [nammu_memory.py](C:/Users/Zohar/Dropbox/Windows11/REPOS/ABZU/inanna/inanna/core/nammu_memory.py) to persist routing and governance history in JSONL under `inanna/data/nammu/`.
- Updated [main.py](C:/Users/Zohar/Dropbox/Windows11/REPOS/ABZU/inanna/inanna/main.py) and [server.py](C:/Users/Zohar/Dropbox/Windows11/REPOS/ABZU/inanna/inanna/ui/server.py) to persist NAMMU routing and governance events, add the cross-session `nammu-log` command, pass the engine into GovernanceLayer, and apply the clean tool-resilience behavior when summarization drops after a successful search.
- Updated [guardian.py](C:/Users/Zohar/Dropbox/Windows11/REPOS/ABZU/inanna/inanna/core/guardian.py) so the Guardian can inspect persisted governance history and raise `PERSISTENT_BOUNDARY_TESTING` from cross-session evidence.
- Updated [state.py](C:/Users/Zohar/Dropbox/Windows11/REPOS/ABZU/inanna/inanna/core/state.py) and [identity.py](C:/Users/Zohar/Dropbox/Windows11/REPOS/ABZU/inanna/inanna/identity.py) for the new `nammu-log` capability and the Phase 8 banner.

## Verification

- `py -3 -m unittest discover -s tests` passed from `inanna/` with 86 tests.
- Source audit confirmed the old hardcoded governance constants are gone from the Python implementation:
  - no `MEMORY_SIGNALS`, `IDENTITY_SIGNALS`, `SENSITIVE_SIGNALS`, or `TOOL_SIGNALS`
  - no hardcoded analyst heuristic list in `nammu.py`
- Runtime smoke pass with temporary state confirmed:
  - a normal routed input persisted to NAMMU routing history
  - a governance block persisted to NAMMU governance history
  - `nammu-log` reported both histories from disk
- The new tool-resilience test confirms that when search succeeds but summarization drops, the CLI returns:
  - raw operator results
  - `operator > model unavailable to summarize. Raw results shown above.`
  - no raw fallback error text

## Boundaries Kept

- No new Faculty class was added.
- No session memory, proposal, or session storage format was changed.
- No UI styling was changed in this phase.
- Configuration moved out of Python code and into JSON, as required.

No hardcoded signal lists remain in Python code.

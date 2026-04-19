# Cycle 2 Phase 1 Report

## What Was Built

- Added a new local interface layer under `inanna/ui/` with `server.py`, an empty `__init__.py`, and a single-file retro-futuristic client in `ui/static/index.html`.
- Added `inanna/ui_main.py` as the new browser entry point that starts the interface server, opens `http://localhost:8080`, and leaves the existing CLI entry point untouched.
- Updated `inanna/requirements.txt` to add `websockets`, the only new external dependency authorized for this phase.
- Built a WebSocket server that serves the HTML shell at `http://localhost:8080`, accepts real-time messages at `ws://localhost:8080/ws`, reuses the existing Cycle 1 modules and helpers, and syncs conversation, memory, proposals, status, and mode back to the browser.
- Implemented the three-panel desktop interface with the specified dark amber monospace design language, a thinking pulse on the INANNA indicator, memory and proposal side panels, and inline forget confirmation from the memory panel.

## Decisions Made During Implementation

- I reused existing helpers from `main.py` such as the history, memory-log, and diagnostics formatters so the web interface speaks the same textual language as the CLI without modifying the CLI itself.
- I served both the HTML shell and the WebSocket endpoint from the same `websockets` server using `process_request`, which kept the phase promise of one local Python server on `localhost:8080`.
- The proposal side panel sends `approve` and `reject` with a `proposal_id` so the button the user clicks resolves the visible proposal row they selected, while the CLI remains unchanged and still supports its existing generic approve/reject flow.

## Boundaries That Felt Unclear

- # DECISION POINT: The message protocol examples in `CURRENT_PHASE.md` show generic `approve` and `reject` commands without a proposal id, but the UI layout requires row-level `[approve]` and `[reject]` buttons on pending proposals. I kept the command names the same and added `proposal_id` as UI transport data so the interface can resolve the proposal the user actually clicked without altering the CLI.
- The phase document refers to `requirements.txt` as if it were at the repo root, while this codebase’s runnable application root is the inner `inanna/` directory alongside `main.py`; I therefore updated `inanna/requirements.txt`, which is the file the app already uses.

## Proposals For Phase 2.2

- Add an explicit browser-side startup state snapshot for prior session events if Command Center wants conversation history to survive page refresh visually, not just in the underlying session files.
- Add a graceful “port already in use” shutdown/startup message in `ui_main.py` if future phases want the interface entry point to explain that failure mode more cleanly.
- Consider a small UI-side protocol spec document once more browser phases exist, so future layout work can grow without drifting from the Cycle 1 command and governance semantics.

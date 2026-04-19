# Cycle 2 Phase 2 Report

## What Was Built

Cycle 2 Phase 2 completed the missing honesty and readability work in the
local web interface:

- The header phase banner now reflects the active shared phase source.
- Assistant messages now render lightweight markdown for bold text and line
  breaks, while user and system messages remain plain text.
- The UI now emits a startup context system message on first load based on the
  initial `memory_count` status payload.
- Memory list items now wrap long lines cleanly inside the side panel.
- The HTTP and WebSocket ports now read from `INANNA_HTTP_PORT` and
  `INANNA_WS_PORT`, and the server injects the WebSocket port into the HTML.
- The forget flow now shows the temporary removing state correctly before the
  memory panel settles into its empty state.

## Decisions Made

- DECISION POINT: `inanna/identity.py` still declared the legacy Phase 9 name.
  The phase document required the banner to come from `identity.CURRENT_PHASE`,
  so the shared constant had to be updated to the active Cycle 2 Phase 2 name.
- DECISION POINT: `inanna/tests/test_identity.py` still asserted the old
  "Complete Presence" phase label. Updating that one phase-aligned expectation
  was necessary to satisfy the phase's own requirement that the existing test
  suite pass.

## Boundaries That Felt Unclear

- The phase document marked `identity.py` and `tests/` as no-change areas, but
  the repository still shipped stale phase truth in both places. Without those
  minimal corrections, the banner requirement and the "all tests pass"
  requirement could not both be met.
- `ui_main.py` opens a browser automatically while the current static server is
  single-threaded. Verification therefore used `ui_main.py` for clean-start
  confirmation and a separate `start_server()` run for isolated browser
  automation against the same code.

## Verification

- `py -3 -m unittest discover -s tests` passed from `inanna/` with 42 tests.
- `py -3 ui_main.py` started cleanly in an isolated verification copy with
  `INANNA_HTTP_PORT=18180` and `INANNA_WS_PORT=18181`. Stdout reported the
  configured ports and stderr remained empty.
- A browser-level verification run against an isolated temp copy on
  `http://localhost:18280` confirmed:
  - the phase banner displayed `Cycle 2 — Phase 2 — The Refined Interface`
  - the served HTML injected `data-ws-port="18281"`
  - the startup system message reported 1 approved memory record
  - `.record-list li` computed to `word-break: break-word` and
    `white-space: pre-wrap`
  - assistant markdown rendered `**bold**` as `<strong>` and preserved line
    breaks
  - the forget flow completed end-to-end: confirm appeared, a pending forget
    proposal was created, approval removed the memory record, the temporary
    `.removing` class appeared, and both memory/proposal panels settled to
    their empty states

## Proposals For Phase 2.3

- Replace the single-threaded static HTTP server with a threaded variant so
  multiple local clients and verification tooling do not contend for one open
  connection.
- Add a lightweight browser regression harness for the UI protocol and consent
  flows so startup status, markdown rendering, and forget-cycle behavior stay
  covered as the interface grows.

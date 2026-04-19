# Cycle 3 Phase 3.4 Report

## What Was Built

Cycle 3 Phase 3.4 turned the proposal panel into a readable dashboard:

- Updated `inanna/main.py` so `proposal-history` is now a command alias
  for the full proposal history report, `STARTUP_COMMANDS` includes the
  new command, and the CLI `status` output now includes total,
  approved, rejected, and pending proposal counts.
- Updated `inanna/core/state.py` so the capabilities line includes
  `proposal-history`, and the rendered status report now exposes the
  proposal count breakdown.
- Updated `inanna/ui/server.py` with a new `proposal-history`
  WebSocket command that returns the full proposal history payload from
  disk, sorted oldest first, and enriched the status payload with
  `pending_proposals`, `total_proposals`, `approved_proposals`, and
  `rejected_proposals`.
- Updated `inanna/ui/static/index.html` so the proposals panel now has:
  filter tabs for all/pending/approved/rejected, status badges,
  approve/reject buttons only for pending proposals, a live pending
  count badge, a `load full history` button, and human-readable
  timestamp formatting for proposal and memory timestamps.
- Updated `inanna/identity.py` to the shared Phase 3.4 banner.
- Updated the phase-aligned tests in `test_commands.py`,
  `test_identity.py`, and `test_proposal.py`.

## Verification

- `py -3 -m unittest discover -s tests`
  - Result: 115 tests passed
- Focused runtime smoke check in a temporary runtime confirmed:
  - `proposal-history` prints the same full proposal history report as
    `history`
  - `status` now reports `Pending proposals`, `Total proposals`,
    `Approved proposals`, and `Rejected proposals` with the expected
    values after proposal state changes

## Boundaries Kept

- No proposal creation flow was added to the UI.
- No proposal editing was introduced.
- No bulk approve/reject operation was added.
- No search, export, or storage-format change was introduced.
- No files outside the Phase 3.4 permitted set were modified.

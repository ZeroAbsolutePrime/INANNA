# Cycle 5 - Phase 5.1 - The Console Surface

## Built

- Added `inanna/ui/static/console.html` as a second browser surface with four placeholder panels: tools, network, faculties, and processes.
- Added `/console` handling in `inanna/ui/server.py` and a WebSocket-side console gate for Guardian and Operator roles only.
- Added a role-gated `[ console ]` launcher to the main interface header in `inanna/ui/static/index.html`.
- Updated `inanna/identity.py` and `inanna/tests/test_identity.py` to reflect the Phase 5.1 identity banner.

## Not Built

- No tool execution
- No network scanning
- No new WebSocket commands
- No Faculty deployment or process monitoring logic

## Verification

- `py -3 -m unittest discover -s tests`

## Notes

- The console uses the existing WebSocket server and status payload.
- Unauthorized console connections receive `console_access_denied` and redirect back to `/`.

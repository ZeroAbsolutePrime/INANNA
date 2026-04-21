# Cycle 7 Phase 7.6 Report

## Phase

Cycle 7 - Phase 7.6 - Authentication & Login

## Summary

Implemented the authentication boundary for INANNA NYX with a dedicated
login page, PBKDF2-HMAC-SHA256 password storage, seeded Guardian credentials,
HTTP route gating, and WebSocket session enforcement.

## Changes

- Added `inanna/core/auth.py` with:
  - `AuthRecord`
  - `AuthStore`
  - PBKDF2-HMAC-SHA256 password hashing and verification helpers
- Seeded `ZAERA / ETERNALOVE` during `InterfaceServer` startup.
- Added shared cookie-token parsing and auth restoration in `inanna/ui/server.py`.
- Added HTTP auth routes:
  - `GET /`
  - `GET /login`
  - `POST /login`
  - `GET /app`
- Enforced authenticated WebSocket initialization before any status or memory
  payload is sent.
- Added `inanna/ui/static/login.html` as the standalone login experience with:
  - `𒀭` glyph
  - `INANNA NYX` title
  - `SOVEREIGN INTELLIGENCE` subtitle
- Removed the legacy `login-overlay` markup and logic from
  `inanna/ui/static/index.html`.
- Updated `inanna/identity.py` for the active phase.
- Added `inanna/tests/test_auth.py` with 17 auth tests covering:
  - password hashing
  - auth store behavior
  - HTTP login routes
  - WebSocket auth gating
- Updated `inanna/tests/test_guardian.py` so existing initial-state tests use
  authenticated cookies under the new Phase 7.6 contract.
- Updated `inanna/tests/test_identity.py` for the phase assertion.

## Verification

Executed from `C:\Users\Zohar\Dropbox\Windows11\REPOS\ABZU\INANNA`:

- `py -3 -m py_compile inanna\core\auth.py inanna\ui\server.py inanna\identity.py inanna\tests\test_auth.py inanna\tests\test_identity.py`

Executed from `C:\Users\Zohar\Dropbox\Windows11\REPOS\ABZU\INANNA\inanna`:

- `py -3 -m unittest tests.test_auth tests.test_identity`
- `py -3 -m unittest tests.test_auth tests.test_guardian tests.test_identity`
- `py -3 -m unittest discover -s tests`

Results:

- Focused auth + identity suite: 35 tests passed
- Focused auth + guardian + identity suite: 43 tests passed
- Full suite: 429 tests passed

## Constraints Respected

- No `voice/` files were modified
- No `console.html` changes were made
- `index.html` was only changed to remove the login overlay path
- No new runtime capability beyond authentication/login was added

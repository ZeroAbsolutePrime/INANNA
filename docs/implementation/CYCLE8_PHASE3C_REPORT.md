# Cycle 8 Phase 8.3c Report

## Phase

Cycle 8 - Phase 8.3c - The Startup Fix

## Completed

- Reduced `Engine.verify_connection()` to a strict `2s` reachability check
- Wrapped NAMMU intent extraction behind a `3s` daemon-thread timeout so routing falls through to regex instead of blocking
- Made `sync_profile_grounding()` conditional during `InterfaceServer.__init__` so startup skips that path when the model is not connected
- Added startup timing and model-mode output in `inanna/ui_main.py`
- Added focused startup coverage in `inanna/tests/test_startup.py`
- Updated the phase banner in `inanna/identity.py`

## Verification

- `py -3 -m py_compile ...`
- `py -3 -m unittest tests.test_startup tests.test_identity`
- `py -3 -m unittest discover -s tests`

## Result

- Startup is now bounded even on slow hardware
- NAMMU routing no longer blocks the session path waiting for a slow model
- Regex fallback remains the correct behavior when the model is unavailable or too slow

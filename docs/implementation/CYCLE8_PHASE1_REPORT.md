# Cycle 8 Phase 8.1 Report

## Phase

Cycle 8 - Phase 8.1 - The Desktop Faculty Core

## Delivered

- Added `inanna/core/desktop_faculty.py` with `DesktopFaculty`, `DesktopResult`,
  `WindowsMCPBackend`, `LinuxAtspiBackend`, and `FallbackBackend`.
- Registered five desktop tools in `inanna/config/tools.json`:
  `desktop_open_app`, `desktop_read_window`, `desktop_click`,
  `desktop_type`, and `desktop_screenshot`.
- Added desktop routing hints to `inanna/config/governance_signals.json`.
- Wired desktop tool detection and execution into `inanna/main.py` and
  `inanna/ui/server.py`, including proposal logic, tool formatting,
  context lines, and audit entries.
- Added `pywinauto>=0.6.8` to `inanna/requirements.txt`.
- Updated `inanna/core/help_system.py` with desktop help coverage.
- Updated `inanna/identity.py` to the active Cycle 8.1 phase and
  included desktop tools in the advertised capability surface.
- Added `inanna/tests/test_desktop_faculty.py` with 20 offline tests.
- Updated affected expectations in `test_identity.py`, `test_operator.py`,
  and `test_commands.py` for the expanded 23-tool registry.

## Verification

- `py -3 -m py_compile inanna/main.py inanna/ui/server.py inanna/core/desktop_faculty.py inanna/core/help_system.py inanna/identity.py inanna/tests/test_desktop_faculty.py`
- `py -3 -m unittest tests.test_desktop_faculty tests.test_identity tests.test_operator tests.test_commands`
- `py -3 -m unittest discover -s tests`

## Result

- Full suite passed: 452 tests green.
- No UI changes were made.
- No voice or auth changes were made.
- Desktop tests remain fully offline and do not make real UI automation calls.

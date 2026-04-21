# Cycle 7 Phase 7.3 Report

## Phase

Cycle 7 - Phase 7.3 - The Process Faculty

## Summary

Implemented the governed Process Faculty for INANNA NYX.
INANNA can now inspect running processes and overall system health without approval,
while process termination and shell command execution remain proposal-gated.

## Changes

- Added `inanna/core/process_faculty.py` with:
  - `ProcessFaculty`
  - `ProcessRecord`
  - `SystemInfo`
  - `ProcessResult`
- Implemented process operations:
  - `list_processes`
  - `system_info`
  - `kill_process`
  - `run_command`
- Added graceful fallback behavior when `psutil` is unavailable.
- Registered the four process tools in `inanna/config/tools.json`.
- Added process domain hints to `inanna/config/governance_signals.json`.
- Added `psutil>=5.9` to `inanna/requirements.txt`.
- Wired Process Faculty routing into:
  - `inanna/main.py`
  - `inanna/ui/server.py`
- Updated `inanna/core/help_system.py` with process guidance and governance notes.
- Updated `inanna/identity.py` for the active phase and permitted tool surface.
- Added `inanna/tests/test_process_faculty.py` with 20 tests.
- Expanded related coverage in:
  - `inanna/tests/test_commands.py`
  - `inanna/tests/test_identity.py`
  - `inanna/tests/test_operator.py`

## Governance Outcome

- Observation tools:
  - `list_processes`
  - `system_info`
  - No approval required
- Action tools:
  - `kill_process`
  - `run_command`
  - Always require proposal approval
- `run_command` blocks elevation attempts such as `sudo`, `doas`, and `runas`.

## Verification

Executed from `C:\Users\Zohar\Dropbox\Windows11\REPOS\ABZU\INANNA\inanna`:

- `py -3 -m unittest tests.test_process_faculty tests.test_commands tests.test_identity tests.test_operator`
- `py -3 -m unittest discover -s tests`
- `py -3 -m py_compile main.py ui\server.py core\process_faculty.py core\help_system.py identity.py tests\test_process_faculty.py tests\test_commands.py tests\test_identity.py tests\test_operator.py`
  - used a temporary `PYTHONPYCACHEPREFIX` because Windows denied direct writes into an existing `__pycache__` target

Results:

- Focused suite: 118 tests passed
- Full suite: 375 tests passed

## Constraints Respected

- No UI files were modified
- Governance architecture was not rewritten
- `filesystem_faculty.py` was left untouched

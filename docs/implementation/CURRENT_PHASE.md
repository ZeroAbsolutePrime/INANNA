# CURRENT PHASE: Cycle 7 - Phase 7.8 - The Capability Proof
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Replaces: Cycle 7 Phase 7.7 - The UX Polish Pass (COMPLETE)**

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — implement verification script and fix any failures
TESTER:     Codex — run verify_cycle7.py and all integration checks
VERIFIER:   Command Center — confirm Cycle 7 is complete

BUILDER forbidden from:
  - Adding new capabilities
  - Modifying voice/ directory
  - Changing auth behavior

---

## What This Phase Is

Cycles 1-6 each ended with a verify_cycleN.py script that proved
the cycle was complete. Cycle 7 needs the same.

Phase 7.8 has two parts:
1. Write verify_cycle7.py — a comprehensive check of all Cycle 7
   capabilities
2. Run it, fix any failures found, confirm all checks pass

This phase declares Cycle 7 complete and opens the path to Cycle 8.

---

## Part A — verify_cycle7.py

Create: inanna/verify_cycle7.py

The script must verify every Cycle 7 deliverable systematically.
It should print PASS/FAIL for each check and end with a count.

### Checks to include:

**Section 1 — Phase 7.1: NixOS Configuration**
- nixos/configuration.nix exists
- nixos/README.md exists
- nixos/inanna-nyx.service exists
- nixos/install.sh exists
- configuration.nix contains inanna-nyx service definition
- configuration.nix contains port 8080
- configuration.nix contains port 8081

**Section 2 — Phase 7.2: File System Faculty**
- core/filesystem_faculty.py exists
- FileSystemFaculty can be instantiated
- FileSystemFaculty has read_file method
- FileSystemFaculty has list_dir method
- FileSystemFaculty has file_info method
- FileSystemFaculty has search_files method
- FileSystemFaculty has write_file method
- is_safe_read(home directory) returns True
- is_forbidden(/etc/shadow) returns True
- read_file on a temp file returns correct content
- write_file writes content correctly
- write_file respects overwrite guard
- list_dir returns entries
- Tools registered: read_file, list_dir, file_info, search_files, write_file

**Section 3 — Phase 7.3: Process Faculty**
- core/process_faculty.py exists
- ProcessFaculty can be instantiated
- system_info() returns success
- system_info() returns hostname
- list_processes() returns at least 1 process
- kill_process with invalid PID returns failure gracefully
- run_command("echo test7") returns success
- run_command stdout contains "test7"
- Tools registered: list_processes, system_info, kill_process, run_command

**Section 4 — Phase 7.4: Package Faculty**
- core/package_faculty.py exists
- PackageFaculty can be instantiated
- Package manager detected (not "unknown")
- search returns PackageResult
- format_result returns non-empty string
- Tools registered: search_packages, list_packages, install_package,
  remove_package, launch_app

**Section 5 — Phase 7.5: Voice Listener**
- voice/__init__.py exists
- voice/listener.py exists
- voice/README.md exists
- VoiceListener instantiates with default model_size "base"
- SAMPLE_RATE == 16000
- MIN_SPEECH_SECONDS == 0.5
- VoiceListener has run method
- VoiceListener has transcribe method

**Section 6 — Phase 7.6: Authentication & Login**
- core/auth.py exists
- ui/static/login.html exists
- AuthStore can be instantiated
- hash_password returns salt:hash format
- verify_password returns True for correct password
- verify_password returns False for wrong password
- authenticate returns record for ZAERA / ETERNALOVE
- authenticate returns None for wrong password
- login.html contains INANNA NYX
- login.html contains POST /login
- login.html does NOT contain __CURRENT_PHASE__ literally
  (it must be replaced at serve time, but the template has it)
  — check that it has the placeholder correctly placed

**Section 7 — Phase 7.7: UX Polish**
- ui/server.py contains "OPERATOR FACULTY COMPLETED" or "TOOL EXECUTION COMPLETE"
- ui/server.py contains "_last_package_context"
- ui/server.py contains "_detect_package_followup" or "followup"
- ui/static/index.html contains "proposalPulse"
- ui/static/index.html contains "inanna_sp" or "sp_state"
- core/help_system.py returns topic header with "INANNA NYX"
- Welcome message uses dynamic tool count

**Section 8 — Software Registry**
- core/software_registry.py exists
- SoftwareRegistry can be instantiated
- is_installed returns None when not loaded (no blocking)
- load() runs without error
- all_entries() returns at least 1 entry after load

**Section 9 — Tool Count**
- Total tools registered: exactly 18
- PACKAGE_TOOL_NAMES contains launch_app
- FILESYSTEM_TOOL_NAMES contains all 5 file tools
- PROCESS_TOOL_NAMES contains all 4 process tools

**Section 10 — Full Test Suite**
- py -3 -m unittest discover -s tests exits with code 0
- Test count >= 429

### Script structure:

```python
#!/usr/bin/env python3
"""
verify_cycle7.py — Cycle 7 Capability Proof
Verifies all Phase 7.1-7.8 deliverables.

Usage: py -3 verify_cycle7.py
Expected: ALL CHECKS PASS
"""
import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "inanna"))

PASS = 0
FAIL = 0
SECTION = ""

def section(name):
    global SECTION
    SECTION = name
    print(f"\n  {name}")
    print("  " + "-" * (len(name)))

def check(label, value, expected=True):
    global PASS, FAIL
    ok = bool(value) == bool(expected) if expected is True or expected is False else value == expected
    status = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
        print(f"    [FAIL] {label}")
        if expected is not True and expected is not False:
            print(f"           expected: {expected!r}")
            print(f"           got:      {value!r}")
        return
    # Only print fails verbosely; pass is brief
    print(f"    [pass] {label}")

# ... all checks ...

if FAIL == 0:
    print(f"\n  ✦ ALL {PASS} CHECKS PASS — Cycle 7 is complete.")
    print(f"  Ready for Cycle 8.")
else:
    print(f"\n  ✗ {FAIL} check(s) failed. Fix before declaring Cycle 7 complete.")
    sys.exit(1)
```

---

## Part B — Integration Test Runner

Enhance inanna/run_integration_tests.py to cover all 9 Use Cases:

```
UC-01: File read, list, write via natural language
UC-02: Package install via natural language (winget)
UC-03: System status query
UC-04: (Voice — skip, deferred)
UC-05: Document read summary (basic)
UC-06: Web search with summary
UC-07: Process list and system info
UC-08: INANNA explains herself
UC-09: Profile system persistence
```

For each UC, add a WebSocket test that:
1. Sends the natural language input
2. Waits for the response
3. Checks the response contains expected content
4. Reports PASS/FAIL

---

## Part C — Fix any failures found

After running verify_cycle7.py, if any checks fail, fix them
before reporting completion. Common expected failures:
- Software registry entry count on minimal systems
- Process faculty psutil availability

---

## Part D — Update identity.py

CURRENT_PHASE = "Cycle 7 - Phase 7.8 - The Capability Proof"

---

## Part E — Cycle 7 Completion Record

Create: docs/cycle7_completion.md

Document:
- All Phase 7.1-7.8 completion dates
- Final test count (431+)
- verify_cycle7.py check count and result
- Known gaps/deferred items (voice activation, NixOS deployment)
- What Cycle 8 will build

---

## Permitted file changes

inanna/verify_cycle7.py              <- NEW
inanna/run_integration_tests.py      <- MODIFY (expand UC coverage)
inanna/identity.py                   <- MODIFY
inanna/ui/server.py                  <- MODIFY (only if verify fails)
docs/cycle7_completion.md            <- NEW

---

## Definition of Done

- [ ] verify_cycle7.py exists and runs
- [ ] ALL checks in verify_cycle7.py pass
- [ ] run_integration_tests.py covers UC-01 through UC-09
- [ ] docs/cycle7_completion.md written
- [ ] CURRENT_PHASE updated
- [ ] All unit tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle7-phase8-complete

---

## Handoff

Commit: cycle7-phase8-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE7_PHASE8_REPORT.md

After this commit, Cycle 7 is declared complete.
The next CURRENT_PHASE.md will open Cycle 8.

---

## What Cycle 8 Will Build

Cycle 8 — The Connected Intelligence:
  8.1  Document Faculty     read/write PDF, DOCX, TXT
  8.2  Email Faculty        local email (msmtp + notmuch)
  8.3  Calendar Faculty     local calendar (vdir/khal)
  8.4  Browser Faculty      open URLs, read page content
  8.5  Telegram Integration send/receive messages
  8.6  LibreOffice Bridge   open/edit/save documents

Each Faculty follows the same pattern established in Cycle 7:
governance-first, proposal for destructive operations,
observation for read operations.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-21*
*Cycle 7 ends where it promised to end:*
*with proof.*
*Every Phase verified.*
*Every tool tested.*
*Every capability confirmed.*
*INANNA knows what she can do.*
*Now she does it.*

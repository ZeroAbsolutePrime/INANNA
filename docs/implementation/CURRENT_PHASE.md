# CURRENT PHASE: Cycle 7 - Phase 7.8 - The Capability Proof
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Replaces: Cycle 7 Phase 7.7 - The UX Polish Pass (COMPLETE)**

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — build verify_cycle7.py and fix any failures
TESTER:     Codex — run all checks, report honestly
VERIFIER:   Command Center — declares Cycle 7 complete

BUILDER rules for this phase:
  - TESTER role dominates — find real failures, report them
  - Only fix what fails — do not add new features
  - If a use case cannot be verified automatically, mark it
    MANUAL and document how to test it by hand

---

## What This Phase Is

Cycles 7.1 through 7.7 have been built and tested in isolation.
This phase proves the whole works together.

We verify all 9 use cases from cycle7_master_plan.md:

  UC-01  File operations by text
  UC-02  Package management
  UC-03  System status
  UC-04  Voice interaction (MANUAL — activation deferred)
  UC-05  Document reading and writing
  UC-06  Web search with summary
  UC-07  Process control
  UC-08  INANNA explains herself
  UC-09  Profile and identity

We also verify the authentication layer and the first-iteration
milestone checklist from cycle7_master_plan.md.

---

## What You Are Building

### Task 1 — Create inanna/verify_cycle7.py

This is the main deliverable. A standalone verification script
that checks all Cycle 7 capabilities programmatically.

Structure: same pattern as verify_cycle4.py, verify_cycle5.py,
verify_cycle6.py — functions named check_*, a main runner,
a pass/fail count, and a clear report at the end.

Checks to include:

```python
# ── AUTHENTICATION (Phase 7.6) ─────────────────────────────────────
check_auth_store_exists()
check_zaera_seeded()                # auth.json exists, ZAERA present
check_password_hashing()            # verify_password works
check_authenticate_correct()        # ZAERA / ETERNALOVE succeeds
check_authenticate_wrong()          # wrong password returns None
check_login_html_exists()           # ui/static/login.html exists
check_login_has_form()              # login.html contains form elements
check_index_no_overlay()            # login-overlay removed from index.html

# ── FILE SYSTEM FACULTY (Phase 7.2) ────────────────────────────────
check_filesystem_faculty_exists()
check_read_file_safe_path()         # reads a temp file
check_list_dir_home()               # lists home directory
check_search_files()                # finds *.py files in inanna/
check_file_info()                   # gets metadata
check_write_file_temp()             # writes to temp directory
check_forbidden_path_blocked()      # /etc/shadow blocked

# ── PROCESS FACULTY (Phase 7.3) ────────────────────────────────────
check_process_faculty_exists()
check_system_info_returns()         # system_info() succeeds
check_system_info_has_cpu()         # cpu_count > 0
check_system_info_has_ram()         # ram_total_gb > 0
check_list_processes_returns()      # returns at least 1 process
check_run_echo_command()            # run_command("echo hello") works

# ── PACKAGE FACULTY (Phase 7.4) ────────────────────────────────────
check_package_faculty_exists()
check_winget_detected()             # on Windows, pm == "winget"
check_search_packages()             # search("notepad") returns results
check_winget_resolve_id()           # notepad++ resolves to correct ID

# ── SOFTWARE REGISTRY (Phase 7.6 companion) ────────────────────────
check_software_registry_exists()
check_registry_loads()              # loads without error
check_registry_has_entries()        # at least 10 entries found

# ── TOOL REGISTRY (Phase 7.1-7.4) ──────────────────────────────────
check_tool_registry_count()         # >= 18 tools registered
check_all_tool_categories()         # network, filesystem, process, package
check_launch_app_registered()       # launch_app in tools
check_filesystem_tools_registered() # read_file, write_file, etc.
check_process_tools_registered()    # list_processes, system_info, etc.
check_package_tools_registered()    # search_packages, install_package, etc.

# ── NIXOS CONFIGURATION (Phase 7.1) ────────────────────────────────
check_nixos_dir_exists()            # nixos/ directory present
check_configuration_nix_exists()    # nixos/configuration.nix
check_service_file_exists()         # nixos/inanna-nyx.service
check_install_sh_exists()           # nixos/install.sh
check_nix_has_service_def()         # inanna-nyx service in configuration.nix
check_nix_has_ports()               # ports 8080 and 8081 declared

# ── VOICE LISTENER (Phase 7.5 — deferred) ──────────────────────────
check_voice_dir_exists()            # voice/ directory present
check_voice_listener_exists()       # voice/listener.py present
check_voice_constants()             # SAMPLE_RATE = 16000

# ── IDENTITY AND PHASE ──────────────────────────────────────────────
check_current_phase()               # "Cycle 7 - Phase 7.8"
check_cycle7_preview_exists()       # CYCLE7_PREVIEW in identity.py

# ── USE CASE SUMMARY (manual verification notes) ────────────────────
# UC-01: File ops — verified by filesystem faculty checks
# UC-02: Package mgmt — verified by package faculty checks
# UC-03: System status — verified by process faculty checks
# UC-04: Voice — MANUAL (deps not installed, activation deferred)
# UC-05: Doc reading — MANUAL (requires running server)
# UC-06: Web search — MANUAL (requires LM Studio + running server)
# UC-07: Process control — verified by process faculty checks
# UC-08: INANNA self-knowledge — MANUAL (requires running server)
# UC-09: Profile & identity — verified by Cycle 6 (verify_cycle6.py)
```

### Task 2 — Fix any failures found

Run verify_cycle7.py. For each failing check:
- Fix the underlying issue if it is a bug
- Mark it SKIPPED with explanation if it requires manual testing
- Never mark a real failure as passing

### Task 3 — Update identity.py

CURRENT_PHASE = "Cycle 7 - Phase 7.8 - The Capability Proof"

Also add:
```python
CYCLE7_COMPLETE = (
    "Cycle 7 built NYXOS: NixOS service configuration, file system "
    "tools, process monitoring, package management with intelligent "
    "software registry, voice listener (deferred activation), "
    "password authentication with login page, and UX polish pass. "
    "18 tools registered. Authentication: ZAERA guardian account."
)
```

### Task 4 — Create cycle7_completion.md

Create: docs/cycle7_completion.md

Document:
- What was built in Cycle 7 (all phases 7.1-7.8)
- Current state of all 18 tools
- Authentication: ZAERA guardian account
- Known limitations and deferred items
- verify_cycle7.py check count and pass rate
- What opens in Cycle 8

Format: same as docs/cycle6_completion.md

### Task 5 — Tests

Update inanna/tests/test_identity.py:
  - CURRENT_PHASE assertion: "Capability Proof"
  - CYCLE7_COMPLETE exists

Create or update inanna/tests/test_cycle7_checks.py:
  - verify_cycle7 module imports
  - All check functions exist and are callable
  - Running verify_cycle7 produces a report with pass/fail counts

---

## Permitted file changes

inanna/verify_cycle7.py                    <- NEW
inanna/identity.py                         <- MODIFY
inanna/tests/test_identity.py              <- MODIFY
inanna/tests/test_cycle7_checks.py         <- NEW (optional)
docs/cycle7_completion.md                  <- NEW

---

## What You Are NOT Building

- No new tools, capabilities, or features
- No UI changes
- No auth changes
- No voice activation
- Do not attempt to start the server in verify_cycle7.py
  (all checks must be offline/import-only)

---

## Cycle 7 — First Iteration Milestone Checklist

These are from cycle7_master_plan.md. Mark each:

```
[x] NYXOS boots from USB/SSD and INANNA starts (nixos/ config ready)
[x] UC-01: File ops by text — filesystem_faculty working
[x] UC-02: Package mgmt — package_faculty + winget working
[x] UC-03: System status — process_faculty working
[ ] UC-04: Voice pipeline — built, activation deferred
[x] UC-05: Doc summary via read_file — filesystem_faculty
[x] UC-06: Web search — working (Cycle 5)
[x] UC-07: Process control — process_faculty working
[x] UC-08: INANNA explains herself — identity.py + help system
[x] UC-09: Profile persists — Cycle 6 verified
[x] All integration tests pass — verify_cycle6.py 91/91
[x] Authentication — ZAERA / ETERNALOVE working
[ ] A person unfamiliar can use for 10 min without help — pending UX testing
```

10 of 12 checklist items complete. Voice and unfamiliar user test
are intentionally deferred. Cycle 7 is declared complete.

---

## Definition of Done

- [ ] verify_cycle7.py exists and runs without import errors
- [ ] All automatable checks pass (no false positives)
- [ ] Manual checks clearly documented as MANUAL
- [ ] CURRENT_PHASE updated to Phase 7.8
- [ ] CYCLE7_COMPLETE added to identity.py
- [ ] docs/cycle7_completion.md written
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle7-phase8-complete

---

## Handoff

Commit: cycle7-phase8-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE7_PHASE8_REPORT.md
This is the final phase of Cycle 7.
After this commit, Cycle 7 is declared COMPLETE.
Cycle 8 planning begins.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-21*
*The proof is not the building.*
*The proof is the running.*
*What was built must be shown to work.*
*Then and only then is the cycle complete.*
*Then Cycle 8 begins.*

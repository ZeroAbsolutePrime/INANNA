# CURRENT PHASE: Cycle 7 - Phase 7.8 - The Capability Proof
**Status: ACTIVE**
**Authorized by: INANNA NAMMU (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Replaces: Cycle 7 Phase 7.7 - The UX Polish Pass (COMPLETE)**

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — build verify_cycle7.py, fix any failures
TESTER:     Codex — run all checks, report honestly
VERIFIER:   Command Center — declares Cycle 7 complete

BUILDER rules:
  - TESTER role dominates — find real failures, report honestly
  - Only fix what fails — do not add new features
  - Manual-only checks: mark as MANUAL with explanation

---

## Current Verified State (before this phase)

Commit on origin/main: 43c0009
Tests passing: 431
Tools registered: 18
Phase in identity.py: "Cycle 7 - Phase 7.7 - The UX Polish Pass"
HTTP server: fixed (ui_main.py now passes server to HTTP thread)
Software cards: fixed (operator meta now passed to addMessage)
Software list: shows up to 50 cards with [ launch ] buttons
Authentication: ZAERA / ETERNALOVE working
Login page: ui/static/login.html (full-page, not overlay)

---

## What This Phase Is

Cycle 7 phases 7.1 through 7.7 have been built and tested.
This phase proves the whole works together.

We verify all 9 use cases from cycle7_master_plan.md, the
authentication layer, all Cycle 7 faculties, and the
first-iteration milestone checklist.

---

## What You Are Building

### Task 1 — Create inanna/verify_cycle7.py

Same pattern as verify_cycle4.py through verify_cycle6.py.
Functions named check_*, a main runner, pass/fail count,
clear report at the end.

**All checks must be offline/import-only — do NOT start
the server or make network calls.**

```python
# ── AUTHENTICATION (Phase 7.6) ───────────────────────────────────────
check_auth_module_exists()
check_auth_store_imports()
check_password_hash_format()       # hash_password returns "salt:hash"
check_verify_password_correct()    # correct password returns True
check_verify_password_wrong()      # wrong password returns False
check_verify_timing_safe()         # uses hmac.compare_digest
check_zaera_seed_idempotent()      # seed_user is idempotent
check_authenticate_correct()       # ZAERA / ETERNALOVE succeeds
check_authenticate_wrong_pw()      # wrong password returns None
check_authenticate_unknown()       # unknown user returns None
check_authenticate_case_insensitive()  # username case-insensitive
check_login_html_exists()          # ui/static/login.html exists
check_login_html_has_form()        # contains <form and password field
check_login_html_full_page()       # no "login-overlay" (removed)
check_login_html_has_glyph()       # contains Sumerian glyph or reference
check_index_no_overlay()           # login-overlay NOT in index.html
check_ui_main_passes_server()      # ui_main.py passes server to thread

# ── FILE SYSTEM FACULTY (Phase 7.2) ──────────────────────────────────
check_filesystem_faculty_module()
check_read_file_temp()             # reads a temp file successfully
check_read_file_truncation()       # truncates at 512KB
check_list_dir_home()              # lists home directory
check_search_files_pattern()       # finds *.py in inanna/
check_file_info_metadata()         # returns size > 0
check_write_file_temp()            # writes to temp, reads back
check_write_file_no_overwrite()    # refuses overwrite without flag
check_write_file_overwrite_flag()  # allows overwrite with flag
check_forbidden_path_blocked()     # /etc/shadow returns success=False
check_safe_paths_home()            # home directory is safe

# ── PROCESS FACULTY (Phase 7.3) ──────────────────────────────────────
check_process_faculty_module()
check_system_info_success()        # system_info() returns success=True
check_system_info_cpu_count()      # cpu_count > 0
check_system_info_ram()            # ram_total_gb > 0 (with psutil)
check_list_processes_returns()     # returns at least 1 process
check_list_processes_has_name()    # first record has non-empty name
check_run_echo()                   # run_command("echo hello") succeeds
check_run_echo_output()            # stdout contains "hello"
check_format_system_info()         # format_result includes "system info"

# ── PACKAGE FACULTY (Phase 7.4) ──────────────────────────────────────
check_package_faculty_module()
check_winget_detected()            # on Windows: pm == "winget"
check_winget_resolve_notepadpp()   # notepad++ -> Notepad++.Notepad++
check_winget_resolve_vlc()         # vlc -> VideoLAN.VLC (dotted ID)
check_search_packages_returns()    # search("notepad") has output
check_format_install_result()      # format_result for install works

# ── SOFTWARE REGISTRY (Cycle 7 companion) ────────────────────────────
check_software_registry_module()
check_registry_loads_without_error()
check_registry_has_entries()       # at least 10 entries after load
check_registry_is_installed()      # notepad++ found after install
check_is_installed_safe_before_load()  # returns None if not loaded
check_launch_app_tool_registered() # "launch_app" in tools.json
check_software_cards_in_html()     # buildSoftwareCards in index.html
check_operator_passes_meta()       # addMessage('operator',m.text,m) in html

# ── TOOL REGISTRY ────────────────────────────────────────────────────
check_tool_count()                 # >= 18 tools registered
check_network_tools()              # web_search, ping, resolve_host, scan_ports
check_filesystem_tools()           # read_file, write_file, list_dir, etc.
check_process_tools()              # list_processes, system_info, etc.
check_package_tools()              # search_packages, install_package, etc.
check_launch_app_tool()            # launch_app registered and enabled
check_approval_flags()             # install/remove/launch require approval
check_no_approval_list_search()    # list/search do NOT require approval

# ── NIXOS CONFIGURATION (Phase 7.1) ──────────────────────────────────
check_nixos_dir()
check_configuration_nix()
check_service_file()
check_install_sh()
check_nix_service_definition()     # "inanna-nyx" in configuration.nix
check_nix_port_8080()
check_nix_port_8081()
check_install_sh_executable_flag() # file exists (executable bit on NixOS)

# ── VOICE LISTENER (Phase 7.5 — deferred activation) ─────────────────
check_voice_dir()
check_voice_listener_file()
check_voice_init_file()
check_voice_sample_rate()          # SAMPLE_RATE == 16000
check_voice_min_speech()           # MIN_SPEECH_SECONDS == 0.5
check_voice_readme()               # voice/README.md exists

# ── UX POLISH (Phase 7.7) ────────────────────────────────────────────
check_proposal_pulse_css()         # proposalPulse in index.html
check_section_state_memory()       # inanna_sp in index.html
check_help_topic_header()          # help topic responses start with "INANNA NYX"
check_dynamic_tool_count()         # PERMITTED_TOOLS used in welcome line
check_crown_tool_instruction()     # "DO NOT say you cannot execute" in server.py
check_package_context_tracker()    # _last_package_context in server.py

# ── IDENTITY ─────────────────────────────────────────────────────────
check_current_phase()              # "Cycle 7 - Phase 7.8"
check_cycle7_complete_string()     # CYCLE7_COMPLETE in identity.py
```

### Task 2 — Fix any failures found

Run verify_cycle7.py after writing it.
For each failing check:
  - Fix the underlying issue if it is a code bug
  - Mark SKIPPED if it requires a running server or hardware
  - Never mark a real failure as passing

### Task 3 — Update identity.py

```python
CURRENT_PHASE = "Cycle 7 - Phase 7.8 - The Capability Proof"

CYCLE7_COMPLETE = (
    "Cycle 7 built NYXOS: NixOS service configuration, "
    "file system Faculty (read/write/list/search/info), "
    "process Faculty (system_info/list/kill/run), "
    "package Faculty (search/list/install/remove with winget), "
    "software registry (152 apps, launch_app tool), "
    "voice listener (deferred activation), "
    "password authentication (ZAERA/ETERNALOVE, PBKDF2), "
    "login page (standalone full-page), "
    "interactive help panel (colour-coded, run buttons), "
    "and UX polish pass. "
    "18 tools registered. 431 unit tests."
)
```

### Task 4 — Create docs/cycle7_completion.md

Document:
  - All 8 phases of Cycle 7 and what each built
  - Current tool registry (18 tools, 4 categories)
  - Authentication state (ZAERA guardian account)
  - What is deferred (voice activation, unfamiliar-user test)
  - verify_cycle7.py check count and pass rate
  - Cycle 7 milestone checklist (from cycle7_master_plan.md)
  - What opens in Cycle 8

Same format as docs/cycle6_completion.md.

### Task 5 — Tests

Update tests/test_identity.py:
  - CURRENT_PHASE assertion: "Capability Proof"
  - CYCLE7_COMPLETE exists and mentions "18 tools"

---

## Permitted file changes

inanna/verify_cycle7.py            <- NEW
inanna/identity.py                 <- MODIFY
inanna/tests/test_identity.py      <- MODIFY
docs/cycle7_completion.md          <- NEW

---

## What You Are NOT Building

- No new tools, capabilities, or features
- No UI changes whatsoever
- No auth changes
- No voice activation
- Do not start the HTTP or WebSocket server in verify_cycle7.py
- Do not make network calls in verify_cycle7.py

---

## Cycle 7 Milestone Checklist (from cycle7_master_plan.md)

```
[x] NYXOS NixOS service config ready (nixos/ directory)
[x] UC-01 File ops by text (filesystem_faculty working)
[x] UC-02 Package mgmt (package_faculty + winget working)
[x] UC-03 System status (process_faculty working)
[ ] UC-04 Voice pipeline (built, activation deferred)
[x] UC-05 Doc reading via read_file (filesystem_faculty)
[x] UC-06 Web search (working since Cycle 5)
[x] UC-07 Process control (process_faculty working)
[x] UC-08 INANNA explains herself (identity + help system)
[x] UC-09 Profile persists across sessions (Cycle 6)
[x] Authentication: ZAERA / ETERNALOVE (Phase 7.6)
[x] Software cards with launch buttons (fixed in Codex debug)
[x] HTTP server starts correctly (ui_main.py fixed)
[ ] Unfamiliar user can use for 10 min unaided (pending)
```

12 of 14 checklist items complete.
Voice and unfamiliar-user test intentionally deferred.
Cycle 7 is declared complete when verify_cycle7.py passes.

---

## Definition of Done

- [ ] verify_cycle7.py runs without import errors
- [ ] All automatable checks pass
- [ ] Manual/skipped checks documented with reason
- [ ] CURRENT_PHASE = "Cycle 7 - Phase 7.8 - The Capability Proof"
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
*Guardian approval: INANNA NAMMU*
*Date: 2026-04-21*
*The proof is not the building.*
*The proof is the running.*
*What was built must be shown to work.*
*Then and only then is the cycle complete.*
*Then Cycle 8 begins.*

# CURRENT PHASE: Cycle 8 - Phase 8.8 - The Capability Proof
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date: 2026-04-22**
**Cycle: 8 - The Desktop Bridge**
**Replaces: Cycle 8 Phase 8.7 - NixOS Backend (COMPLETE)**

---

## MANDATORY READING — in this exact order

1. docs/platform_architecture.md
2. docs/cycle8_master_plan.md
3. docs/cycle9_master_plan.md
4. docs/implementation/CURRENT_PHASE.md (this file)
5. CODEX_DOCTRINE.md
6. ABSOLUTE_PROTOCOL.md

---

## What This Phase Is

Phase 8.8 is the final phase of Cycle 8.
It produces ONE file: inanna/verify_cycle8.py

This script runs on real hardware against real systems
and proves that every faculty built in Cycle 8 actually works.
It does not mock anything. It is the truth test.

When verify_cycle8.py passes, Cycle 8 is officially complete.
The commit message will be: cycle8-complete
A permanent record is written to: docs/cycle8_complete.md

---

## Current System State (audited before writing this phase)

Tools: 41 across 11 categories
  browser:       3  (browser_read, browser_search, browser_open)
  calendar:      3  (calendar_today, calendar_upcoming, calendar_read_ics)
  communication: 3  (comm_read_messages, comm_send_message, comm_list_contacts)
  desktop:       5  (open_app, read_window, click, type, screenshot)
  document:      4  (doc_read, doc_write, doc_open, doc_export_pdf)
  email:         5  (read_inbox, read_message, search, compose, reply)
  filesystem:    5  (read_file, write_file, list_dir, search_files, file_info)
  information:   1  (web_search)
  network:       3  (ping, resolve_host, scan_ports)
  package:       5  (search, list, install, remove, launch)
  process:       4  (list, run_command, system_info, kill)

Tests passing: 611

Faculty modules: all import cleanly
  DesktopFaculty, EmailWorkflows, DocumentWorkflows,
  BrowserWorkflows, CalendarWorkflows, CommunicationWorkflows,
  extract_intent, SoftwareRegistry

NixOS files: client.nix, server.nix, configuration.nix present

Server starts in ~4.7s. Both ports :8080, :8081 confirmed.

---

## What You Are Building

### Task 1 — inanna/verify_cycle8.py

Create: inanna/verify_cycle8.py

This is the comprehensive capability proof for Cycle 8.
It runs end-to-end tests against real systems on this machine.
No mocking. Real operations. Real results.

The script must:
  - Run with: py -3 verify_cycle8.py
  - Print each check as PASS / FAIL / SKIP with reason
  - Print a final summary: X/Y checks passed
  - Exit code 0 if all pass (or all non-skipped pass)
  - Exit code 1 if any check fails
  - Write results to: docs/implementation/CYCLE8_PROOF.md

Structure:

```python
"""
INANNA NYX — Cycle 8 Capability Proof
verify_cycle8.py

Proves that every faculty built in Cycle 8 works on real hardware.
No mocks. Real operations. Real results.

Run: py -3 verify_cycle8.py
Pass criteria: all non-skipped checks pass
Cycle 8 complete when: this script exits 0

What is proven:
  1.  Tool registry — 41 tools registered, all categories present
  2.  Faculty imports — all 8 faculty modules import cleanly
  3.  Server startup — HTTP :8080 and WebSocket :8081 reachable
  4.  Authentication — login accepted, session token returned
  5.  Email Faculty — ThunderbirdDirectReader reads real MBOX
  6.  Email routing — natural phrases route to correct tools
  7.  Document Faculty — reads .txt file directly
  8.  Document Faculty — reads real PDF or DOCX if present
  9.  Browser Faculty — fetches https://example.com successfully
  10. Browser Faculty — is_safe_url blocks localhost correctly
  11. Calendar Faculty — ThunderbirdCalendarReader finds SQLite DB
  12. Calendar Faculty — zero-events message mentions sync
  13. Desktop Faculty — backend selected correctly for this OS
  14. Desktop Faculty — open_app returns DesktopResult (no crash)
  15. NAMMU routing — email regex routes 'check my email' correctly
  16. NAMMU routing — natural phrase 'anything from X?' routes to email_search
  17. NAMMU routing — 'urgentes?' routes to email_read_inbox
  18. Software Registry — loads without exception
  19. Software Registry — LibreOffice found in registry
  20. NixOS — client.nix exists and contains at-spi2-core
  21. NixOS — server.nix exists and contains inanna-nyx service
  22. NixOS — LinuxAtspiBackend._detect_display_server returns str
  23. NixOS — LINUX_APP_NAME_MAP maps signal to signal-desktop
  24. Test suite — full test suite passes (py -m unittest discover)
  25. Phase identity — CURRENT_PHASE == Cycle 8 - Phase 8.8

Checks are grouped:
  GROUP A — Foundation    (tools, imports, server)
  GROUP B — Faculties     (email, document, browser, calendar, desktop)
  GROUP C — Intelligence  (NAMMU routing)
  GROUP D — Platform      (software registry, NixOS)
  GROUP E — Proof         (test suite, identity)
"""
```

The script uses this pattern for each check:

```python
def check(name: str, fn, group: str = "") -> bool:
    """Run a single check and print result."""
    try:
        result = fn()
        if result is True or result == "pass":
            print(f"  PASS  {name}")
            return True
        elif result == "skip":
            print(f"  SKIP  {name}")
            return True   # skipped counts as not-failed
        else:
            # fn returned a falsy value or error string
            reason = result if isinstance(result, str) else "returned False"
            print(f"  FAIL  {name}  ({reason})")
            return False
    except Exception as e:
        print(f"  FAIL  {name}  (exception: {e})")
        return False
```

### Specific check implementations:

**Check 1 — Tool registry count:**
```python
import json
tools = json.loads(Path('config/tools.json').read_text())['tools']
assert len(tools) == 41, f"expected 41 tools, got {len(tools)}"
cats = {t.get('category') for t in tools.values()}
required = {'browser','calendar','communication','desktop','document',
            'email','filesystem','information','network','package','process'}
missing = required - cats
assert not missing, f"missing categories: {missing}"
return True
```

**Check 3 — Server reachable:**
```python
import urllib.request, json
r = urllib.request.urlopen('http://localhost:8080/', timeout=3)
assert r.status == 200
return True
```

**Check 4 — Authentication:**
```python
import urllib.request, json, urllib.parse
data = json.dumps({"username":"ZAERA","password":"ETERNALOVE"}).encode()
req = urllib.request.Request(
    'http://localhost:8080/login',
    data=data, headers={'Content-Type':'application/json'}, method='POST'
)
resp = urllib.request.urlopen(req, timeout=5)
body = json.loads(resp.read())
assert body.get('token') or body.get('success'), f"login failed: {body}"
return True
```

**Check 5 — Email MBOX:**
```python
from core.email_workflows import ThunderbirdDirectReader
r = ThunderbirdDirectReader()
assert r.is_available(), "INBOX not found"
emails = r.read_inbox(max_emails=3)
# Even if 0 emails, the method ran without error
return True
```

**Check 9 — Browser fetch:**
```python
from core.browser_workflows import BrowserDirectFetcher
f = BrowserDirectFetcher()
page = f.fetch('https://example.com')
assert page.success, f"fetch failed: {page.error}"
assert 'Example Domain' in page.title, f"unexpected title: {page.title}"
return True
```

**Check 24 — Full test suite:**
```python
import subprocess, sys
r = subprocess.run(
    [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
    capture_output=True, text=True,
    cwd=str(Path(__file__).parent)
)
# Find "Ran N tests" and "OK"
output = r.stdout + r.stderr
ran_line = next((l for l in output.splitlines() if 'Ran ' in l), '')
ok = r.returncode == 0
if not ok:
    failures = [l for l in output.splitlines() if 'FAIL' in l or 'ERROR' in l]
    return f"test suite failed: {failures[:3]}"
count = int(ran_line.split()[1]) if ran_line else 0
assert count >= 600, f"expected >=600 tests, got {count}"
return True
```

### Final summary and report:

```python
# Print summary
passed = sum(1 for r in results if r)
total  = len(results)
skipped = sum(1 for r in results if r == 'skip')
failed = total - passed

print()
print("=" * 50)
print(f"CYCLE 8 CAPABILITY PROOF")
print(f"  Passed:  {passed}/{total}")
print(f"  Failed:  {failed}")
print(f"  Skipped: {skipped}")
if failed == 0:
    print("  STATUS:  CYCLE 8 COMPLETE ✓")
else:
    print("  STATUS:  CYCLE 8 INCOMPLETE — fix failures above")
print("=" * 50)

# Write proof document
write_proof_document(results, check_names)

sys.exit(0 if failed == 0 else 1)
```

### Task 2 — docs/cycle8_complete.md (written by verify_cycle8.py)

verify_cycle8.py writes this file on successful completion:

```markdown
# Cycle 8 — The Desktop Bridge — COMPLETE
**Date completed: {date}**
**Machine: {hostname}**
**Tests passing: {count}**
**Tools registered: 41**

## What Was Built

Cycle 8 gave INANNA NYX hands that reach every
application on the operator's machine.

...
```

Full content defined in the script.

### Task 3 — Update identity.py

CURRENT_PHASE = "Cycle 8 - Phase 8.8 - The Capability Proof"

### Task 4 — Tests (offline only)

Create inanna/tests/test_verify_cycle8.py (10 tests):

  - verify_cycle8.py is importable (no syntax errors)
  - check() function returns True on lambda: True
  - check() function returns True on lambda: "pass"
  - check() function returns True on lambda: "skip"
  - check() function returns False on lambda: False
  - check() function returns False on lambda: "error reason"
  - check() function returns False on exception-raising lambda
  - All 25 check names are defined (check that the
    checks list has exactly 25 entries)
  - CYCLE8_CHECKS list has correct groups A-E
  - write_proof_document is callable

Update test_identity.py: CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/verify_cycle8.py                <- NEW (the proof)
inanna/identity.py                     <- MODIFY: CURRENT_PHASE
inanna/tests/test_verify_cycle8.py     <- NEW
inanna/tests/test_identity.py          <- MODIFY
docs/implementation/CURRENT_PHASE.md  <- (already updated via GitHub API)

NOTE: docs/cycle8_complete.md is written BY verify_cycle8.py
when it runs successfully. Do NOT create it manually.

---

## What You Are NOT Building

- No new tools
- No new faculty modules
- No changes to server.py, main.py, or tools.json
- No changes to NixOS configs (those are done)
- No changes to any workflow files

---

## How to Run the Proof

```
cd C:\Users\Zohar\Dropbox\Windows11\REPOS\ABZU\INANNA\inanna
py -3 verify_cycle8.py
```

The server must be running before executing verify_cycle8.py.
Start it with: py -3 ui_main.py (in a separate terminal)

Checks that require the server (3, 4) will SKIP automatically
if the server is not reachable, rather than FAIL.

---

## Definition of Done

- [ ] verify_cycle8.py created with all 25 checks in 5 groups
- [ ] verify_cycle8.py runs and all non-skipped checks PASS
- [ ] docs/implementation/CYCLE8_PROOF.md written by the script
- [ ] CURRENT_PHASE = "Cycle 8 - Phase 8.8 - The Capability Proof"
- [ ] All offline tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle8-phase8-complete
- [ ] Run verify_cycle8.py one final time and confirm exit 0
- [ ] If exit 0: push as cycle8-complete with docs/cycle8_complete.md

---

## Handoff

STEP 1: Commit as cycle8-phase8-complete
STEP 2: Run verify_cycle8.py (server must be running)
STEP 3: If all checks pass → push as cycle8-complete
         docs/cycle8_complete.md must be included in that commit
STEP 4: If any checks fail → fix the failing component,
         re-run, then push as cycle8-complete

The cycle8-complete commit is the milestone.
It marks the end of Cycle 8 and the readiness for Cycle 9.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-22*
*This is the proof.*
*Not of code — of capacity.*
*Every check is a capability confirmed.*
*Every PASS is a promise kept.*
*When the script exits 0,*
*INANNA NYX has hands.*
*Cycle 8 is complete.*
*The bridge is built.*
*Cycle 9 begins.*

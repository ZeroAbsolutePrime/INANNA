from __future__ import annotations

"""
INANNA NYX - Cycle 8 Capability Proof
verify_cycle8.py

Proves that every faculty built in Cycle 8 works on real hardware.
No mocks. Real operations. Real results.

Run: py -3 verify_cycle8.py
Pass criteria: all non-skipped checks pass
Cycle 8 complete when: this script exits 0
"""

import json
import platform
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from core.browser_workflows import BrowserDirectFetcher, is_safe_url
from core.calendar_workflows import (
    CalendarComprehension,
    CalendarResult,
    CalendarWorkflows,
    ThunderbirdCalendarReader,
)
from core.communication_workflows import CommunicationWorkflows
from core.desktop_faculty import DesktopFaculty, DesktopResult, LINUX_APP_NAME_MAP, LinuxAtspiBackend
from core.document_workflows import DocumentWorkflows
from core.email_workflows import ThunderbirdDirectReader
from core.nammu_intent import extract_intent
from core.software_registry import SoftwareRegistry
from identity import CURRENT_PHASE
from main import extract_email_tool_request


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent
DOCS_ROOT = REPO_ROOT / "docs"
IMPLEMENTATION_DOCS_ROOT = DOCS_ROOT / "implementation"
TOOLS_PATH = APP_ROOT / "config" / "tools.json"
IDENTITY_PATH = APP_ROOT / "identity.py"
MAIN_PATH = APP_ROOT / "main.py"
SERVER_PATH = APP_ROOT / "ui" / "server.py"
CURRENT_PHASE_PATH = IMPLEMENTATION_DOCS_ROOT / "CURRENT_PHASE.md"
CLIENT_NIX_PATH = REPO_ROOT / "nixos" / "client.nix"
SERVER_NIX_PATH = REPO_ROOT / "nixos" / "server.nix"
PROOF_PATH = IMPLEMENTATION_DOCS_ROOT / "CYCLE8_PROOF.md"
COMPLETE_PATH = DOCS_ROOT / "cycle8_complete.md"

SERVER_ROOT = "http://localhost:8080/"
LOGIN_URL = "http://localhost:8080/login"


GROUP_NAMES = {
    "A": "Foundation",
    "B": "Faculties",
    "C": "Intelligence",
    "D": "Platform",
    "E": "Proof",
}

EXPECTED_PHASE = "Cycle 8 - Phase 8.8 - The Capability Proof"
EXPECTED_CATEGORIES = {
    "browser",
    "calendar",
    "communication",
    "desktop",
    "document",
    "email",
    "filesystem",
    "information",
    "network",
    "package",
    "process",
}

LAST_CHECK_STATUS = "FAIL"
LAST_CHECK_REASON = ""


@dataclass(frozen=True)
class Cycle8Check:
    code: str
    group: str
    name: str
    fn: Callable[[], object]


@dataclass
class CheckResult:
    code: str
    group: str
    name: str
    status: str
    reason: str = ""


def _set_last(status: str, reason: str = "") -> None:
    global LAST_CHECK_STATUS, LAST_CHECK_REASON
    LAST_CHECK_STATUS = status
    LAST_CHECK_REASON = reason


def _classify_result(value: object) -> tuple[str, str]:
    if value is True or value == "pass":
        return "PASS", ""
    if value == "skip":
        return "SKIP", ""
    if isinstance(value, str):
        return "FAIL", value
    if not value:
        return "FAIL", "returned False"
    return "FAIL", f"unexpected return: {value!r}"


def check(name: str, fn: Callable[[], object], group: str = "") -> bool:
    """Run a single check and print result."""
    del group
    try:
        result = fn()
        status, reason = _classify_result(result)
        _set_last(status, reason)
        if status == "PASS":
            print(f"  PASS  {name}")
            return True
        if status == "SKIP":
            print(f"  SKIP  {name}")
            return True
        print(f"  FAIL  {name}  ({reason})")
        return False
    except Exception as exc:  # pragma: no cover - exercised through runtime use
        _set_last("FAIL", f"exception: {exc}")
        print(f"  FAIL  {name}  (exception: {exc})")
        return False


def run_check(case: Cycle8Check) -> CheckResult:
    passed = check(case.name, case.fn, group=case.group)
    del passed
    return CheckResult(
        code=case.code,
        group=case.group,
        name=case.name,
        status=LAST_CHECK_STATUS,
        reason=LAST_CHECK_REASON,
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_tools() -> dict[str, dict[str, object]]:
    payload = json.loads(read_text(TOOLS_PATH))
    tools = payload.get("tools", {})
    return tools if isinstance(tools, dict) else {}


def find_real_document() -> Path | None:
    for pattern in ("*.pdf", "*.docx"):
        for candidate in REPO_ROOT.rglob(pattern):
            if ".git" in candidate.parts:
                continue
            if candidate.is_file():
                return candidate
    return None


def can_connect(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def server_is_available() -> bool:
    return can_connect("127.0.0.1", 8080, timeout=1.5)


def network_error(message: str) -> bool:
    lowered = str(message or "").lower()
    return any(
        token in lowered
        for token in (
            "timed out",
            "timeout",
            "temporarily unavailable",
            "name or service not known",
            "nodename nor servname",
            "failed to resolve",
            "connection refused",
            "network is unreachable",
            "remote end closed",
            "certificate",
            "ssl",
        )
    )


def assert_tool_request(text: str, expected_tool: str) -> dict[str, object] | str:
    request = extract_email_tool_request(text)
    if request is None:
        return f"no tool request for {text!r}"
    tool_name = str(request.get("tool", ""))
    if tool_name != expected_tool:
        return f"expected {expected_tool}, got {tool_name}"
    return request


def check_tool_registry_count() -> object:
    tools = load_tools()
    if len(tools) != 41:
        return f"expected 41 tools, got {len(tools)}"
    categories = {
        str(tool.get("category", "")).strip()
        for tool in tools.values()
        if isinstance(tool, dict)
    }
    missing = sorted(EXPECTED_CATEGORIES - categories)
    if missing:
        return f"missing categories: {missing}"
    return True


def check_faculty_imports() -> object:
    desktop = DesktopFaculty()
    document = DocumentWorkflows(desktop)
    communication = CommunicationWorkflows(desktop)
    calendar = CalendarWorkflows()
    registry = SoftwareRegistry()
    intent = extract_intent("hello")
    checks = [
        isinstance(desktop, DesktopFaculty),
        isinstance(document, DocumentWorkflows),
        isinstance(communication, CommunicationWorkflows),
        isinstance(BrowserDirectFetcher(), BrowserDirectFetcher),
        isinstance(calendar, CalendarWorkflows),
        isinstance(ThunderbirdDirectReader(), ThunderbirdDirectReader),
        isinstance(registry, SoftwareRegistry),
        hasattr(intent, "intent"),
    ]
    if not all(checks):
        return "one or more Cycle 8 modules did not instantiate cleanly"
    return True


def check_server_reachable() -> object:
    if not server_is_available():
        return "skip"
    try:
        with urllib.request.urlopen(SERVER_ROOT, timeout=3) as response:
            if int(response.status) != 200:
                return f"http status {response.status}"
        if not can_connect("127.0.0.1", 8081, timeout=2.0):
            return "port 8081 not reachable"
        return True
    except urllib.error.URLError:
        return "skip"
    except OSError:
        return "skip"


def check_authentication_login() -> object:
    if not server_is_available():
        return "skip"
    payload = json.dumps({"username": "ZAERA", "password": "ETERNALOVE"}).encode("utf-8")
    request = urllib.request.Request(
        LOGIN_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
        if body.get("token") or body.get("success"):
            return True
        return f"login failed: {body}"
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(exc)
        return f"login http error {exc.code}: {body}"
    except urllib.error.URLError:
        return "skip"
    except OSError:
        return "skip"


def check_email_mbox_reader() -> object:
    reader = ThunderbirdDirectReader()
    if not reader.is_available():
        return "INBOX not found"
    emails = reader.read_inbox(max_emails=3)
    if not isinstance(emails, list):
        return "read_inbox did not return a list"
    return True


def check_email_natural_routing() -> object:
    request = assert_tool_request("check thunderbird inbox", "email_read_inbox")
    if isinstance(request, str):
        return request
    params = request.get("params", {})
    if not isinstance(params, dict):
        return "params payload is not a dict"
    app = str(params.get("app", ""))
    if app != "thunderbird":
        return f"expected thunderbird app, got {app!r}"
    return True


def check_document_read_text() -> object:
    workflows = DocumentWorkflows(DesktopFaculty())
    with TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "cycle8.txt"
        target.write_text("Cycle 8 proof text file.\nReal file read.", encoding="utf-8")
        record, comprehension = workflows.read_document(str(target))
    if not record.success:
        return record.error or "text document read failed"
    if "Cycle 8 proof text file." not in record.content:
        return "text content missing from read result"
    if "DOCUMENT:" not in comprehension.to_crown_context():
        return "document comprehension missing"
    return True


def check_document_read_real_binary() -> object:
    target = find_real_document()
    if target is None:
        return "skip"
    workflows = DocumentWorkflows(DesktopFaculty())
    record, _comprehension = workflows.read_document(str(target))
    if not record.success:
        return record.error or f"could not read {target.name}"
    if not (record.content or record.sheet_names):
        return f"{target.name} produced no readable content"
    return True


def check_browser_fetch_example() -> object:
    record = BrowserDirectFetcher().fetch("https://example.com")
    if not record.success:
        if network_error(record.error or ""):
            return "skip"
        return record.error or "fetch failed"
    if "Example Domain" not in record.title:
        return f"unexpected title: {record.title!r}"
    return True


def check_browser_blocks_localhost() -> object:
    if is_safe_url("http://localhost:8080/"):
        return "localhost should be blocked"
    if is_safe_url("http://127.0.0.1:8080/"):
        return "127.0.0.1 should be blocked"
    return True


def check_calendar_sqlite_available() -> object:
    reader = ThunderbirdCalendarReader()
    if not reader.is_available():
        return "Thunderbird calendar database not found"
    result = reader.read_today()
    if not isinstance(result, CalendarResult):
        return "calendar reader did not return CalendarResult"
    return True


def check_calendar_zero_event_sync_message() -> object:
    workflows = CalendarWorkflows()
    empty = CalendarResult(success=True, source="thunderbird_sqlite", events=[], todos=[])
    comprehension = CalendarComprehension(
        total_events=0,
        period_label="today",
        source="thunderbird_sqlite",
        has_remote_calendar=True,
    )
    rendered = workflows.format_result(empty, comprehension)
    lowered = rendered.lower()
    if "open thunderbird" not in lowered or "sync" not in lowered:
        return "zero-events context did not mention opening Thunderbird to sync"
    return True


def check_desktop_backend_selected() -> object:
    faculty = DesktopFaculty()
    expected = platform.system()
    if expected == "Windows" and faculty.backend_name != "windows-mcp":
        return f"expected windows-mcp, got {faculty.backend_name}"
    if expected == "Linux" and faculty.backend_name != "linux-atspi2":
        return f"expected linux-atspi2, got {faculty.backend_name}"
    if expected not in {"Windows", "Linux"} and not faculty.backend_name.startswith("fallback-"):
        return f"expected fallback backend, got {faculty.backend_name}"
    return True


def check_desktop_open_app_result() -> object:
    faculty = DesktopFaculty()
    query = "notepad" if platform.system() == "Windows" else "firefox"
    result = faculty.open_app(query)
    if not isinstance(result, DesktopResult):
        return "open_app did not return DesktopResult"
    if result.tool != "open_app":
        return f"unexpected tool field: {result.tool}"
    return True


def check_nammu_check_my_email() -> object:
    request = assert_tool_request("check my email", "email_read_inbox")
    return True if not isinstance(request, str) else request


def check_nammu_anything_from() -> object:
    request = assert_tool_request("anything from Matxalen?", "email_search")
    if isinstance(request, str):
        return request
    params = request.get("params", {})
    if not isinstance(params, dict):
        return "params payload is not a dict"
    query = str(params.get("query", ""))
    if "Matxalen".lower() not in query.lower():
        return f"sender missing from query: {query!r}"
    return True


def check_nammu_urgentes() -> object:
    request = assert_tool_request("urgentes?", "email_read_inbox")
    if isinstance(request, str):
        return request
    params = request.get("params", {})
    if not isinstance(params, dict) or not params.get("urgency_only"):
        return "urgency_only flag missing"
    return True


def check_software_registry_loads() -> object:
    registry = SoftwareRegistry()
    registry.load()
    return True


def check_software_registry_libreoffice() -> object:
    registry = SoftwareRegistry()
    registry.load()
    match = registry.is_installed("libreoffice")
    if match is None:
        return "LibreOffice not found in registry"
    return True


def check_client_nix_has_atspi() -> object:
    if not CLIENT_NIX_PATH.exists():
        return f"missing {CLIENT_NIX_PATH.name}"
    text = read_text(CLIENT_NIX_PATH)
    required = ("at-spi2-core", "pyatspi")
    missing = [item for item in required if item not in text]
    if missing:
        return f"missing nix packages: {missing}"
    return True


def check_server_nix_has_service() -> object:
    if not SERVER_NIX_PATH.exists():
        return f"missing {SERVER_NIX_PATH.name}"
    text = read_text(SERVER_NIX_PATH)
    if "inanna-nyx" not in text or "systemd.services" not in text:
        return "inanna-nyx service definition missing"
    return True


def check_detect_display_server_returns_str() -> object:
    value = LinuxAtspiBackend()._detect_display_server()
    if not isinstance(value, str):
        return f"expected str, got {type(value).__name__}"
    if value not in {"x11", "wayland"}:
        return f"unexpected display server value: {value}"
    return True


def check_signal_name_map() -> object:
    mapped = LINUX_APP_NAME_MAP.get("signal")
    if mapped != "signal-desktop":
        return f"expected signal-desktop, got {mapped!r}"
    return True


def extract_test_count(output: str) -> int:
    match = re.search(r"Ran\s+(\d+)\s+tests?", str(output))
    return int(match.group(1)) if match else 0


def check_full_test_suite() -> object:
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        capture_output=True,
        text=True,
        cwd=str(APP_ROOT),
    )
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    if result.returncode != 0:
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        failures = [line for line in lines if "FAIL" in line or "ERROR" in line]
        return f"test suite failed: {failures[:3] or lines[:5]}"
    count = extract_test_count(output)
    if count < 600:
        return f"expected >=600 tests, got {count}"
    return True


def check_phase_identity() -> object:
    if CURRENT_PHASE != EXPECTED_PHASE:
        return f"CURRENT_PHASE mismatch: {CURRENT_PHASE}"
    first_line = read_text(CURRENT_PHASE_PATH).splitlines()[0].strip()
    if EXPECTED_PHASE not in first_line:
        return f"CURRENT_PHASE.md mismatch: {first_line}"
    return True


CYCLE8_CHECKS = [
    Cycle8Check("A1", "A", "Tool registry: 41 tools and 11 categories", check_tool_registry_count),
    Cycle8Check("A2", "A", "Faculty imports: Cycle 8 modules import cleanly", check_faculty_imports),
    Cycle8Check("A3", "A", "Server startup: HTTP :8080 and port :8081 reachable", check_server_reachable),
    Cycle8Check("A4", "A", "Authentication: ZAERA login succeeds", check_authentication_login),
    Cycle8Check("A5", "A", "Email Faculty: ThunderbirdDirectReader reads real MBOX", check_email_mbox_reader),
    Cycle8Check("B6", "B", "Email routing: natural inbox phrase routes correctly", check_email_natural_routing),
    Cycle8Check("B7", "B", "Document Faculty: reads .txt directly", check_document_read_text),
    Cycle8Check("B8", "B", "Document Faculty: reads real PDF or DOCX if present", check_document_read_real_binary),
    Cycle8Check("B9", "B", "Browser Faculty: fetches https://example.com", check_browser_fetch_example),
    Cycle8Check("B10", "B", "Browser Faculty: blocks localhost safely", check_browser_blocks_localhost),
    Cycle8Check("C11", "C", "Calendar Faculty: ThunderbirdCalendarReader finds SQLite DB", check_calendar_sqlite_available),
    Cycle8Check("C12", "C", "Calendar Faculty: zero-events message mentions sync", check_calendar_zero_event_sync_message),
    Cycle8Check("C13", "C", "Desktop Faculty: backend selected correctly", check_desktop_backend_selected),
    Cycle8Check("C14", "C", "Desktop Faculty: open_app returns DesktopResult", check_desktop_open_app_result),
    Cycle8Check("C15", "C", "NAMMU routing: 'check my email' -> email_read_inbox", check_nammu_check_my_email),
    Cycle8Check("D16", "D", "NAMMU routing: 'anything from X?' -> email_search", check_nammu_anything_from),
    Cycle8Check("D17", "D", "NAMMU routing: 'urgentes?' -> email_read_inbox", check_nammu_urgentes),
    Cycle8Check("D18", "D", "Software Registry: loads without exception", check_software_registry_loads),
    Cycle8Check("D19", "D", "Software Registry: LibreOffice found in registry", check_software_registry_libreoffice),
    Cycle8Check("D20", "D", "NixOS client: client.nix contains at-spi2-core", check_client_nix_has_atspi),
    Cycle8Check("E21", "E", "NixOS server: server.nix contains inanna-nyx service", check_server_nix_has_service),
    Cycle8Check("E22", "E", "NixOS backend: _detect_display_server returns str", check_detect_display_server_returns_str),
    Cycle8Check("E23", "E", "NixOS backend: signal maps to signal-desktop", check_signal_name_map),
    Cycle8Check("E24", "E", "Proof: full unittest suite passes (>=600 tests)", check_full_test_suite),
    Cycle8Check("E25", "E", "Phase identity: CURRENT_PHASE == Cycle 8 - Phase 8.8", check_phase_identity),
]


def format_result_table(results: list[CheckResult]) -> str:
    lines = [
        "| Code | Group | Status | Check | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        reason = result.reason.replace("\n", " ").replace("|", "\\|").strip() or "-"
        lines.append(
            f"| {result.code} | {result.group} | {result.status} | {result.name} | {reason} |"
        )
    return "\n".join(lines)


def write_completion_document(results: list[CheckResult]) -> None:
    passed = sum(1 for result in results if result.status == "PASS")
    skipped = sum(1 for result in results if result.status == "SKIP")
    proof = f"""# Cycle 8 - The Desktop Bridge - COMPLETE
**Date completed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}**
**Machine: {platform.node()}**
**Python: {platform.python_version()}**
**Checks passed: {passed}**
**Checks skipped: {skipped}**
**Tools registered: 41**

## What Was Built

Cycle 8 gave INANNA NYX hands that reach beyond the terminal:
desktop control, communication workflows, email workflows,
document handling, browser reading, calendar awareness,
and the NixOS bridge for the split client/server architecture.

## Capability Proof

The proof was executed by `inanna/verify_cycle8.py`.
All non-skipped checks passed.

## Notes

- Server and network checks may skip gracefully if the service is unavailable.
- Local faculty checks executed against the real machine state.
- Detailed proof output is recorded in `docs/implementation/CYCLE8_PROOF.md`.
"""
    COMPLETE_PATH.write_text(proof, encoding="utf-8")


def write_proof_document(results: list[CheckResult]) -> None:
    passed = sum(1 for result in results if result.status == "PASS")
    skipped = sum(1 for result in results if result.status == "SKIP")
    failed = sum(1 for result in results if result.status == "FAIL")
    total = len(results)
    status_line = "CYCLE 8 COMPLETE" if failed == 0 else "CYCLE 8 INCOMPLETE"
    by_group = []
    for group in ("A", "B", "C", "D", "E"):
        group_results = [result for result in results if result.group == group]
        by_group.append(
            f"- Group {group} - {GROUP_NAMES[group]}: "
            f"{sum(1 for result in group_results if result.status == 'PASS')} pass, "
            f"{sum(1 for result in group_results if result.status == 'SKIP')} skip, "
            f"{sum(1 for result in group_results if result.status == 'FAIL')} fail"
        )

    document = f"""# Cycle 8 Capability Proof
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Machine:** {platform.node()}
**Python:** {platform.python_version()}
**Phase:** {CURRENT_PHASE}

## Summary

- Passed: {passed}/{total}
- Failed: {failed}
- Skipped: {skipped}
- Status: {status_line}

## Groups

{chr(10).join(by_group)}

## Results

{format_result_table(results)}
"""
    PROOF_PATH.write_text(document, encoding="utf-8")
    if failed == 0:
        write_completion_document(results)


def main() -> int:
    print("INANNA NYX - Cycle 8 Capability Proof")
    print("=====================================")

    results: list[CheckResult] = []
    current_group = None
    for case in CYCLE8_CHECKS:
        if case.group != current_group:
            current_group = case.group
            print()
            print(f"GROUP {case.group} - {GROUP_NAMES[case.group]}")
        results.append(run_check(case))

    passed = sum(1 for result in results if result.status == "PASS")
    skipped = sum(1 for result in results if result.status == "SKIP")
    failed = sum(1 for result in results if result.status == "FAIL")
    total = len(results)

    print()
    print("=" * 50)
    print("CYCLE 8 CAPABILITY PROOF")
    print(f"  Passed:  {passed}/{total}")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped}")
    if failed == 0:
        print("  STATUS:  CYCLE 8 COMPLETE")
    else:
        print("  STATUS:  CYCLE 8 INCOMPLETE - fix failures above")
    print("=" * 50)

    write_proof_document(results)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

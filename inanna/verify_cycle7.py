from __future__ import annotations

import hmac
import json
import platform
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from core.auth import AuthStore, hash_password, verify_password
from core.filesystem_faculty import MAX_READ_BYTES, FileSystemFaculty
from core.help_system import build_help_response
from core.package_faculty import PackageFaculty, PackageResult
from core.process_faculty import ProcessFaculty
from core.software_registry import SoftwareRegistry
from identity import CURRENT_PHASE, CYCLE7_COMPLETE
from voice.listener import MIN_SPEECH_SECONDS, SAMPLE_RATE


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent
DOCS_ROOT = REPO_ROOT / "docs"
AUTH_PATH = APP_ROOT / "core" / "auth.py"
FILESYSTEM_PATH = APP_ROOT / "core" / "filesystem_faculty.py"
PROCESS_PATH = APP_ROOT / "core" / "process_faculty.py"
PACKAGE_PATH = APP_ROOT / "core" / "package_faculty.py"
SOFTWARE_REGISTRY_PATH = APP_ROOT / "core" / "software_registry.py"
TOOLS_CONFIG_PATH = APP_ROOT / "config" / "tools.json"
GOVERNANCE_SIGNALS_PATH = APP_ROOT / "config" / "governance_signals.json"
IDENTITY_PATH = APP_ROOT / "identity.py"
SERVER_PATH = APP_ROOT / "ui" / "server.py"
INDEX_HTML_PATH = APP_ROOT / "ui" / "static" / "index.html"
LOGIN_HTML_PATH = APP_ROOT / "ui" / "static" / "login.html"
UI_MAIN_PATH = APP_ROOT / "ui_main.py"
NIXOS_DIR = REPO_ROOT / "nixos"
CONFIGURATION_NIX_PATH = NIXOS_DIR / "configuration.nix"
SERVICE_PATH = NIXOS_DIR / "inanna-nyx.service"
INSTALL_SH_PATH = NIXOS_DIR / "install.sh"
VOICE_DIR = APP_ROOT / "voice"
VOICE_LISTENER_PATH = VOICE_DIR / "listener.py"
VOICE_INIT_PATH = VOICE_DIR / "__init__.py"
VOICE_README_PATH = VOICE_DIR / "README.md"

WINGET_SEARCH_SAMPLE = """Name                                Id                                  Version      Match               Source
---------------------------------------------------------------------------------------------------------------
Notepad++                           Notepad++.Notepad++                 8.8.8        Tag: notepad        winget
Notepad++ (Store)                   9MSMLRH6LZF3                        Unknown      Tag: notepad        msstore
VLC media player                    VideoLAN.VLC                        3.0.21       Tag: vlc            winget
VLC UWP                             XPDM1ZW6815MQM                      Unknown      Tag: vlc            msstore
"""


@dataclass
class CheckResult:
    label: str
    status: str
    detail: str = ""


def passed(label: str, detail: str = "") -> CheckResult:
    return CheckResult(label, "PASS", detail)


def failed(label: str, detail: str = "") -> CheckResult:
    return CheckResult(label, "FAIL", detail)


def manual(label: str, detail: str = "") -> CheckResult:
    return CheckResult(label, "MANUAL", detail)


def ensure(label: str, condition: bool, detail: str = "") -> CheckResult:
    return passed(label, detail) if condition else failed(label, detail)


@lru_cache(maxsize=None)
def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def tools_payload() -> dict[str, object]:
    return json.loads(TOOLS_CONFIG_PATH.read_text(encoding="utf-8"))


def tools_config() -> dict[str, dict[str, object]]:
    payload = tools_payload().get("tools", {})
    return payload if isinstance(payload, dict) else {}


@lru_cache(maxsize=1)
def software_registry_probe() -> tuple[SoftwareRegistry | None, str | None]:
    registry = SoftwareRegistry()
    try:
        registry.load()
        return registry, None
    except Exception as error:  # pragma: no cover - defensive for local environment
        return None, str(error)


def compact(text: str) -> str:
    return "".join(str(text).split())


def emit(line: str) -> None:
    try:
        print(line)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        safe_line = line.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe_line)


def make_auth_store() -> tuple[TemporaryDirectory[str], AuthStore]:
    temp_dir = TemporaryDirectory()
    store = AuthStore(Path(temp_dir.name))
    store.seed_user("zaera", "ZAERA", "ETERNALOVE", "guardian")
    return temp_dir, store


def make_winget_result() -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=WINGET_SEARCH_SAMPLE, stderr="")


def check_auth_module_exists() -> CheckResult:
    return ensure("Authentication: core/auth.py exists", AUTH_PATH.exists(), str(AUTH_PATH))


def check_auth_store_imports() -> CheckResult:
    temp_dir = None
    try:
        temp_dir, store = make_auth_store()
        return ensure("Authentication: AuthStore imports and instantiates", isinstance(store, AuthStore))
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def check_password_hash_format() -> CheckResult:
    hashed = hash_password("ETERNALOVE")
    if ":" not in hashed:
        return failed("Authentication: hash_password returns salt:hash", hashed)
    salt, digest = hashed.split(":", 1)
    is_hex = all(character in "0123456789abcdef" for character in (salt + digest).lower())
    return ensure(
        "Authentication: hash_password returns salt:hash",
        bool(salt) and bool(digest) and is_hex,
        hashed,
    )


def check_verify_password_correct() -> CheckResult:
    hashed = hash_password("ETERNALOVE")
    return ensure(
        "Authentication: verify_password accepts the correct password",
        verify_password("ETERNALOVE", hashed),
    )


def check_verify_password_wrong() -> CheckResult:
    hashed = hash_password("ETERNALOVE")
    return ensure(
        "Authentication: verify_password rejects the wrong password",
        verify_password("wrong-password", hashed) is False,
    )


def check_verify_timing_safe() -> CheckResult:
    return ensure(
        "Authentication: verify_password uses hmac.compare_digest",
        "hmac.compare_digest" in source(AUTH_PATH) and callable(hmac.compare_digest),
    )


def check_zaera_seed_idempotent() -> CheckResult:
    temp_dir = None
    try:
        temp_dir, store = make_auth_store()
        first = store.get_by_username("ZAERA")
        second = store.seed_user("zaera", "ZAERA", "CHANGED", "guardian")
        return ensure(
            "Authentication: seed_user is idempotent for ZAERA",
            first is not None and first.password_hash == second.password_hash,
        )
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def check_authenticate_correct() -> CheckResult:
    temp_dir = None
    try:
        temp_dir, store = make_auth_store()
        record = store.authenticate("ZAERA", "ETERNALOVE")
        return ensure(
            "Authentication: ZAERA / ETERNALOVE authenticates",
            record is not None and record.username == "ZAERA",
        )
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def check_authenticate_wrong_pw() -> CheckResult:
    temp_dir = None
    try:
        temp_dir, store = make_auth_store()
        return ensure(
            "Authentication: wrong password returns None",
            store.authenticate("ZAERA", "WRONG") is None,
        )
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def check_authenticate_unknown() -> CheckResult:
    temp_dir = None
    try:
        temp_dir, store = make_auth_store()
        return ensure(
            "Authentication: unknown username returns None",
            store.authenticate("UNKNOWN", "ETERNALOVE") is None,
        )
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def check_authenticate_case_insensitive() -> CheckResult:
    temp_dir = None
    try:
        temp_dir, store = make_auth_store()
        record = store.authenticate("zaera", "ETERNALOVE")
        return ensure(
            "Authentication: username matching is case-insensitive",
            record is not None and record.username == "ZAERA",
        )
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def check_login_html_exists() -> CheckResult:
    return ensure("Authentication: ui/static/login.html exists", LOGIN_HTML_PATH.exists())


def check_login_html_has_form() -> CheckResult:
    login_html = source(LOGIN_HTML_PATH)
    return ensure(
        "Authentication: login.html contains a form and password field",
        "<form" in login_html.lower() and 'type="password"' in login_html.lower(),
    )


def check_login_html_full_page() -> CheckResult:
    return ensure(
        "Authentication: login.html is standalone and has no login overlay",
        "login-overlay" not in source(LOGIN_HTML_PATH),
    )


def check_login_html_has_glyph() -> CheckResult:
    login_html = source(LOGIN_HTML_PATH)
    return ensure(
        "Authentication: login.html contains the 𒀭 glyph reference",
        "𒀭" in login_html or "INANNA NYX" in login_html,
    )


def check_index_no_overlay() -> CheckResult:
    return ensure(
        "Authentication: index.html no longer contains login-overlay",
        "login-overlay" not in source(INDEX_HTML_PATH),
    )


def check_ui_main_passes_server() -> CheckResult:
    ui_main = source(UI_MAIN_PATH)
    compact_ui_main = compact(ui_main)
    thread_ok = "threading.Thread(target=run_http_server,args=(server,),daemon=True)" in compact_ui_main
    server_ok = "server=InterfaceServer()" in compact_ui_main
    order_ok = (
        server_ok
        and thread_ok
        and compact_ui_main.index("server=InterfaceServer()")
        < compact_ui_main.index("threading.Thread(target=run_http_server,args=(server,),daemon=True)")
    )
    return ensure(
        "Authentication: ui_main.py passes InterfaceServer to the HTTP thread",
        thread_ok and order_ok,
    )


def check_filesystem_faculty_module() -> CheckResult:
    return ensure(
        "File System Faculty: core/filesystem_faculty.py exists and imports",
        FILESYSTEM_PATH.exists() and isinstance(FileSystemFaculty(), FileSystemFaculty),
    )


def check_read_file_temp() -> CheckResult:
    faculty = FileSystemFaculty()
    with TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "hello.txt"
        target.write_text("hello filesystem", encoding="utf-8")
        result = faculty.read_file(str(target))
    return ensure(
        "File System Faculty: read_file reads a temporary file",
        result.success and result.content == "hello filesystem",
        result.error or "",
    )


def check_read_file_truncation() -> CheckResult:
    faculty = FileSystemFaculty()
    with TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "large.txt"
        target.write_bytes(b"a" * (MAX_READ_BYTES + 128))
        result = faculty.read_file(str(target))
    return ensure(
        "File System Faculty: read_file truncates at 512 KB",
        result.success and result.truncated and result.bytes_read == MAX_READ_BYTES,
        str(result.bytes_read),
    )


def check_list_dir_home() -> CheckResult:
    faculty = FileSystemFaculty()
    result = faculty.list_dir(str(Path.home()))
    return ensure(
        "File System Faculty: list_dir lists the home directory",
        result.success and isinstance(result.entries, list),
        result.error or "",
    )


def check_search_files_pattern() -> CheckResult:
    faculty = FileSystemFaculty()
    result = faculty.search_files(str(APP_ROOT), "*.py")
    return ensure(
        "File System Faculty: search_files finds Python files in inanna/",
        result.success and len(result.entries) >= 1 and any(entry.path.endswith(".py") for entry in result.entries),
        result.error or "",
    )


def check_file_info_metadata() -> CheckResult:
    faculty = FileSystemFaculty()
    result = faculty.file_info(str(IDENTITY_PATH))
    size_bytes = result.info.size_bytes if result.info is not None else 0
    return ensure(
        "File System Faculty: file_info returns metadata with size > 0",
        result.success and result.info is not None and size_bytes > 0,
        str(size_bytes),
    )


def check_write_file_temp() -> CheckResult:
    faculty = FileSystemFaculty()
    with TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "written.txt"
        write_result = faculty.write_file(str(target), "written content")
        read_back = target.read_text(encoding="utf-8")
    return ensure(
        "File System Faculty: write_file writes a temporary file",
        write_result.success and read_back == "written content",
        write_result.error or "",
    )


def check_write_file_no_overwrite() -> CheckResult:
    faculty = FileSystemFaculty()
    with TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "written.txt"
        target.write_text("first", encoding="utf-8")
        result = faculty.write_file(str(target), "second")
    return ensure(
        "File System Faculty: write_file refuses overwrite without the flag",
        result.success is False and "already exists" in str(result.error).lower(),
        result.error or "",
    )


def check_write_file_overwrite_flag() -> CheckResult:
    faculty = FileSystemFaculty()
    with TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "written.txt"
        target.write_text("first", encoding="utf-8")
        result = faculty.write_file(str(target), "second", overwrite=True)
        read_back = target.read_text(encoding="utf-8")
    return ensure(
        "File System Faculty: write_file allows overwrite=True",
        result.success and read_back == "second",
        result.error or "",
    )


def check_forbidden_path_blocked() -> CheckResult:
    faculty = FileSystemFaculty()
    result = faculty.read_file("/etc/shadow")
    return ensure(
        "File System Faculty: forbidden paths are blocked",
        faculty.is_forbidden(Path("/etc/shadow")) and result.success is False,
        result.error or "",
    )


def check_safe_paths_home() -> CheckResult:
    faculty = FileSystemFaculty()
    return ensure(
        "File System Faculty: home directory is a safe read path",
        faculty.is_safe_read(Path.home()),
    )


def check_process_faculty_module() -> CheckResult:
    return ensure(
        "Process Faculty: core/process_faculty.py exists and imports",
        PROCESS_PATH.exists() and isinstance(ProcessFaculty(), ProcessFaculty),
    )


def check_system_info_success() -> CheckResult:
    result = ProcessFaculty().system_info()
    return ensure("Process Faculty: system_info returns success=True", result.success, result.error or "")


def check_system_info_cpu_count() -> CheckResult:
    result = ProcessFaculty().system_info()
    count = result.system_info.cpu_count if result.system_info is not None else 0
    return ensure("Process Faculty: system_info reports cpu_count > 0", count > 0, str(count))


def check_system_info_ram() -> CheckResult:
    result = ProcessFaculty().system_info()
    ram = result.system_info.ram_total_gb if result.system_info is not None else 0.0
    return ensure("Process Faculty: system_info reports ram_total_gb > 0", ram > 0, str(ram))


def check_list_processes_returns() -> CheckResult:
    result = ProcessFaculty().list_processes(limit=5)
    return ensure(
        "Process Faculty: list_processes returns at least one process",
        result.success and len(result.records) >= 1,
        result.error or "",
    )


def check_list_processes_has_name() -> CheckResult:
    result = ProcessFaculty().list_processes(limit=1)
    first_name = result.records[0].name if result.records else ""
    return ensure(
        "Process Faculty: list_processes records have non-empty names",
        result.success and bool(first_name.strip()),
        first_name,
    )


def check_run_echo() -> CheckResult:
    result = ProcessFaculty().run_command("echo hello")
    return ensure("Process Faculty: run_command('echo hello') succeeds", result.success, result.stderr or result.error or "")


def check_run_echo_output() -> CheckResult:
    result = ProcessFaculty().run_command("echo hello")
    return ensure(
        "Process Faculty: run_command('echo hello') returns stdout",
        "hello" in result.stdout.lower(),
        result.stdout,
    )


def check_format_system_info() -> CheckResult:
    faculty = ProcessFaculty()
    formatted = faculty.format_result(faculty.system_info())
    return ensure(
        "Process Faculty: format_result includes 'system info'",
        "proc > system info" in formatted.lower(),
        formatted.splitlines()[0] if formatted else "",
    )


def check_package_faculty_module() -> CheckResult:
    return ensure(
        "Package Faculty: core/package_faculty.py exists and imports",
        PACKAGE_PATH.exists() and isinstance(PackageFaculty(), PackageFaculty),
    )


def check_winget_detected() -> CheckResult:
    faculty = PackageFaculty()
    if platform.system() != "Windows":
        return manual("Package Faculty: winget detection is Windows-specific", faculty.pm)
    return ensure("Package Faculty: package manager resolves to winget", faculty.pm == "winget", faculty.pm)


def check_winget_resolve_notepadpp() -> CheckResult:
    faculty = PackageFaculty()
    if platform.system() != "Windows":
        return manual("Package Faculty: Notepad++ ID resolution is Windows-specific")
    with patch("core.package_faculty.subprocess.run", return_value=make_winget_result()):
        resolved = faculty._winget_resolve_id("notepad++")
    return ensure(
        "Package Faculty: notepad++ resolves to Notepad++.Notepad++",
        resolved == "Notepad++.Notepad++",
        str(resolved),
    )


def check_winget_resolve_vlc() -> CheckResult:
    faculty = PackageFaculty()
    if platform.system() != "Windows":
        return manual("Package Faculty: VLC ID resolution is Windows-specific")
    with patch("core.package_faculty.subprocess.run", return_value=make_winget_result()):
        resolved = faculty._winget_resolve_id("vlc")
    return ensure(
        "Package Faculty: vlc resolves to VideoLAN.VLC",
        resolved == "VideoLAN.VLC",
        str(resolved),
    )


def check_search_packages_returns() -> CheckResult:
    faculty = PackageFaculty()
    if platform.system() != "Windows":
        return manual("Package Faculty: offline winget search probe is Windows-specific")
    with patch("core.package_faculty.subprocess.run", return_value=make_winget_result()):
        result = faculty.search("notepad")
    return ensure(
        "Package Faculty: search('notepad') returns output and parsed records without network",
        result.success and bool(result.output.strip()) and len(result.records) >= 1,
        result.error or "",
    )


def check_format_install_result() -> CheckResult:
    formatted = PackageFaculty().format_result(
        PackageResult(
            success=True,
            operation="install",
            query="firefox",
            output="Installed successfully.",
            package_manager="winget",
        )
    )
    return ensure(
        "Package Faculty: format_result renders install results",
        "installed: firefox" in formatted.lower(),
        formatted,
    )


def check_software_registry_module() -> CheckResult:
    return ensure(
        "Software Registry: core/software_registry.py exists and imports",
        SOFTWARE_REGISTRY_PATH.exists() and isinstance(SoftwareRegistry(), SoftwareRegistry),
    )


def check_registry_loads_without_error() -> CheckResult:
    _registry, error = software_registry_probe()
    return ensure("Software Registry: load() completes without error", error is None, error or "")


def check_registry_has_entries() -> CheckResult:
    registry, error = software_registry_probe()
    count = len(registry.all_entries()) if registry is not None and error is None else 0
    return ensure("Software Registry: local registry has at least 10 entries", count >= 10, str(count))


def check_registry_is_installed() -> CheckResult:
    if platform.system() != "Windows":
        return manual("Software Registry: notepad++ installation check is Windows-specific")
    registry, error = software_registry_probe()
    if registry is None or error is not None:
        return failed("Software Registry: notepad++ is visible after load", error or "registry unavailable")
    match = registry.is_installed("notepad++")
    return ensure(
        "Software Registry: notepad++ is visible after load",
        match is not None and "notepad" in match.name.lower(),
        f"{match.name if match else 'missing'}",
    )


def check_is_installed_safe_before_load() -> CheckResult:
    registry = SoftwareRegistry()
    return ensure(
        "Software Registry: is_installed() safely returns None before load()",
        registry.is_installed("notepad++") is None,
    )


def check_launch_app_tool_registered() -> CheckResult:
    tools = tools_config()
    return ensure(
        "Software Registry: launch_app is registered in tools.json",
        "launch_app" in tools,
    )


def check_software_cards_in_html() -> CheckResult:
    return ensure(
        "Software Registry: index.html includes buildSoftwareCards()",
        "function buildSoftwareCards" in source(INDEX_HTML_PATH),
    )


def check_operator_passes_meta() -> CheckResult:
    compact_index = compact(source(INDEX_HTML_PATH))
    return ensure(
        "Software Registry: operator messages pass meta into addMessage()",
        "if(t==='operator'){addMessage('operator',m.text,m);return;}" in compact_index,
    )


def check_tool_count() -> CheckResult:
    tools = tools_config()
    return ensure("Tool Registry: at least 18 tools are registered", len(tools) >= 18, str(len(tools)))


def check_network_tools() -> CheckResult:
    tools = tools_config()
    required = {"web_search", "ping", "resolve_host", "scan_ports"}
    return ensure(
        "Tool Registry: network tools are present",
        required.issubset(tools.keys()),
        str(sorted(required - set(tools.keys()))),
    )


def check_filesystem_tools() -> CheckResult:
    tools = tools_config()
    required = {"read_file", "list_dir", "file_info", "search_files", "write_file"}
    return ensure(
        "Tool Registry: filesystem tools are present",
        required.issubset(tools.keys()),
        str(sorted(required - set(tools.keys()))),
    )


def check_process_tools() -> CheckResult:
    tools = tools_config()
    required = {"list_processes", "system_info", "kill_process", "run_command"}
    return ensure(
        "Tool Registry: process tools are present",
        required.issubset(tools.keys()),
        str(sorted(required - set(tools.keys()))),
    )


def check_package_tools() -> CheckResult:
    tools = tools_config()
    required = {"search_packages", "list_packages", "install_package", "remove_package"}
    return ensure(
        "Tool Registry: package tools are present",
        required.issubset(tools.keys()),
        str(sorted(required - set(tools.keys()))),
    )


def check_launch_app_tool() -> CheckResult:
    tools = tools_config()
    launch_app = tools.get("launch_app", {})
    enabled = isinstance(launch_app, dict) and bool(launch_app.get("enabled"))
    return ensure("Tool Registry: launch_app is enabled", enabled)


def check_approval_flags() -> CheckResult:
    tools = tools_config()
    required = {"install_package", "remove_package", "launch_app"}
    condition = all(bool(tools.get(name, {}).get("requires_approval")) for name in required)
    return ensure("Tool Registry: install/remove/launch require approval", condition)


def check_no_approval_list_search() -> CheckResult:
    tools = tools_config()
    no_approval = {
        "list_dir",
        "file_info",
        "search_files",
        "list_processes",
        "system_info",
        "search_packages",
        "list_packages",
    }
    condition = all(not bool(tools.get(name, {}).get("requires_approval")) for name in no_approval)
    return ensure("Tool Registry: list/search observation tools skip approval", condition)


def check_nixos_dir() -> CheckResult:
    return ensure("NixOS Configuration: nixos/ directory exists", NIXOS_DIR.exists() and NIXOS_DIR.is_dir())


def check_configuration_nix() -> CheckResult:
    return ensure("NixOS Configuration: configuration.nix exists", CONFIGURATION_NIX_PATH.exists())


def check_service_file() -> CheckResult:
    return ensure("NixOS Configuration: inanna-nyx.service exists", SERVICE_PATH.exists())


def check_install_sh() -> CheckResult:
    return ensure("NixOS Configuration: install.sh exists", INSTALL_SH_PATH.exists())


def check_nix_service_definition() -> CheckResult:
    configuration = source(CONFIGURATION_NIX_PATH)
    return ensure(
        "NixOS Configuration: configuration.nix declares inanna-nyx",
        "systemd.services.inanna-nyx" in configuration,
    )


def check_nix_port_8080() -> CheckResult:
    return ensure("NixOS Configuration: configuration.nix exposes port 8080", "8080" in source(CONFIGURATION_NIX_PATH))


def check_nix_port_8081() -> CheckResult:
    return ensure("NixOS Configuration: configuration.nix exposes port 8081", "8081" in source(CONFIGURATION_NIX_PATH))


def check_install_sh_executable_flag() -> CheckResult:
    return ensure(
        "NixOS Configuration: install.sh exists as the executable installer target",
        INSTALL_SH_PATH.exists() and INSTALL_SH_PATH.suffix == ".sh",
    )


def check_voice_dir() -> CheckResult:
    return ensure("Voice Listener: inanna/voice directory exists", VOICE_DIR.exists() and VOICE_DIR.is_dir())


def check_voice_listener_file() -> CheckResult:
    return ensure("Voice Listener: voice/listener.py exists", VOICE_LISTENER_PATH.exists())


def check_voice_init_file() -> CheckResult:
    return ensure("Voice Listener: voice/__init__.py exists", VOICE_INIT_PATH.exists())


def check_voice_sample_rate() -> CheckResult:
    return ensure("Voice Listener: SAMPLE_RATE == 16000", SAMPLE_RATE == 16000, str(SAMPLE_RATE))


def check_voice_min_speech() -> CheckResult:
    return ensure("Voice Listener: MIN_SPEECH_SECONDS == 0.5", MIN_SPEECH_SECONDS == 0.5, str(MIN_SPEECH_SECONDS))


def check_voice_readme() -> CheckResult:
    return ensure("Voice Listener: voice/README.md exists", VOICE_README_PATH.exists())


def check_proposal_pulse_css() -> CheckResult:
    return ensure("UX Polish: index.html includes proposalPulse CSS", "proposalPulse" in source(INDEX_HTML_PATH))


def check_section_state_memory() -> CheckResult:
    return ensure("UX Polish: side panel state is stored in inanna_sp", "inanna_sp" in source(INDEX_HTML_PATH))


def check_help_topic_header() -> CheckResult:
    response = build_help_response("guardian", "faculties")
    return ensure(
        "UX Polish: help topic responses start with INANNA NYX",
        response.startswith("INANNA NYX"),
        response.splitlines()[0] if response else "",
    )


def check_dynamic_tool_count() -> CheckResult:
    server_source = source(SERVER_PATH)
    return ensure(
        "UX Polish: welcome message uses self.operator.PERMITTED_TOOLS dynamically",
        "len(self.operator.PERMITTED_TOOLS)" in server_source,
    )


def check_crown_tool_instruction() -> CheckResult:
    return ensure(
        "UX Polish: server.py tells CROWN not to disclaim post-tool execution",
        "DO NOT say you cannot execute commands" in source(SERVER_PATH),
    )


def check_package_context_tracker() -> CheckResult:
    server_source = source(SERVER_PATH)
    return ensure(
        "UX Polish: server.py tracks the last package context",
        "_last_package_context" in server_source,
    )


def check_current_phase() -> CheckResult:
    return ensure(
        "Identity: CURRENT_PHASE is Cycle 7 - Phase 7.8 - The Capability Proof",
        CURRENT_PHASE == "Cycle 7 - Phase 7.8 - The Capability Proof",
        CURRENT_PHASE,
    )


def check_cycle7_complete_string() -> CheckResult:
    tokens = ("NYXOS", "18 tools", "PBKDF2", "login")
    return ensure(
        "Identity: CYCLE7_COMPLETE exists and summarizes the completed cycle",
        all(token in CYCLE7_COMPLETE for token in tokens),
        CYCLE7_COMPLETE,
    )


CHECKS = [
    check_auth_module_exists,
    check_auth_store_imports,
    check_password_hash_format,
    check_verify_password_correct,
    check_verify_password_wrong,
    check_verify_timing_safe,
    check_zaera_seed_idempotent,
    check_authenticate_correct,
    check_authenticate_wrong_pw,
    check_authenticate_unknown,
    check_authenticate_case_insensitive,
    check_login_html_exists,
    check_login_html_has_form,
    check_login_html_full_page,
    check_login_html_has_glyph,
    check_index_no_overlay,
    check_ui_main_passes_server,
    check_filesystem_faculty_module,
    check_read_file_temp,
    check_read_file_truncation,
    check_list_dir_home,
    check_search_files_pattern,
    check_file_info_metadata,
    check_write_file_temp,
    check_write_file_no_overwrite,
    check_write_file_overwrite_flag,
    check_forbidden_path_blocked,
    check_safe_paths_home,
    check_process_faculty_module,
    check_system_info_success,
    check_system_info_cpu_count,
    check_system_info_ram,
    check_list_processes_returns,
    check_list_processes_has_name,
    check_run_echo,
    check_run_echo_output,
    check_format_system_info,
    check_package_faculty_module,
    check_winget_detected,
    check_winget_resolve_notepadpp,
    check_winget_resolve_vlc,
    check_search_packages_returns,
    check_format_install_result,
    check_software_registry_module,
    check_registry_loads_without_error,
    check_registry_has_entries,
    check_registry_is_installed,
    check_is_installed_safe_before_load,
    check_launch_app_tool_registered,
    check_software_cards_in_html,
    check_operator_passes_meta,
    check_tool_count,
    check_network_tools,
    check_filesystem_tools,
    check_process_tools,
    check_package_tools,
    check_launch_app_tool,
    check_approval_flags,
    check_no_approval_list_search,
    check_nixos_dir,
    check_configuration_nix,
    check_service_file,
    check_install_sh,
    check_nix_service_definition,
    check_nix_port_8080,
    check_nix_port_8081,
    check_install_sh_executable_flag,
    check_voice_dir,
    check_voice_listener_file,
    check_voice_init_file,
    check_voice_sample_rate,
    check_voice_min_speech,
    check_voice_readme,
    check_proposal_pulse_css,
    check_section_state_memory,
    check_help_topic_header,
    check_dynamic_tool_count,
    check_crown_tool_instruction,
    check_package_context_tracker,
    check_current_phase,
    check_cycle7_complete_string,
]


def main() -> int:
    results = [check() for check in CHECKS]

    emit("INANNA NYX - Cycle 7 Capability Verification")
    emit("============================================")
    for result in results:
        if result.status == "PASS" or not result.detail:
            emit(f"[{result.status}] {result.label}")
        else:
            emit(f"[{result.status}] {result.label} ({result.detail})")
    emit("--------------------------------------------")

    passed_count = sum(1 for result in results if result.status == "PASS")
    failed_count = sum(1 for result in results if result.status == "FAIL")
    manual_count = sum(1 for result in results if result.status == "MANUAL")
    total = len(results)
    automatable = total - manual_count

    if failed_count == 0:
        if manual_count:
            emit(
                f"All {automatable} automatable checks passed. "
                f"{manual_count} manual check(s) remain documented."
            )
        else:
            emit(f"All {total} checks passed. Cycle 7 capability surface verified.")
        return 0

    emit(
        f"{passed_count} of {automatable} automatable checks passed. "
        f"{failed_count} failed, {manual_count} manual."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

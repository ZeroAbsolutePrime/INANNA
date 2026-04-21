# CURRENT PHASE: Cycle 7 - Phase 7.4 - The Package Faculty
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Cycle: 7 - NYXOS: The Sovereign Intelligence Operating System**
**Replaces: Cycle 7 Phase 7.3 - The Process Faculty (COMPLETE)**

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — implement package tools and faculty
TESTER:     Codex — unit tests
VERIFIER:   Command Center — confirm after push

BUILDER forbidden from:
  - Modifying web UI (index.html, console.html)
  - Touching filesystem_faculty.py or process_faculty.py
  - Implementing actual NixOS package management on Windows
    (use platform detection, stub NixOS operations on Windows)

---

## What This Phase Is

Phase 7.3 gave INANNA eyes into the running system.
Phase 7.4 gives INANNA the ability to manage what is installed.

The Package Faculty is cross-platform:
  - On NixOS (Linux): uses nix-env and nix-channel
  - On Windows: uses winget
  - On Debian/Ubuntu: uses apt
  - On macOS: uses brew

All install and remove operations require proposal approval.
Search and list operations require no approval.

After this phase, you can say:
  "INANNA, what packages do I have installed?"
  "INANNA, search for a text editor"
  "INANNA, install firefox" (requires approval)
  "INANNA, remove an unused package" (requires approval)

---

## What You Are Building

### Task 1 - inanna/core/package_faculty.py

Create: inanna/core/package_faculty.py

The faculty detects the platform at init and selects
the appropriate package manager.

```python
from __future__ import annotations
import subprocess
import sys
import platform
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PackageRecord:
    name: str
    version: str
    description: str
    installed: bool


@dataclass
class PackageResult:
    success: bool
    operation: str      # search | list | install | remove | update
    query: str
    records: list[PackageRecord] = field(default_factory=list)
    output: str = ""
    error: Optional[str] = None
    package_manager: str = ""


class PackageFaculty:
    """
    Cross-platform governed package management.
    Detection order: NixOS → apt/dpkg → brew → winget → unknown
    Search and list: no approval required.
    Install and remove: ALWAYS require proposal approval.
    """

    def __init__(self) -> None:
        self.pm = self._detect_package_manager()

    def _detect_package_manager(self) -> str:
        system = platform.system().lower()
        # NixOS detection
        if system == "linux":
            try:
                with open("/etc/os-release") as f:
                    if "nixos" in f.read().lower():
                        return "nix"
            except Exception:
                pass
            # Debian/Ubuntu
            result = subprocess.run(["which", "apt"], capture_output=True)
            if result.returncode == 0:
                return "apt"
        if system == "darwin":
            result = subprocess.run(["which", "brew"], capture_output=True)
            if result.returncode == 0:
                return "brew"
        if system == "windows":
            result = subprocess.run(
                ["winget", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                return "winget"
        return "unknown"

    def search(self, query: str) -> PackageResult:
        if self.pm == "nix":
            return self._nix_search(query)
        if self.pm == "apt":
            return self._apt_search(query)
        if self.pm == "brew":
            return self._brew_search(query)
        if self.pm == "winget":
            return self._winget_search(query)
        return PackageResult(
            False, "search", query,
            error=f"No supported package manager detected on {platform.system()}.",
            package_manager="unknown",
        )

    def list_installed(self, filter_name: str = "") -> PackageResult:
        if self.pm == "nix":
            return self._nix_list(filter_name)
        if self.pm == "apt":
            return self._apt_list(filter_name)
        if self.pm == "brew":
            return self._brew_list(filter_name)
        if self.pm == "winget":
            return self._winget_list(filter_name)
        return PackageResult(
            False, "list", filter_name,
            error="No supported package manager detected.",
            package_manager="unknown",
        )

    def install(self, package_name: str) -> PackageResult:
        """ALWAYS requires proposal approval before calling."""
        if self.pm == "nix":
            return self._run(
                ["nix-env", "-iA", f"nixpkgs.{package_name}"],
                "install", package_name,
            )
        if self.pm == "apt":
            return self._run(
                ["apt-get", "install", "-y", package_name],
                "install", package_name,
            )
        if self.pm == "brew":
            return self._run(
                ["brew", "install", package_name],
                "install", package_name,
            )
        if self.pm == "winget":
            return self._run(
                ["winget", "install", "--id", package_name, "-e"],
                "install", package_name,
            )
        return PackageResult(
            False, "install", package_name,
            error="No supported package manager detected.",
            package_manager="unknown",
        )

    def remove(self, package_name: str) -> PackageResult:
        """ALWAYS requires proposal approval before calling."""
        if self.pm == "nix":
            return self._run(
                ["nix-env", "-e", package_name],
                "remove", package_name,
            )
        if self.pm == "apt":
            return self._run(
                ["apt-get", "remove", "-y", package_name],
                "remove", package_name,
            )
        if self.pm == "brew":
            return self._run(
                ["brew", "uninstall", package_name],
                "remove", package_name,
            )
        if self.pm == "winget":
            return self._run(
                ["winget", "uninstall", "--id", package_name],
                "remove", package_name,
            )
        return PackageResult(
            False, "remove", package_name,
            error="No supported package manager detected.",
            package_manager="unknown",
        )

    def _run(
        self, cmd: list[str], operation: str, query: str
    ) -> PackageResult:
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            output = result.stdout[:4096] + (
                "\n" + result.stderr[:512] if result.stderr else ""
            )
            return PackageResult(
                result.returncode == 0,
                operation, query,
                output=output.strip(),
                package_manager=self.pm,
                error=result.stderr[:200] if result.returncode != 0 else None,
            )
        except FileNotFoundError:
            return PackageResult(
                False, operation, query,
                error=f"Package manager '{self.pm}' not found.",
                package_manager=self.pm,
            )
        except subprocess.TimeoutExpired:
            return PackageResult(
                False, operation, query,
                error="Package operation timed out (120s).",
                package_manager=self.pm,
            )
        except Exception as e:
            return PackageResult(
                False, operation, query,
                error=str(e),
                package_manager=self.pm,
            )

    def _nix_search(self, query: str) -> PackageResult:
        return self._run(
            ["nix-env", "-qaP", f".*{query}.*"],
            "search", query,
        )

    def _nix_list(self, filter_name: str) -> PackageResult:
        result = self._run(["nix-env", "-q"], "list", filter_name)
        if result.success and filter_name:
            lines = [l for l in result.output.splitlines()
                     if filter_name.lower() in l.lower()]
            result.output = "\n".join(lines)
        return result

    def _apt_search(self, query: str) -> PackageResult:
        return self._run(
            ["apt-cache", "search", query],
            "search", query,
        )

    def _apt_list(self, filter_name: str) -> PackageResult:
        cmd = ["dpkg", "--get-selections"]
        if filter_name:
            cmd.extend([filter_name + "*"])
        return self._run(cmd, "list", filter_name)

    def _brew_search(self, query: str) -> PackageResult:
        return self._run(["brew", "search", query], "search", query)

    def _brew_list(self, filter_name: str) -> PackageResult:
        return self._run(["brew", "list", "--versions"], "list", filter_name)

    def _winget_search(self, query: str) -> PackageResult:
        return self._run(
            ["winget", "search", query, "--accept-source-agreements"],
            "search", query,
        )

    def _winget_list(self, filter_name: str) -> PackageResult:
        cmd = ["winget", "list", "--accept-source-agreements"]
        if filter_name:
            cmd.extend(["--name", filter_name])
        return self._run(cmd, "list", filter_name)

    def format_result(self, result: PackageResult) -> str:
        pm_label = f"[{result.package_manager}]" if result.package_manager else ""
        if not result.success:
            return f"pkg {pm_label} > error: {result.error}"

        if result.operation in ("search", "list"):
            lines = result.output.splitlines()
            if not lines:
                return f"pkg {pm_label} > no results for: {result.query}"
            shown = lines[:30]
            header = (
                f"pkg {pm_label} > {result.operation}: {result.query}"
                + (f" ({len(lines)} results)" if len(lines) > 30 else "")
            )
            return header + "\n\n" + "\n".join(shown)

        if result.operation == "install":
            return (
                f"pkg {pm_label} > installed: {result.query}\n"
                + (result.output[:500] if result.output else "Done.")
            )

        if result.operation == "remove":
            return (
                f"pkg {pm_label} > removed: {result.query}\n"
                + (result.output[:500] if result.output else "Done.")
            )

        return f"pkg {pm_label} > {result.operation}: {result.query}"
```

### Task 2 - Register package tools in tools.json

Add to inanna/config/tools.json:

```json
{
  "name": "search_packages",
  "description": "Search for available packages to install",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "query": "Package name or keyword to search for"
  }
},
{
  "name": "list_packages",
  "description": "List installed packages, optionally filtered by name",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "filter": "Optional name filter"
  }
},
{
  "name": "install_package",
  "description": "Install a package using the system package manager",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "package": "Package name to install"
  }
},
{
  "name": "remove_package",
  "description": "Remove an installed package",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "package": "Package name to remove"
  }
}
```

### Task 3 - Wire PackageFaculty into server.py and main.py

Instantiate at startup:
```python
from core.package_faculty import PackageFaculty
package_faculty = PackageFaculty()
```

Handle in _run_tool() following the same ToolResult pattern
as filesystem_faculty and process_faculty.

### Task 4 - Domain hints

Add to governance_signals.json domain_hints:
```json
"packages": [
  "install", "uninstall", "remove package", "search package",
  "list packages", "what is installed", "package manager",
  "nix-env", "apt", "brew", "winget", "software"
]
```

### Task 5 - Update help_system.py

Add packages section to HELP_COMMON and HELP_TOPICS.

### Task 6 - Update identity.py

CURRENT_PHASE = "Cycle 7 - Phase 7.4 - The Package Faculty"

### Task 7 - Tests

Create inanna/tests/test_package_faculty.py:
  - PackageFaculty instantiates
  - _detect_package_manager() returns a string
  - format_result() formats search result correctly
  - format_result() formats error correctly
  - format_result() for install shows package name
  - install() on unknown pm returns success=False
  - remove() on unknown pm returns success=False
  - search() on unknown pm returns success=False with message
  - list_installed() on unknown pm returns success=False

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_commands.py: add 4 package tools.

---

## Permitted file changes

inanna/identity.py
inanna/main.py
inanna/config/tools.json
inanna/config/governance_signals.json
inanna/core/package_faculty.py     <- NEW
inanna/core/help_system.py
inanna/core/state.py
inanna/ui/server.py
inanna/tests/test_package_faculty.py  <- NEW
inanna/tests/test_identity.py
inanna/tests/test_commands.py

---

## What You Are NOT Building

- No changes to index.html or console.html
- No NixOS channel management (nix-channel --update)
- No package upgrade/update operation (future phase)
- No dependency resolution display
- No voice integration (Phase 7.5)

---

## Definition of Done

- [ ] core/package_faculty.py with PackageFaculty
- [ ] Platform detection works on Windows (winget) and NixOS (nix)
- [ ] 4 new tools in tools.json (17 total)
- [ ] Package domain hints in governance_signals.json
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle7-phase4-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE7_PHASE4_REPORT.md
Stop. Do not begin Phase 7.5 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-21*
*INANNA learns to tend the garden of installed software.*
*Search is free. Installation requires your word.*
*Removal requires your word.*
*The system is yours. INANNA is the steward.*

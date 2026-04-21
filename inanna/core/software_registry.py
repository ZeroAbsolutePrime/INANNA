"""
INANNA NYX Software Registry
Knows what is installed, where it lives, and how to launch it.
Cross-platform: Windows (registry + winget), Linux (which + dpkg), macOS (brew + spotlight).
"""
from __future__ import annotations

import platform
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SoftwareEntry:
    name: str                  # display name
    pkg_id: str                # winget/apt/brew ID
    version: str
    executable: str            # path to executable if known
    source: str                # winget | registry | path | apt | brew
    installed: bool = True
    update_available: str = "" # version string if update exists


@dataclass
class LaunchResult:
    success: bool
    app_name: str
    executable: str = ""
    error: Optional[str] = None


class SoftwareRegistry:
    """
    Live registry of installed software.
    Supports: lookup by name, launch by name, deduplication check.
    """

    def __init__(self) -> None:
        self._cache: list[SoftwareEntry] = []
        self._loaded = False

    def load(self, force: bool = False) -> None:
        """Populate the registry from system sources."""
        if self._loaded and not force:
            return
        entries: list[SoftwareEntry] = []

        if platform.system() == "Windows":
            entries.extend(self._load_winget())
            entries.extend(self._load_app_paths_registry())
        elif platform.system() == "Linux":
            entries.extend(self._load_apt())
        elif platform.system() == "Darwin":
            entries.extend(self._load_brew())

        # Deduplicate: winget entries take priority over registry entries
        seen: dict[str, SoftwareEntry] = {}
        for e in entries:
            key = e.name.lower().strip()
            if key not in seen or e.source == "winget":
                seen[key] = e

        self._cache = list(seen.values())
        self._loaded = True

    def find(self, query: str) -> list[SoftwareEntry]:
        """Find installed software matching a query string."""
        self.load()
        q = query.lower().strip()
        results = []
        for e in self._cache:
            name_lower = e.name.lower()
            pkg_lower = e.pkg_id.lower()
            if q in name_lower or q in pkg_lower:
                results.append(e)
        # Sort: exact matches first, then partial
        results.sort(key=lambda e: (
            0 if e.name.lower() == q else
            1 if e.name.lower().startswith(q) else 2
        ))
        return results

    def is_installed(self, query: str) -> Optional[SoftwareEntry]:
        """Return the first matching installed entry, or None."""
        matches = self.find(query)
        return matches[0] if matches else None

    def launch(self, query: str) -> LaunchResult:
        """
        Launch an installed application by name.
        ALWAYS requires proposal approval before calling.
        """
        entry = self.is_installed(query)
        if not entry:
            return LaunchResult(
                False, query,
                error=f"No installed software matching '{query}' found."
            )
        if not entry.executable:
            # Try to launch by name via system
            return self._launch_by_name(entry.name, entry.pkg_id)

        exe = Path(entry.executable)
        if not exe.exists():
            return LaunchResult(
                False, entry.name, str(exe),
                error=f"Executable not found: {exe}"
            )
        try:
            subprocess.Popen([str(exe)], close_fds=True)
            return LaunchResult(True, entry.name, str(exe))
        except Exception as e:
            return LaunchResult(False, entry.name, str(exe), error=str(e))

    def _launch_by_name(self, name: str, pkg_id: str) -> LaunchResult:
        """Fallback: launch using OS mechanisms."""
        try:
            if platform.system() == "Windows":
                # Use Start-Process via PowerShell — works for registry-registered apps
                cmd = f'Start-Process "{name}"'
                result = subprocess.run(
                    ["powershell", "-Command", cmd],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return LaunchResult(True, name)
                # Try pkg_id as executable stem
                stem = pkg_id.split(".")[-1] if "." in pkg_id else pkg_id
                subprocess.Popen(["start", "", stem], shell=True)
                return LaunchResult(True, name)
            elif platform.system() == "Linux":
                subprocess.Popen(["xdg-open", name], close_fds=True)
                return LaunchResult(True, name)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", name], close_fds=True)
                return LaunchResult(True, name)
        except Exception as e:
            return LaunchResult(False, name, error=str(e))
        return LaunchResult(False, name, error="Launch not supported on this platform.")

    # ── Platform loaders ─────────────────────────────────────────

    def _load_winget(self) -> list[SoftwareEntry]:
        try:
            result = subprocess.run(
                ["winget", "list", "--accept-source-agreements"],
                capture_output=True, text=True, timeout=30
            )
            return self._parse_winget_installed(result.stdout)
        except Exception:
            return []

    def _parse_winget_installed(self, output: str) -> list[SoftwareEntry]:
        entries = []
        lines = output.splitlines()
        # Find header to get column positions
        header_line = ""
        for line in lines:
            if "Name" in line and "Id" in line and "Version" in line:
                header_line = line
                break
        if not header_line:
            return entries

        name_col = header_line.index("Name") if "Name" in header_line else 0
        id_col = header_line.index("Id") if "Id" in header_line else -1
        ver_col = header_line.index("Version") if "Version" in header_line else -1
        avail_col = header_line.index("Available") if "Available" in header_line else -1

        for line in lines:
            stripped = line.strip()
            if not stripped or set(stripped) == {"-"}:
                continue
            lowered = stripped.lower()
            if lowered.startswith(("name", "no package")):
                continue
            if id_col > 0 and ver_col > id_col:
                name = line[name_col:id_col].strip()
                pkg_id = line[id_col:ver_col].strip()
                version = line[ver_col:avail_col].strip() if avail_col > ver_col else line[ver_col:].strip().split()[0] if line[ver_col:].strip() else ""
                update = line[avail_col:].strip().split()[0] if avail_col > 0 and line[avail_col:].strip() else ""
            else:
                cols = [p.strip() for p in re.split(r"\s{2,}", stripped) if p.strip()]
                if len(cols) < 2:
                    continue
                name = cols[0]
                pkg_id = cols[1] if len(cols) > 1 else ""
                version = cols[2] if len(cols) > 2 else ""
                update = cols[3] if len(cols) > 3 else ""

            if not name or not pkg_id:
                continue
            # Skip ARP and MSIX entries (garbled or non-standard IDs)
            if pkg_id.startswith(("ARP\\", "MSIX\\")):
                continue
            # Skip entries with garbled unicode replacement characters
            if "\ufffd" in name or "\ufffd" in version:
                continue

            entries.append(SoftwareEntry(
                name=name,
                pkg_id=pkg_id,
                version=version,
                executable="",
                source="winget",
                update_available=update,
            ))
        return entries

    def _load_app_paths_registry(self) -> list[SoftwareEntry]:
        """Load from Windows App Paths registry — gives us executable paths."""
        entries = []
        try:
            import winreg
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    key = winreg.OpenKey(
                        hive,
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
                    )
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey = winreg.OpenKey(key, subkey_name)
                            try:
                                exe_path, _ = winreg.QueryValueEx(subkey, "")
                                exe_path = exe_path.strip('"').strip()
                                name = Path(subkey_name).stem
                                entries.append(SoftwareEntry(
                                    name=name,
                                    pkg_id=subkey_name,
                                    version="",
                                    executable=exe_path,
                                    source="registry",
                                ))
                            except FileNotFoundError:
                                pass
                            finally:
                                winreg.CloseKey(subkey)
                        except OSError:
                            break
                        i += 1
                    winreg.CloseKey(key)
                except FileNotFoundError:
                    pass
        except ImportError:
            pass  # Not on Windows
        return entries

    def _load_apt(self) -> list[SoftwareEntry]:
        try:
            result = subprocess.run(
                ["dpkg", "--get-selections"],
                capture_output=True, text=True, timeout=15
            )
            entries = []
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "install":
                    pkg = parts[0].split(":")[0]
                    entries.append(SoftwareEntry(
                        name=pkg, pkg_id=pkg, version="",
                        executable="", source="apt"
                    ))
            return entries
        except Exception:
            return []

    def _load_brew(self) -> list[SoftwareEntry]:
        try:
            result = subprocess.run(
                ["brew", "list", "--versions"],
                capture_output=True, text=True, timeout=15
            )
            entries = []
            for line in result.stdout.splitlines():
                parts = line.split()
                if parts:
                    name = parts[0]
                    version = parts[1] if len(parts) > 1 else ""
                    entries.append(SoftwareEntry(
                        name=name, pkg_id=name, version=version,
                        executable="", source="brew"
                    ))
            return entries
        except Exception:
            return []

    def summary(self) -> dict:
        """Return a summary for status payloads."""
        self.load()
        return {
            "total": len(self._cache),
            "sources": list({e.source for e in self._cache}),
        }

    def all_entries(self) -> list[SoftwareEntry]:
        self.load()
        return list(self._cache)

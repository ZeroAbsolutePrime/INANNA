from __future__ import annotations

import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PackageRecord:
    name: str
    version: str
    description: str
    installed: bool


@dataclass
class PackageResult:
    success: bool
    operation: str
    query: str
    records: list[PackageRecord] = field(default_factory=list)
    output: str = ""
    error: str | None = None
    package_manager: str = ""


class PackageFaculty:
    """
    Cross-platform governed package management for INANNA NYX.
    Search and list are observation operations.
    Install and remove remain approval-gated by routing.
    """

    def __init__(self) -> None:
        self.pm = self._detect_package_manager()

    def _detect_package_manager(self) -> str:
        system = platform.system().lower()
        if system == "linux":
            try:
                os_release = Path("/etc/os-release").read_text(encoding="utf-8")
                if "nixos" in os_release.lower():
                    return "nix"
            except OSError:
                pass
            if shutil.which("apt") and shutil.which("dpkg-query"):
                return "apt"
        if system == "darwin" and shutil.which("brew"):
            return "brew"
        if system == "windows":
            if shutil.which("winget"):
                return "winget"
            try:
                result = subprocess.run(
                    ["winget", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    return "winget"
            except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
                pass
        return "unknown"

    def search(self, query: str) -> PackageResult:
        cleaned_query = str(query or "").strip()
        if not cleaned_query:
            return PackageResult(
                False,
                "search",
                cleaned_query,
                error="Package search query is required.",
                package_manager=self.pm,
            )
        if self.pm == "nix":
            return self._nix_search(cleaned_query)
        if self.pm == "apt":
            return self._apt_search(cleaned_query)
        if self.pm == "brew":
            return self._brew_search(cleaned_query)
        if self.pm == "winget":
            return self._winget_search(cleaned_query)
        return PackageResult(
            False,
            "search",
            cleaned_query,
            error=f"No supported package manager detected on {platform.system()}.",
            package_manager="unknown",
        )

    def list_installed(self, filter_name: str = "") -> PackageResult:
        cleaned_filter = str(filter_name or "").strip()
        if self.pm == "nix":
            return self._nix_list(cleaned_filter)
        if self.pm == "apt":
            return self._apt_list(cleaned_filter)
        if self.pm == "brew":
            return self._brew_list(cleaned_filter)
        if self.pm == "winget":
            return self._winget_list(cleaned_filter)
        return PackageResult(
            False,
            "list",
            cleaned_filter,
            error="No supported package manager detected.",
            package_manager="unknown",
        )

    def install(self, package_name: str) -> PackageResult:
        cleaned_name = str(package_name or "").strip()
        if not cleaned_name:
            return PackageResult(
                False,
                "install",
                cleaned_name,
                error="Package name is required.",
                package_manager=self.pm,
            )
        if self.pm == "nix":
            return self._run(
                ["nix-env", "-iA", f"nixpkgs.{cleaned_name}"],
                "install",
                cleaned_name,
                timeout=120,
            )
        if self.pm == "apt":
            return self._run(
                ["apt-get", "install", "-y", cleaned_name],
                "install",
                cleaned_name,
                timeout=120,
            )
        if self.pm == "brew":
            return self._run(
                ["brew", "install", cleaned_name],
                "install",
                cleaned_name,
                timeout=120,
            )
        if self.pm == "winget":
            return self._run(
                ["winget", "install", "--id", cleaned_name, "-e"],
                "install",
                cleaned_name,
                timeout=120,
            )
        return PackageResult(
            False,
            "install",
            cleaned_name,
            error="No supported package manager detected.",
            package_manager="unknown",
        )

    def remove(self, package_name: str) -> PackageResult:
        cleaned_name = str(package_name or "").strip()
        if not cleaned_name:
            return PackageResult(
                False,
                "remove",
                cleaned_name,
                error="Package name is required.",
                package_manager=self.pm,
            )
        if self.pm == "nix":
            return self._run(
                ["nix-env", "-e", cleaned_name],
                "remove",
                cleaned_name,
                timeout=120,
            )
        if self.pm == "apt":
            return self._run(
                ["apt-get", "remove", "-y", cleaned_name],
                "remove",
                cleaned_name,
                timeout=120,
            )
        if self.pm == "brew":
            return self._run(
                ["brew", "uninstall", cleaned_name],
                "remove",
                cleaned_name,
                timeout=120,
            )
        if self.pm == "winget":
            return self._run(
                ["winget", "uninstall", "--id", cleaned_name],
                "remove",
                cleaned_name,
                timeout=120,
            )
        return PackageResult(
            False,
            "remove",
            cleaned_name,
            error="No supported package manager detected.",
            package_manager="unknown",
        )

    def _run(
        self,
        command: list[str],
        operation: str,
        query: str,
        timeout: int = 60,
    ) -> PackageResult:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            stdout = str(result.stdout or "").strip()
            stderr = str(result.stderr or "").strip()
            combined = stdout
            if stderr:
                combined = f"{combined}\n{stderr}".strip()
            return PackageResult(
                success=result.returncode == 0,
                operation=operation,
                query=query,
                output=combined[:4096],
                error=stderr[:512] if result.returncode != 0 and stderr else None,
                package_manager=self.pm,
            )
        except FileNotFoundError:
            return PackageResult(
                False,
                operation,
                query,
                error=f"Package manager '{self.pm}' not found.",
                package_manager=self.pm,
            )
        except subprocess.TimeoutExpired:
            return PackageResult(
                False,
                operation,
                query,
                error=f"Package operation timed out ({timeout}s).",
                package_manager=self.pm,
            )
        except Exception as error:
            return PackageResult(
                False,
                operation,
                query,
                error=str(error),
                package_manager=self.pm,
            )

    def _nix_search(self, query: str) -> PackageResult:
        result = self._run(["nix-env", "-qaP", f".*{query}.*"], "search", query)
        result.records = self._parse_nix_search(result.output)
        return result

    def _nix_list(self, filter_name: str) -> PackageResult:
        result = self._run(["nix-env", "-q"], "list", filter_name or "installed")
        result.records = self._parse_nix_list(result.output, filter_name)
        return result

    def _apt_search(self, query: str) -> PackageResult:
        result = self._run(["apt-cache", "search", query], "search", query)
        result.records = self._parse_apt_search(result.output)
        return result

    def _apt_list(self, filter_name: str) -> PackageResult:
        result = self._run(
            ["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\n"],
            "list",
            filter_name or "installed",
        )
        result.records = self._parse_dpkg_list(result.output, filter_name)
        return result

    def _brew_search(self, query: str) -> PackageResult:
        result = self._run(["brew", "search", query], "search", query)
        result.records = self._parse_brew_search(result.output)
        return result

    def _brew_list(self, filter_name: str) -> PackageResult:
        result = self._run(["brew", "list", "--versions"], "list", filter_name or "installed")
        result.records = self._parse_brew_list(result.output, filter_name)
        return result

    def _winget_search(self, query: str) -> PackageResult:
        result = self._run(
            ["winget", "search", query, "--accept-source-agreements"],
            "search",
            query,
        )
        result.records = self._parse_winget_table(result.output, installed=False)
        return result

    def _winget_list(self, filter_name: str) -> PackageResult:
        command = ["winget", "list", "--accept-source-agreements"]
        if filter_name:
            command.extend(["--name", filter_name])
        result = self._run(command, "list", filter_name or "installed")
        result.records = self._parse_winget_table(result.output, installed=True)
        if filter_name:
            lowered = filter_name.lower()
            result.records = [
                record for record in result.records if lowered in record.name.lower()
            ]
        return result

    def _split_name_version(self, value: str) -> tuple[str, str]:
        cleaned = str(value or "").strip()
        match = re.match(r"^(?P<name>.+?)-(?P<version>\d[\w.\-+]*)$", cleaned)
        if match:
            return match.group("name"), match.group("version")
        return cleaned, ""

    def _parse_nix_search(self, output: str) -> list[PackageRecord]:
        records: list[PackageRecord] = []
        for line in output.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            parts = cleaned.split(None, 1)
            name = parts[0].strip()
            version = parts[1].strip() if len(parts) > 1 else ""
            records.append(
                PackageRecord(
                    name=name,
                    version=version,
                    description="",
                    installed=False,
                )
            )
        return records

    def _parse_nix_list(self, output: str, filter_name: str = "") -> list[PackageRecord]:
        records: list[PackageRecord] = []
        lowered_filter = filter_name.lower()
        for line in output.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            name, version = self._split_name_version(cleaned)
            if lowered_filter and lowered_filter not in name.lower():
                continue
            records.append(
                PackageRecord(
                    name=name,
                    version=version,
                    description="",
                    installed=True,
                )
            )
        return records

    def _parse_apt_search(self, output: str) -> list[PackageRecord]:
        records: list[PackageRecord] = []
        for line in output.splitlines():
            cleaned = line.strip()
            if not cleaned or " - " not in cleaned:
                continue
            name, description = cleaned.split(" - ", 1)
            records.append(
                PackageRecord(
                    name=name.strip(),
                    version="",
                    description=description.strip(),
                    installed=False,
                )
            )
        return records

    def _parse_dpkg_list(self, output: str, filter_name: str = "") -> list[PackageRecord]:
        records: list[PackageRecord] = []
        lowered_filter = filter_name.lower()
        for line in output.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            parts = cleaned.split("\t")
            name = parts[0].strip()
            version = parts[1].strip() if len(parts) > 1 else ""
            if lowered_filter and lowered_filter not in name.lower():
                continue
            records.append(
                PackageRecord(
                    name=name,
                    version=version,
                    description="",
                    installed=True,
                )
            )
        return records

    def _parse_brew_search(self, output: str) -> list[PackageRecord]:
        records: list[PackageRecord] = []
        for line in output.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            records.append(
                PackageRecord(
                    name=cleaned,
                    version="",
                    description="",
                    installed=False,
                )
            )
        return records

    def _parse_brew_list(self, output: str, filter_name: str = "") -> list[PackageRecord]:
        records: list[PackageRecord] = []
        lowered_filter = filter_name.lower()
        for line in output.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            parts = cleaned.split()
            name = parts[0].strip()
            version = " ".join(parts[1:]).strip()
            if lowered_filter and lowered_filter not in name.lower():
                continue
            records.append(
                PackageRecord(
                    name=name,
                    version=version,
                    description="",
                    installed=True,
                )
            )
        return records

    def _parse_winget_table(self, output: str, installed: bool) -> list[PackageRecord]:
        records: list[PackageRecord] = []
        for line in output.splitlines():
            cleaned = line.rstrip()
            stripped = cleaned.strip()
            if not stripped:
                continue
            if set(stripped) == {"-"}:
                continue
            lowered = stripped.lower()
            if lowered.startswith(("name", "no package found", "the `msstore` source")):
                continue
            columns = [part.strip() for part in re.split(r"\s{2,}", stripped) if part.strip()]
            if not columns:
                continue
            name = columns[0]
            version = columns[2] if len(columns) >= 3 else ""
            description = columns[1] if len(columns) >= 2 else ""
            records.append(
                PackageRecord(
                    name=name,
                    version=version,
                    description=description,
                    installed=installed,
                )
            )
        return records

    def format_result(self, result: PackageResult) -> str:
        pm_label = f"[{result.package_manager}]" if result.package_manager else ""
        if not result.success:
            return f"pkg {pm_label} > error: {result.error or 'Unknown package error.'}"

        if result.operation in {"search", "list"}:
            scope = result.query or "installed"
            if result.records:
                lines = [f"pkg {pm_label} > {result.operation}: {scope}"]
                visible = result.records[:30]
                for record in visible:
                    line = f"  {record.name}"
                    if record.version:
                        line += f" {record.version}"
                    if record.description:
                        line += f" - {record.description}"
                    lines.append(line)
                if len(result.records) > len(visible):
                    lines.append(f"  ... {len(result.records) - len(visible)} more")
                return "\n".join(lines)
            if result.output.strip():
                return f"pkg {pm_label} > {result.operation}: {scope}\n\n{result.output[:2000]}"
            return f"pkg {pm_label} > no results for: {scope}"

        if result.operation == "install":
            detail = result.output[:500] if result.output else "Done."
            return f"pkg {pm_label} > installed: {result.query}\n{detail}"

        if result.operation == "remove":
            detail = result.output[:500] if result.output else "Done."
            return f"pkg {pm_label} > removed: {result.query}\n{detail}"

        return f"pkg {pm_label} > {result.operation}: {result.query}"

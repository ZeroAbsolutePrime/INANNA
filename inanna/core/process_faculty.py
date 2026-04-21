from __future__ import annotations

import csv
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field


@dataclass
class ProcessRecord:
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    username: str
    started_at: str
    cmdline: str


@dataclass
class SystemInfo:
    platform: str
    hostname: str
    uptime_seconds: int
    uptime_human: str
    cpu_count: int
    cpu_percent: float
    ram_total_gb: float
    ram_used_gb: float
    ram_percent: float
    disk_total_gb: float
    disk_used_gb: float
    disk_percent: float
    python_version: str


@dataclass
class ProcessResult:
    success: bool
    operation: str
    query: str
    records: list[ProcessRecord] = field(default_factory=list)
    system_info: SystemInfo | None = None
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    error: str | None = None
    count: int = 0


class ProcessFaculty:
    """
    Governed process and system operations for INANNA NYX.
    """

    HAS_PSUTIL = False

    def __init__(self) -> None:
        self._psutil = None
        try:
            import psutil  # type: ignore

            self._psutil = psutil
            ProcessFaculty.HAS_PSUTIL = True
        except ImportError:
            ProcessFaculty.HAS_PSUTIL = False

    def _format_uptime(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    def list_processes(
        self,
        filter_name: str = "",
        sort_by: str = "memory",
        limit: int = 20,
    ) -> ProcessResult:
        cleaned_filter = str(filter_name or "").strip()
        cleaned_sort = str(sort_by or "memory").strip().lower()
        cleaned_limit = max(1, min(int(limit or 20), 100))

        if self._psutil is None:
            return self._fallback_list(cleaned_filter, cleaned_sort, cleaned_limit)

        psutil = self._psutil
        try:
            records: list[ProcessRecord] = []
            for proc in psutil.process_iter(
                [
                    "pid",
                    "name",
                    "status",
                    "cpu_percent",
                    "memory_info",
                    "memory_percent",
                    "username",
                    "create_time",
                    "cmdline",
                ]
            ):
                try:
                    info = proc.info
                    name = str(info.get("name") or "").strip()
                    cmdline_parts = info.get("cmdline") or []
                    cmdline = " ".join(str(part) for part in cmdline_parts).strip()
                    searchable = f"{name} {cmdline}".lower()
                    if cleaned_filter and cleaned_filter.lower() not in searchable:
                        continue
                    memory_info = info.get("memory_info")
                    memory_mb = 0.0
                    if memory_info is not None:
                        memory_mb = round(float(memory_info.rss) / 1024 / 1024, 1)
                    create_time = float(info.get("create_time") or 0)
                    try:
                        started_at = time.strftime("%H:%M", time.localtime(create_time))
                    except Exception:
                        started_at = "?"
                    records.append(
                        ProcessRecord(
                            pid=int(info.get("pid") or 0),
                            name=name or cmdline[:40] or "?",
                            status=str(info.get("status") or "?"),
                            cpu_percent=round(float(info.get("cpu_percent") or 0.0), 1),
                            memory_mb=memory_mb,
                            memory_percent=round(float(info.get("memory_percent") or 0.0), 1),
                            username=str(info.get("username") or "?"),
                            started_at=started_at,
                            cmdline=(cmdline or name)[:160],
                        )
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            records = self._sort_records(records, cleaned_sort)
            total = len(records)
            return ProcessResult(
                success=True,
                operation="list",
                query=cleaned_filter or "all",
                records=records[:cleaned_limit],
                count=total,
            )
        except Exception as error:
            return ProcessResult(
                success=False,
                operation="list",
                query=cleaned_filter or "all",
                error=str(error),
            )

    def _sort_records(
        self,
        records: list[ProcessRecord],
        sort_by: str,
    ) -> list[ProcessRecord]:
        items = list(records)
        if sort_by == "cpu":
            items.sort(key=lambda record: record.cpu_percent, reverse=True)
        elif sort_by == "name":
            items.sort(key=lambda record: record.name.lower())
        elif sort_by == "pid":
            items.sort(key=lambda record: record.pid)
        else:
            items.sort(key=lambda record: record.memory_mb, reverse=True)
        return items

    def _fallback_list(
        self,
        filter_name: str = "",
        sort_by: str = "memory",
        limit: int = 20,
    ) -> ProcessResult:
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                records: list[ProcessRecord] = []
                for row in csv.reader(result.stdout.splitlines()):
                    if len(row) < 5:
                        continue
                    name = row[0].strip()
                    if filter_name and filter_name.lower() not in name.lower():
                        continue
                    memory_text = row[4].replace(",", "").replace(" K", "").strip()
                    try:
                        memory_mb = round(int(memory_text) / 1024, 1)
                    except ValueError:
                        memory_mb = 0.0
                    records.append(
                        ProcessRecord(
                            pid=int(row[1]) if str(row[1]).isdigit() else 0,
                            name=name,
                            status="running",
                            cpu_percent=0.0,
                            memory_mb=memory_mb,
                            memory_percent=0.0,
                            username="?",
                            started_at="?",
                            cmdline=name,
                        )
                    )
            else:
                result = subprocess.run(
                    ["ps", "-eo", "pid=,pcpu=,pmem=,user=,comm=,args="],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                records = []
                for line in result.stdout.strip().splitlines():
                    parts = line.strip().split(None, 5)
                    if len(parts) < 6:
                        continue
                    pid_text, cpu_text, mem_text, user_text, name_text, args_text = parts
                    searchable = f"{name_text} {args_text}".lower()
                    if filter_name and filter_name.lower() not in searchable:
                        continue
                    try:
                        cpu_percent = float(cpu_text)
                    except ValueError:
                        cpu_percent = 0.0
                    try:
                        memory_percent = float(mem_text)
                    except ValueError:
                        memory_percent = 0.0
                    records.append(
                        ProcessRecord(
                            pid=int(pid_text) if pid_text.isdigit() else 0,
                            name=name_text[:40],
                            status="?",
                            cpu_percent=round(cpu_percent, 1),
                            memory_mb=0.0,
                            memory_percent=round(memory_percent, 1),
                            username=user_text[:32],
                            started_at="?",
                            cmdline=args_text[:160],
                        )
                    )

            records = self._sort_records(records, sort_by)
            total = len(records)
            return ProcessResult(
                success=True,
                operation="list",
                query=filter_name or "all",
                records=records[:limit],
                count=total,
            )
        except Exception as error:
            return ProcessResult(
                success=False,
                operation="list",
                query=filter_name or "all",
                error=str(error),
            )

    def system_info(self) -> ProcessResult:
        if self._psutil is None:
            return self._fallback_system_info()

        psutil = self._psutil
        try:
            boot_time = float(psutil.boot_time())
            uptime_seconds = max(int(time.time() - boot_time), 0)
            cpu_percent = float(psutil.cpu_percent(interval=0.1))
            ram = psutil.virtual_memory()
            disk_root = PathAnchor.current()
            disk = psutil.disk_usage(disk_root)
            info = SystemInfo(
                platform=f"{platform.system()} {platform.release()}".strip(),
                hostname=platform.node(),
                uptime_seconds=uptime_seconds,
                uptime_human=self._format_uptime(uptime_seconds),
                cpu_count=int(psutil.cpu_count() or (os.cpu_count() or 1)),
                cpu_percent=round(cpu_percent, 1),
                ram_total_gb=round(float(ram.total) / 1024**3, 1),
                ram_used_gb=round(float(ram.used) / 1024**3, 1),
                ram_percent=round(float(ram.percent), 1),
                disk_total_gb=round(float(disk.total) / 1024**3, 1),
                disk_used_gb=round(float(disk.used) / 1024**3, 1),
                disk_percent=round(float(disk.percent), 1),
                python_version=sys.version.split()[0],
            )
            return ProcessResult(True, "system", "system", system_info=info)
        except Exception as error:
            return ProcessResult(False, "system", "system", error=str(error))

    def _fallback_system_info(self) -> ProcessResult:
        try:
            disk_root = PathAnchor.current()
            disk = shutil.disk_usage(disk_root)
            info = SystemInfo(
                platform=f"{platform.system()} {platform.release()}".strip(),
                hostname=platform.node(),
                uptime_seconds=0,
                uptime_human="unknown",
                cpu_count=int(os.cpu_count() or 1),
                cpu_percent=0.0,
                ram_total_gb=0.0,
                ram_used_gb=0.0,
                ram_percent=0.0,
                disk_total_gb=round(float(disk.total) / 1024**3, 1),
                disk_used_gb=round(float(disk.used) / 1024**3, 1),
                disk_percent=round((float(disk.used) / float(disk.total) * 100.0), 1)
                if disk.total
                else 0.0,
                python_version=sys.version.split()[0],
            )
            return ProcessResult(True, "system", "system", system_info=info)
        except Exception as error:
            return ProcessResult(False, "system", "system", error=str(error))

    def kill_process(self, pid: int) -> ProcessResult:
        cleaned_pid = int(pid or 0)
        if cleaned_pid <= 0:
            return ProcessResult(False, "kill", str(pid), error=f"No process with pid {pid}.")
        if self._psutil is None:
            return ProcessResult(
                False,
                "kill",
                str(cleaned_pid),
                error="psutil not available. Install: pip install psutil",
            )

        psutil = self._psutil
        try:
            proc = psutil.Process(cleaned_pid)
            name = proc.name()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
            return ProcessResult(
                True,
                "kill",
                str(cleaned_pid),
                stdout=f"Process {name} (pid {cleaned_pid}) terminated.",
            )
        except psutil.NoSuchProcess:
            return ProcessResult(
                False,
                "kill",
                str(cleaned_pid),
                error=f"No process with pid {cleaned_pid}.",
            )
        except psutil.AccessDenied:
            return ProcessResult(
                False,
                "kill",
                str(cleaned_pid),
                error=f"Access denied: cannot kill pid {cleaned_pid}.",
            )
        except Exception as error:
            return ProcessResult(False, "kill", str(cleaned_pid), error=str(error))

    def run_command(self, command: str, timeout: int = 30) -> ProcessResult:
        cleaned_command = str(command or "").strip()
        cleaned_timeout = max(1, min(int(timeout or 30), 300))
        if not cleaned_command:
            return ProcessResult(False, "run", cleaned_command, error="Command is required.")
        if cleaned_command.lower().startswith(("sudo ", "doas ", "runas ")):
            return ProcessResult(
                False,
                "run",
                cleaned_command,
                error="Elevated commands are not allowed through run_command.",
            )

        try:
            result = subprocess.run(
                cleaned_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=cleaned_timeout,
            )
            return ProcessResult(
                success=result.returncode == 0,
                operation="run",
                query=cleaned_command,
                stdout=result.stdout[:4096],
                stderr=result.stderr[:1024],
                returncode=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ProcessResult(
                False,
                "run",
                cleaned_command,
                error=f"Command timed out after {cleaned_timeout}s.",
            )
        except Exception as error:
            return ProcessResult(False, "run", cleaned_command, error=str(error))

    def format_result(self, result: ProcessResult) -> str:
        if not result.success:
            return f"proc > error: {result.error or 'Unknown process error.'}"

        if result.operation == "list":
            lines = [
                f"proc > processes ({result.count} total"
                + (
                    f", showing top {len(result.records)}"
                    if result.count > len(result.records)
                    else ""
                )
                + ")",
                f"{'PID':>7}  {'NAME':<28}  {'CPU':>5}  {'MEM':>8}  {'STATUS':<10}",
                "-" * 65,
            ]
            for record in result.records:
                lines.append(
                    f"{record.pid:>7}  {record.name[:28]:<28}  "
                    f"{record.cpu_percent:>4.1f}%  "
                    f"{record.memory_mb:>6.1f}MB  {record.status:<10}"
                )
            return "\n".join(lines)

        if result.operation == "system":
            info = result.system_info
            if info is None:
                return "proc > no system info"

            def bar(percent: float) -> str:
                count = max(0, min(int(percent // 10), 10))
                return ("#" * count).ljust(10) + f" {percent:.0f}%"

            return "\n".join(
                [
                    "proc > system info",
                    f"  host:     {info.hostname}",
                    f"  platform: {info.platform}",
                    f"  uptime:   {info.uptime_human}",
                    f"  python:   {info.python_version}",
                    "",
                    f"  CPU ({info.cpu_count} cores)  {bar(info.cpu_percent)}",
                    f"  RAM {info.ram_used_gb:.1f}/{info.ram_total_gb:.1f}GB  {bar(info.ram_percent)}",
                    f"  DISK {info.disk_used_gb:.1f}/{info.disk_total_gb:.1f}GB  {bar(info.disk_percent)}",
                ]
            )

        if result.operation == "kill":
            return f"proc > {result.stdout}"

        if result.operation == "run":
            lines = [f"proc > run: {result.query}", f"     exit: {result.returncode}"]
            if result.stdout:
                lines.extend(["", result.stdout.rstrip()])
            if result.stderr:
                lines.append(f"stderr: {result.stderr.rstrip()[:200]}")
            return "\n".join(lines)

        return f"proc > {result.operation}: done"


class PathAnchor:
    @staticmethod
    def current() -> str:
        if os.name == "nt":
            return os.environ.get("SystemDrive", "C:") + "\\"
        return "/"

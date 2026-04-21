# CURRENT PHASE: Cycle 7 - Phase 7.3 - The Process Faculty
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Cycle: 7 - NYXOS: The Sovereign Intelligence Operating System**
**Replaces: Cycle 7 Phase 7.2 - The File System Faculty (COMPLETE)**

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — implement process tools and faculty
TESTER:     Codex — unit tests + integration verification
VERIFIER:   Command Center — confirm after push

BUILDER forbidden from:
  - Modifying web UI (index.html, console.html)
  - Changing governance architecture
  - Touching filesystem_faculty.py

---

## What This Phase Is

Phase 7.2 gave INANNA hands — the ability to read and write files.
Phase 7.3 gives INANNA eyes into the running system.

The Process Faculty allows INANNA to:
  - See what processes are running on your machine
  - See how much CPU and memory each process uses
  - Get overall system health (CPU, RAM, disk, uptime)
  - Kill a process — always with proposal approval
  - Run a shell command — always with proposal approval

After this phase, you can say:
  "INANNA, what is using all my memory?"
  "INANNA, how is the system doing?"
  "INANNA, show me all Python processes"
  "INANNA, kill the process called firefox" (requires approval)
  "INANNA, run echo hello" (requires approval)

Every destructive operation requires proposal approval.
Process listing and system info require no approval.
This is the principle: observation is free, action requires consent.

---

## What You Are Building

### Task 1 - inanna/core/process_faculty.py

Create: inanna/core/process_faculty.py

```python
from __future__ import annotations
import os
import sys
import time
import platform
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProcessRecord:
    pid: int
    name: str
    status: str          # running | sleeping | stopped | zombie
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    username: str
    started_at: str
    cmdline: str         # truncated command line


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
    operation: str       # list | info | kill | system | run
    query: str
    records: list[ProcessRecord] = field(default_factory=list)
    system_info: Optional[SystemInfo] = None
    stdout: str = ""
    stderr: str = ""
    returncode: Optional[int] = None
    error: Optional[str] = None
    count: int = 0


class ProcessFaculty:
    """
    Governed process and system operations for INANNA NYX.

    Observation operations (no approval required):
      list_processes, system_info

    Action operations (ALWAYS require proposal approval):
      kill_process, run_command

    Cross-platform: works on Windows, Linux (NixOS), macOS.
    Graceful fallback if psutil is not installed.
    """

    HAS_PSUTIL = False

    def __init__(self) -> None:
        try:
            import psutil  # noqa: F401
            ProcessFaculty.HAS_PSUTIL = True
        except ImportError:
            ProcessFaculty.HAS_PSUTIL = False

    def _format_uptime(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"

    def list_processes(
        self,
        filter_name: str = "",
        sort_by: str = "memory",  # memory | cpu | name | pid
        limit: int = 20,
    ) -> ProcessResult:
        if not self.HAS_PSUTIL:
            return self._fallback_list()
        import psutil
        try:
            records = []
            for proc in psutil.process_iter(
                ["pid", "name", "status", "cpu_percent",
                 "memory_info", "memory_percent", "username",
                 "create_time", "cmdline"]
            ):
                try:
                    info = proc.info
                    name = info.get("name") or ""
                    if filter_name and filter_name.lower() not in name.lower():
                        continue
                    mem_info = info.get("memory_info")
                    mem_mb = round(mem_info.rss / 1024 / 1024, 1) if mem_info else 0.0
                    cmdline = info.get("cmdline") or []
                    cmd = " ".join(cmdline)[:80] if cmdline else name
                    create_time = info.get("create_time") or 0
                    try:
                        started = time.strftime(
                            "%H:%M", time.localtime(create_time)
                        )
                    except Exception:
                        started = "?"
                    records.append(ProcessRecord(
                        pid=info.get("pid") or 0,
                        name=name,
                        status=info.get("status") or "?",
                        cpu_percent=round(info.get("cpu_percent") or 0.0, 1),
                        memory_mb=mem_mb,
                        memory_percent=round(info.get("memory_percent") or 0.0, 1),
                        username=info.get("username") or "?",
                        started_at=started,
                        cmdline=cmd,
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort
            if sort_by == "cpu":
                records.sort(key=lambda r: r.cpu_percent, reverse=True)
            elif sort_by == "name":
                records.sort(key=lambda r: r.name.lower())
            elif sort_by == "pid":
                records.sort(key=lambda r: r.pid)
            else:  # memory default
                records.sort(key=lambda r: r.memory_mb, reverse=True)

            total = len(records)
            records = records[:limit]

            return ProcessResult(
                True, "list", filter_name or "all",
                records=records, count=total,
            )
        except Exception as e:
            return ProcessResult(False, "list", filter_name, error=str(e))

    def _fallback_list(self) -> ProcessResult:
        """Fallback when psutil is not available — use OS commands."""
        import subprocess
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, timeout=10
                )
                records = []
                for line in result.stdout.strip().splitlines()[:20]:
                    parts = [p.strip('"') for p in line.split('","')]
                    if len(parts) >= 5:
                        try:
                            mem_kb = int(parts[4].replace(",","").replace(" K","").strip())
                        except Exception:
                            mem_kb = 0
                        records.append(ProcessRecord(
                            pid=int(parts[1]) if parts[1].isdigit() else 0,
                            name=parts[0], status="running",
                            cpu_percent=0.0,
                            memory_mb=round(mem_kb / 1024, 1),
                            memory_percent=0.0,
                            username="?", started_at="?",
                            cmdline=parts[0],
                        ))
                return ProcessResult(True, "list", "all", records=records, count=len(records))
            else:
                result = subprocess.run(
                    ["ps", "aux", "--sort=-%mem"],
                    capture_output=True, text=True, timeout=10
                )
                records = []
                for line in result.stdout.strip().splitlines()[1:21]:
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        records.append(ProcessRecord(
                            pid=int(parts[1]) if parts[1].isdigit() else 0,
                            name=parts[10][:40],
                            status="?",
                            cpu_percent=float(parts[2]) if parts[2].replace('.','').isdigit() else 0.0,
                            memory_mb=0.0,
                            memory_percent=float(parts[3]) if parts[3].replace('.','').isdigit() else 0.0,
                            username=parts[0][:16],
                            started_at=parts[8],
                            cmdline=parts[10][:80],
                        ))
                return ProcessResult(True, "list", "all", records=records, count=len(records))
        except Exception as e:
            return ProcessResult(False, "list", "all", error=str(e))

    def system_info(self) -> ProcessResult:
        if not self.HAS_PSUTIL:
            return self._fallback_system_info()
        import psutil
        try:
            boot_time = psutil.boot_time()
            uptime = int(time.time() - boot_time)
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            info = SystemInfo(
                platform=platform.system() + " " + platform.release(),
                hostname=platform.node(),
                uptime_seconds=uptime,
                uptime_human=self._format_uptime(uptime),
                cpu_count=psutil.cpu_count(),
                cpu_percent=cpu,
                ram_total_gb=round(ram.total / 1024**3, 1),
                ram_used_gb=round(ram.used / 1024**3, 1),
                ram_percent=ram.percent,
                disk_total_gb=round(disk.total / 1024**3, 1),
                disk_used_gb=round(disk.used / 1024**3, 1),
                disk_percent=disk.percent,
                python_version=sys.version.split()[0],
            )
            return ProcessResult(True, "system", "info", system_info=info)
        except Exception as e:
            return ProcessResult(False, "system", "info", error=str(e))

    def _fallback_system_info(self) -> ProcessResult:
        info = SystemInfo(
            platform=platform.system() + " " + platform.release(),
            hostname=platform.node(),
            uptime_seconds=0,
            uptime_human="unknown",
            cpu_count=os.cpu_count() or 1,
            cpu_percent=0.0,
            ram_total_gb=0.0,
            ram_used_gb=0.0,
            ram_percent=0.0,
            disk_total_gb=0.0,
            disk_used_gb=0.0,
            disk_percent=0.0,
            python_version=sys.version.split()[0],
        )
        return ProcessResult(True, "system", "info", system_info=info)

    def kill_process(self, pid: int) -> ProcessResult:
        """
        Kill a process by PID.
        ALWAYS requires proposal approval before calling.
        """
        if not self.HAS_PSUTIL:
            return ProcessResult(
                False, "kill", str(pid),
                error="psutil not available. Install: pip install psutil"
            )
        import psutil
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                proc.kill()
            return ProcessResult(
                True, "kill", str(pid),
                stdout=f"Process {name} (pid {pid}) terminated.",
            )
        except psutil.NoSuchProcess:
            return ProcessResult(
                False, "kill", str(pid),
                error=f"No process with pid {pid}."
            )
        except psutil.AccessDenied:
            return ProcessResult(
                False, "kill", str(pid),
                error=f"Access denied: cannot kill pid {pid}."
            )
        except Exception as e:
            return ProcessResult(False, "kill", str(pid), error=str(e))

    def run_command(
        self, command: str, timeout: int = 30
    ) -> ProcessResult:
        """
        Run a shell command.
        ALWAYS requires proposal approval before calling.
        """
        import subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ProcessResult(
                result.returncode == 0,
                "run", command,
                stdout=result.stdout[:4096],
                stderr=result.stderr[:1024],
                returncode=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ProcessResult(
                False, "run", command,
                error=f"Command timed out after {timeout}s."
            )
        except Exception as e:
            return ProcessResult(False, "run", command, error=str(e))

    def format_result(self, result: ProcessResult) -> str:
        if not result.success:
            return f"proc > error: {result.error}"

        if result.operation == "list":
            lines = [
                f"proc > processes ({result.count} total"
                + (f", showing top {len(result.records)}" if result.count > len(result.records) else "")
                + f", sorted by {'memory' if True else '?'})",
                f"{'PID':>7}  {'NAME':<28}  {'CPU':>5}  {'MEM':>8}  {'STATUS':<10}",
                "─" * 65,
            ]
            for r in result.records:
                lines.append(
                    f"{r.pid:>7}  {r.name[:28]:<28}  "
                    f"{r.cpu_percent:>4.1f}%  "
                    f"{r.memory_mb:>6.1f}MB  {r.status:<10}"
                )
            return "\n".join(lines)

        if result.operation == "system":
            s = result.system_info
            if not s:
                return "proc > no system info"
            bar = lambda pct: ("█" * int(pct / 10)).ljust(10) + f" {pct:.0f}%"
            return (
                f"proc > system info\n"
                f"  host:     {s.hostname}\n"
                f"  platform: {s.platform}\n"
                f"  uptime:   {s.uptime_human}\n"
                f"  python:   {s.python_version}\n"
                f"\n"
                f"  CPU ({s.cpu_count} cores)  {bar(s.cpu_percent)}\n"
                f"  RAM {s.ram_used_gb:.1f}/{s.ram_total_gb:.1f}GB  {bar(s.ram_percent)}\n"
                f"  DISK {s.disk_used_gb:.1f}/{s.disk_total_gb:.1f}GB  {bar(s.disk_percent)}"
            )

        if result.operation == "kill":
            return f"proc > {result.stdout}"

        if result.operation == "run":
            lines = [f"proc > run: {result.query}",
                     f"     exit: {result.returncode}"]
            if result.stdout:
                lines.append("")
                lines.append(result.stdout.rstrip())
            if result.stderr:
                lines.append(f"stderr: {result.stderr.rstrip()[:200]}")
            return "\n".join(lines)

        return f"proc > {result.operation}: done"
```

### Task 2 - Register process tools in tools.json

Add to inanna/config/tools.json:

```json
{
  "name": "list_processes",
  "description": "List running processes sorted by memory or CPU",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "filter": "Optional name filter (e.g. python, firefox)",
    "sort": "Sort by: memory (default), cpu, name, pid",
    "limit": "Max results to show (default 20)"
  }
},
{
  "name": "system_info",
  "description": "Get system health: CPU, RAM, disk, uptime",
  "requires_approval": false,
  "enabled": true,
  "parameters": {}
},
{
  "name": "kill_process",
  "description": "Terminate a running process by PID",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "pid": "Process ID to terminate"
  }
},
{
  "name": "run_command",
  "description": "Execute a shell command",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "command": "Shell command to run",
    "timeout": "Timeout in seconds (default 30)"
  }
}
```

### Task 3 - Wire ProcessFaculty into server.py and main.py

Instantiate at startup:
```python
from core.process_faculty import ProcessFaculty
process_faculty = ProcessFaculty()
```

Handle in _run_tool():
```python
if tool_name == "list_processes":
    result = process_faculty.list_processes(
        filter_name=args.get("filter", ""),
        sort_by=args.get("sort", "memory"),
        limit=int(args.get("limit", 20)),
    )
    return ToolResult(
        tool="list_processes",
        query=args.get("filter", "all"),
        success=result.success,
        data={"count": result.count},
        error=result.error,
        formatted=process_faculty.format_result(result),
    )

if tool_name == "system_info":
    result = process_faculty.system_info()
    return ToolResult(
        tool="system_info", query="system",
        success=result.success,
        data={},
        error=result.error,
        formatted=process_faculty.format_result(result),
    )

if tool_name == "kill_process":
    pid = int(args.get("pid", 0))
    result = process_faculty.kill_process(pid)
    return ToolResult(
        tool="kill_process", query=str(pid),
        success=result.success,
        data={},
        error=result.error,
        formatted=process_faculty.format_result(result),
    )

if tool_name == "run_command":
    result = process_faculty.run_command(
        args.get("command", ""),
        timeout=int(args.get("timeout", 30)),
    )
    return ToolResult(
        tool="run_command",
        query=args.get("command", ""),
        success=result.success,
        data={"returncode": result.returncode},
        error=result.error,
        formatted=process_faculty.format_result(result),
    )
```

### Task 4 - Add psutil to requirements.txt

Add to inanna/requirements.txt:
```
psutil>=5.9
```

psutil is the cross-platform process and system monitoring library.
It works on Windows, Linux (NixOS), and macOS.
If not installed, ProcessFaculty falls back to OS commands gracefully.

### Task 5 - Domain hints for process faculty

Add to governance_signals.json domain_hints:
```json
"process": [
  "process", "processes", "running", "memory usage",
  "cpu usage", "system info", "system health", "uptime",
  "kill process", "terminate", "what is using", "ram",
  "disk space", "how is the system", "performance"
]
```

### Task 6 - Update help_system.py

Add to HELP_COMMON:
```
  SYSTEM & PROCESSES
    "how is the system doing?"
    "what is using all my memory?"
    "show me python processes"
    "kill process 1234" (requires approval)
    "run echo hello" (requires approval)
```

Add topic "processes" to HELP_TOPICS with full guidance.

### Task 7 - Update identity.py

CURRENT_PHASE = "Cycle 7 - Phase 7.3 - The Process Faculty"

### Task 8 - Tests

Create inanna/tests/test_process_faculty.py:
  - ProcessFaculty instantiates
  - system_info() returns ProcessResult with success=True
  - system_info() returns SystemInfo with hostname
  - system_info() returns cpu_count > 0
  - system_info() format_result includes "system info"
  - list_processes() returns ProcessResult with success=True
  - list_processes() returns at least 1 record
  - list_processes() filter works (filter="python" returns fewer)
  - list_processes() format_result includes "PID"
  - kill_process() with invalid pid returns success=False
  - run_command("echo hello") returns success=True
  - run_command("echo hello") stdout contains "hello"
  - run_command with invalid command returns failure gracefully
  - format_result() for list shows process table header
  - format_result() for system shows CPU line
  - format_result() for error shows "proc > error"
  - _format_uptime(0) returns "0s"
  - _format_uptime(90) returns "1m 30s"
  - _format_uptime(3700) returns "1h 1m"
  - ProcessFaculty works without psutil (fallback)

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_commands.py: add list_processes, system_info,
  kill_process, run_command.

---

## Permitted file changes

inanna/identity.py                      <- MODIFY: update CURRENT_PHASE
inanna/main.py                          <- MODIFY: wire ProcessFaculty
inanna/requirements.txt                 <- MODIFY: add psutil
inanna/config/tools.json                <- MODIFY: add 4 process tools
inanna/config/governance_signals.json   <- MODIFY: add process hints
inanna/core/
  process_faculty.py                    <- NEW
  help_system.py                        <- MODIFY: add processes section
  state.py                              <- MODIFY: update phase
inanna/ui/
  server.py                             <- MODIFY: wire ProcessFaculty
inanna/tests/
  test_process_faculty.py               <- NEW
  test_identity.py                      <- MODIFY: update phase
  test_commands.py                      <- MODIFY: add process tools

---

## What You Are NOT Building

- No process suspension or pause (kill only)
- No process priority adjustment (nice/renice)
- No network connections per process (Phase 7.x)
- No process tree visualization
- No changes to index.html or console.html
- No voice integration (Phase 7.5)
- run_command does NOT allow sudo or root commands
  — if the command requires elevation, it will fail
  gracefully with Access Denied

---

## Definition of Done

- [ ] core/process_faculty.py with all 4 operations
- [ ] ProcessFaculty gracefully handles missing psutil
- [ ] 4 new tools in tools.json (13 total)
- [ ] process domain hints in governance_signals.json
- [ ] psutil in requirements.txt
- [ ] help_system.py updated with processes section
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle7-phase3-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE7_PHASE3_REPORT.md
Stop. Do not begin Phase 7.4 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-21*
*INANNA gains eyes into the running system.*
*She can see what breathes and what strains.*
*She can quiet what harms — with your word.*
*Observation is free. Action requires consent.*
*That is the law.*

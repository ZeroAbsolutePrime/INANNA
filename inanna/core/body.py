from __future__ import annotations

import importlib
import os
import platform
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class BodyReport:
    timestamp: str
    platform: str
    python_version: str
    cpu_count: int | None
    memory_total_mb: float | None
    memory_available_mb: float | None
    memory_used_pct: float | None
    disk_total_gb: float | None
    disk_free_gb: float | None
    disk_used_pct: float | None
    session_id: str
    session_uptime_seconds: float
    realm: str
    model_url: str
    model_name: str
    model_mode: str
    data_root: str
    memory_record_count: int
    pending_proposal_count: int
    routing_log_count: int


class BodyInspector:
    def inspect(
        self,
        session_id: str,
        session_started_at: str,
        realm: str,
        model_url: str,
        model_name: str,
        model_mode: str,
        data_root: Path,
        memory_record_count: int,
        pending_proposal_count: int,
        routing_log_count: int,
    ) -> BodyReport:
        now = datetime.now(timezone.utc)
        memory_total_mb, memory_available_mb, memory_used_pct = self._inspect_memory()
        disk_total_gb, disk_free_gb, disk_used_pct = self._inspect_disk(data_root)
        started_at = self._parse_started_at(session_started_at)
        uptime_seconds = max(0.0, (now - started_at).total_seconds())
        platform_name = f"{platform.system()} {platform.release()}".strip() or "Unknown"

        return BodyReport(
            timestamp=now.isoformat(),
            platform=platform_name,
            python_version=sys.version.split()[0],
            cpu_count=os.cpu_count(),
            memory_total_mb=memory_total_mb,
            memory_available_mb=memory_available_mb,
            memory_used_pct=memory_used_pct,
            disk_total_gb=disk_total_gb,
            disk_free_gb=disk_free_gb,
            disk_used_pct=disk_used_pct,
            session_id=session_id,
            session_uptime_seconds=uptime_seconds,
            realm=realm,
            model_url=model_url,
            model_name=model_name,
            model_mode=model_mode,
            data_root=str(data_root),
            memory_record_count=memory_record_count,
            pending_proposal_count=pending_proposal_count,
            routing_log_count=routing_log_count,
        )

    def format_report(self, report: BodyReport) -> str:
        lines = [
            f"Body Report - {report.timestamp}",
            "Machine:",
            f"  Platform: {report.platform}",
            f"  Python: {report.python_version}",
            f"  CPU count: {self._format_int(report.cpu_count)}",
            "Memory:",
            f"  Total MB: {self._format_float(report.memory_total_mb)}",
            f"  Available MB: {self._format_float(report.memory_available_mb)}",
            f"  Used %: {self._format_float(report.memory_used_pct)}",
            "Disk:",
            f"  Total GB: {self._format_float(report.disk_total_gb)}",
            f"  Free GB: {self._format_float(report.disk_free_gb)}",
            f"  Used %: {self._format_float(report.disk_used_pct)}",
            "Session:",
            f"  Session ID: {report.session_id}",
            f"  Uptime: {self._format_uptime(report.session_uptime_seconds)}",
            f"  Realm: {report.realm}",
            "Model:",
            f"  URL: {report.model_url or 'not set'}",
            f"  Name: {report.model_name or 'not set'}",
            f"  Mode: {report.model_mode}",
            "Data:",
            f"  Root: {report.data_root}",
            f"  Memory records: {report.memory_record_count}",
            f"  Pending proposals: {report.pending_proposal_count}",
            f"  Routing log entries: {report.routing_log_count}",
        ]
        return "\n".join(lines)

    def _format_uptime(self, seconds: float) -> str:
        total_seconds = max(0, int(seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    def _inspect_memory(self) -> tuple[float | None, float | None, float | None]:
        psutil_memory = self._inspect_memory_with_psutil()
        if psutil_memory != (None, None, None):
            return psutil_memory
        return self._inspect_memory_from_proc()

    def _inspect_memory_with_psutil(self) -> tuple[float | None, float | None, float | None]:
        try:
            psutil = importlib.import_module("psutil")
            virtual_memory = psutil.virtual_memory()
        except Exception:
            return (None, None, None)

        return (
            round(float(virtual_memory.total) / (1024 * 1024), 1),
            round(float(virtual_memory.available) / (1024 * 1024), 1),
            round(float(virtual_memory.percent), 1),
        )

    def _inspect_memory_from_proc(self) -> tuple[float | None, float | None, float | None]:
        meminfo_path = Path("/proc/meminfo")
        if not meminfo_path.exists():
            return (None, None, None)

        meminfo: dict[str, float] = {}
        for line in meminfo_path.read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            parts = raw_value.strip().split()
            if not parts:
                continue
            try:
                meminfo[key] = float(parts[0])
            except ValueError:
                continue

        total_kb = meminfo.get("MemTotal")
        available_kb = meminfo.get("MemAvailable")
        if total_kb is None or available_kb is None or total_kb <= 0:
            return (None, None, None)

        total_mb = round(total_kb / 1024, 1)
        available_mb = round(available_kb / 1024, 1)
        used_pct = round(((total_kb - available_kb) / total_kb) * 100, 1)
        return (total_mb, available_mb, used_pct)

    def _inspect_disk(self, data_root: Path) -> tuple[float | None, float | None, float | None]:
        try:
            usage = shutil.disk_usage(data_root)
        except OSError:
            return (None, None, None)

        total_gb = round(usage.total / (1024 * 1024 * 1024), 2)
        free_gb = round(usage.free / (1024 * 1024 * 1024), 2)
        if usage.total <= 0:
            used_pct = None
        else:
            used_pct = round(((usage.total - usage.free) / usage.total) * 100, 1)
        return (total_gb, free_gb, used_pct)

    def _parse_started_at(self, started_at: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(started_at)
        except ValueError:
            return datetime.now(timezone.utc)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _format_float(self, value: float | None) -> str:
        if value is None:
            return "unavailable"
        if value.is_integer():
            return str(int(value))
        return f"{value:.1f}"

    def _format_int(self, value: int | None) -> str:
        if value is None:
            return "unavailable"
        return str(value)

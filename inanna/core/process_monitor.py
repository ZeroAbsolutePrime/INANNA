from __future__ import annotations

import os
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProcessRecord:
    name: str
    pid: Optional[int]
    status: str
    uptime_seconds: int
    description: str
    endpoint: Optional[str] = None
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None


class ProcessMonitor:
    def __init__(self, server_start_time: float) -> None:
        self.server_start_time = server_start_time

    def inanna_record(self) -> ProcessRecord:
        http_port = os.getenv("INANNA_HTTP_PORT", "8080")
        ws_port = os.getenv("INANNA_WS_PORT", "8081")
        uptime = max(int(time.time() - self.server_start_time), 0)
        return ProcessRecord(
            name="INANNA NYX Server",
            pid=os.getpid(),
            status="running",
            uptime_seconds=uptime,
            description=f"HTTP :{http_port}  WebSocket :{ws_port}  Python {sys.version.split()[0]}",
            endpoint=f"http://localhost:{http_port}",
        )

    def lm_studio_record(self) -> ProcessRecord:
        endpoint = "http://localhost:1234"
        try:
            req = urllib.request.Request(
                f"{endpoint}/v1/models",
                headers={"User-Agent": "INANNA-monitor"},
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                status = "running" if response.status == 200 else "ready"
        except Exception:
            status = "offline"
        return ProcessRecord(
            name="LM Studio",
            pid=None,
            status=status,
            uptime_seconds=0,
            description="http://localhost:1234/v1  local inference",
            endpoint=endpoint,
        )

    def all_records(self) -> list[ProcessRecord]:
        records = [self.inanna_record(), self.lm_studio_record()]
        try:
            import psutil  # type: ignore

            process = psutil.Process(os.getpid())
            records[0].memory_mb = round(process.memory_info().rss / 1024 / 1024, 1)
            records[0].cpu_percent = round(process.cpu_percent(interval=0.1), 1)
        except ImportError:
            pass
        return records

    def format_uptime(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

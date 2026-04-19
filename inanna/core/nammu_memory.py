from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROUTING_LOG_FILE = "routing_log.jsonl"
GOVERNANCE_LOG_FILE = "governance_log.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _load_jsonl(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    if limit <= 0:
        return records
    return records[-limit:]


def append_routing_event(
    nammu_dir: Path,
    session_id: str,
    route: str,
    input_preview: str,
) -> None:
    _append_jsonl(
        nammu_dir / ROUTING_LOG_FILE,
        {
            "timestamp": utc_now(),
            "session_id": session_id,
            "route": route,
            "input_preview": input_preview,
        },
    )


def append_governance_event(
    nammu_dir: Path,
    session_id: str,
    decision: str,
    reason: str,
    input_preview: str,
) -> None:
    if decision == "allow":
        return
    _append_jsonl(
        nammu_dir / GOVERNANCE_LOG_FILE,
        {
            "timestamp": utc_now(),
            "session_id": session_id,
            "decision": decision,
            "reason": reason,
            "input_preview": input_preview,
        },
    )


def load_routing_history(nammu_dir: Path, limit: int = 20) -> list[dict[str, Any]]:
    return _load_jsonl(nammu_dir / ROUTING_LOG_FILE, limit)


def load_governance_history(nammu_dir: Path, limit: int = 20) -> list[dict[str, Any]]:
    return _load_jsonl(nammu_dir / GOVERNANCE_LOG_FILE, limit)

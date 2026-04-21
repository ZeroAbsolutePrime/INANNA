from __future__ import annotations

import json
import textwrap
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ReflectionEntry:
    entry_id: str
    observation: str
    context: str
    approved_at: str = ""
    approved_by: str = ""
    created_at: str = field(default_factory=utc_now)


class ReflectiveMemory:
    """
    INANNA's self-knowledge store.
    Proposal-governed. Nothing enters without Guardian approval.
    Stored as JSONL - one entry per line, append-only.
    """

    def __init__(self, self_dir: Path) -> None:
        self.self_dir = self_dir
        self.self_dir.mkdir(parents=True, exist_ok=True)
        self.reflection_path = self.self_dir / "reflection.jsonl"

    def propose(self, observation: str, context: str) -> ReflectionEntry:
        return ReflectionEntry(
            entry_id=f"reflect-{uuid.uuid4().hex[:8]}",
            observation=str(observation or "").strip(),
            context=str(context or "").strip(),
        )

    def approve(self, entry: ReflectionEntry, approved_by: str = "guardian") -> None:
        entry.approved_at = utc_now()
        entry.approved_by = str(approved_by or "guardian").strip() or "guardian"
        record = {
            "entry_id": entry.entry_id,
            "observation": entry.observation,
            "context": entry.context,
            "approved_at": entry.approved_at,
            "approved_by": entry.approved_by,
            "created_at": entry.created_at,
        }
        with self.reflection_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_all(self) -> list[ReflectionEntry]:
        if not self.reflection_path.exists():
            return []
        entries: list[ReflectionEntry] = []
        for line in self.reflection_path.read_text(encoding="utf-8").splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            try:
                payload = json.loads(cleaned)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            try:
                entries.append(ReflectionEntry(**payload))
            except TypeError:
                continue
        return entries

    def count(self) -> int:
        return len(self.load_all())

    def format_for_display(self) -> str:
        entries = self.load_all()
        if not entries:
            return "INANNA's self-knowledge is empty. No reflections have been approved yet."

        label = "entry" if len(entries) == 1 else "entries"
        lines = [f"INANNA's self-knowledge - {len(entries)} {label}:", ""]
        for index, entry in enumerate(entries):
            approved_date = entry.approved_at[:10] if entry.approved_at else "?"
            observation_lines = textwrap.wrap(entry.observation, width=55) or [entry.observation]
            context_lines = textwrap.wrap(entry.context, width=55) or [entry.context]
            lines.append(f"  [{approved_date}] {observation_lines[0]}")
            for continuation in observation_lines[1:]:
                lines.append(f"               {continuation}")
            if entry.context:
                lines.append(f"               context: {context_lines[0]}")
                for continuation in context_lines[1:]:
                    lines.append(f"                        {continuation}")
            if index != len(entries) - 1:
                lines.append("")
        return "\n".join(lines)

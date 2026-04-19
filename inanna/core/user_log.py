from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class UserLog:
    def __init__(self, logs_dir: Path) -> None:
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        response_preview: str,
    ) -> None:
        path = self._path_for(user_id)
        entry = {
            "timestamp": utc_now(),
            "session_id": session_id,
            "role": role,
            "content": content,
            "response_preview": response_preview[:200],
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def load(self, user_id: str, limit: int = 50) -> list[dict]:
        path = self._path_for(user_id)
        if not path.exists():
            return []
        entries = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return entries[-limit:]

    def entry_count(self, user_id: str) -> int:
        return len(self.load(user_id, limit=10_000_000))

    def clear(self, user_id: str) -> int:
        path = self._path_for(user_id)
        if not path.exists():
            return 0
        count = self.entry_count(user_id)
        path.unlink()
        return count

    def _path_for(self, user_id: str) -> Path:
        return self.logs_dir / f"{user_id}.jsonl"

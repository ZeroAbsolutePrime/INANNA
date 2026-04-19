from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_REALM = "default"


@dataclass
class RealmConfig:
    name: str
    purpose: str
    created_at: str
    governance_context: str = ""


class RealmManager:
    def __init__(self, data_root: Path) -> None:
        self.data_root = data_root
        self.realms_root = data_root / "realms"
        self.realms_root.mkdir(parents=True, exist_ok=True)

    def list_realms(self) -> list[str]:
        return sorted(
            [
                directory.name
                for directory in self.realms_root.iterdir()
                if directory.is_dir() and (directory / "realm.json").exists()
            ]
        )

    def realm_exists(self, name: str) -> bool:
        return (self.realms_root / name / "realm.json").exists()

    def create_realm(
        self,
        name: str,
        purpose: str = "",
        governance_context: str = "",
    ) -> RealmConfig:
        realm_dir = self.realms_root / name
        realm_dir.mkdir(parents=True, exist_ok=True)
        for subdirectory in ("sessions", "memory", "proposals", "nammu"):
            (realm_dir / subdirectory).mkdir(exist_ok=True)
        config = RealmConfig(
            name=name,
            purpose=purpose,
            created_at=datetime.now(timezone.utc).isoformat(),
            governance_context=governance_context,
        )
        (realm_dir / "realm.json").write_text(
            json.dumps(config.__dict__, indent=2),
            encoding="utf-8",
        )
        return config

    def load_realm(self, name: str) -> RealmConfig | None:
        path = self.realms_root / name / "realm.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return RealmConfig(**data)

    def realm_data_dirs(self, name: str) -> dict[str, Path]:
        base = self.realms_root / name
        return {
            "sessions": base / "sessions",
            "memory": base / "memory",
            "proposals": base / "proposals",
            "nammu": base / "nammu",
        }

    def ensure_default_realm(self) -> RealmConfig:
        if not self.realm_exists(DEFAULT_REALM):
            return self.create_realm(
                name=DEFAULT_REALM,
                purpose="The default operational context.",
                governance_context="Standard governance applies.",
            )
        loaded = self.load_realm(DEFAULT_REALM)
        if loaded is None:
            return self.create_realm(
                name=DEFAULT_REALM,
                purpose="The default operational context.",
                governance_context="Standard governance applies.",
            )
        return loaded

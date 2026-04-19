# CURRENT PHASE: Cycle 3 - Phase 1 - The Realm Boundary
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 3 - The Commander Room**
**Replaces: Cycle 2 - Phase 9 - The Multi-Faculty Proof (COMPLETE)**

---

## What Cycle 3 Is

Cycle 2 built the NAMMU Kernel: routing, governance, two Faculties,
bounded tool use, Guardian monitoring, and persistent NAMMU memory.

Cycle 3 builds the Commander Room: the constitutional observability
surface where the full system becomes visible and stewardable.

The Master Cycle Plan describes Cycle 3 as nine phases:
3.1 The Realm Boundary
3.2 The Realm Memory
3.3 The Body Report
3.4 The Proposal Dashboard
3.5 The Faculty Monitor
3.6 The Memory Map
3.7 The Guardian Room
3.8 The Audit Surface
3.9 The Commander Room

Phase 3.1 begins with the foundation: Realms.

---

## What This Phase Is

The system ontology defines a Realm as:
"A bounded operational domain with its own governance context,
memory scope, and embodied meaning. A realm is more than a folder
or namespace. It is a meaningful domain of life or operation."

Currently INANNA has one implicit realm: the default session.
Everything that happens — conversations, memories, proposals,
routing decisions — flows into one undifferentiated space.

Phase 3.1 makes Realms explicit. The user can name a realm,
switch between realms, and INANNA carries different memory and
context depending on which realm is active. Proposals, memory
records, and NAMMU history are scoped to their realm.

This is the first step toward the Commander Room: you cannot
observe a system that has no structure to observe.

---

## What a Realm Is in This Phase

A Realm in Phase 3.1 is:
- A named operational context with its own data directory
- Its own session files, memory files, and proposal files
- Its own NAMMU routing and governance log
- A governance context file that names the realm and its purpose
- Switchable at session start — not mid-session

A Realm is NOT in this phase:
- Not a separate model endpoint
- Not a separate Faculty configuration
- Not a separate user account
- Not a network-distributed context
- Not a security boundary — that is a later phase

---

## What You Are Building

### Task 1 - inanna/core/realm.py

Create a new file: inanna/core/realm.py

```python
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone


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
        return sorted([
            d.name for d in self.realms_root.iterdir()
            if d.is_dir() and (d / "realm.json").exists()
        ])

    def realm_exists(self, name: str) -> bool:
        return (self.realms_root / name / "realm.json").exists()

    def create_realm(self, name: str, purpose: str = "",
                     governance_context: str = "") -> RealmConfig:
        realm_dir = self.realms_root / name
        realm_dir.mkdir(parents=True, exist_ok=True)
        for sub in ("sessions", "memory", "proposals", "nammu"):
            (realm_dir / sub).mkdir(exist_ok=True)
        config = RealmConfig(
            name=name,
            purpose=purpose,
            created_at=datetime.now(timezone.utc).isoformat(),
            governance_context=governance_context,
        )
        (realm_dir / "realm.json").write_text(
            json.dumps(config.__dict__, indent=2), encoding="utf-8"
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
        return self.load_realm(DEFAULT_REALM)
```

### Task 2 - Realm-scoped data directories in main.py

Update main.py to:
1. Instantiate RealmManager at startup
2. Call ensure_default_realm() to create default realm if absent
3. Read active realm from env var INANNA_REALM (default: "default")
4. Use realm data directories for SESSION_DIR, MEMORY_DIR,
   PROPOSAL_DIR, and NAMMU_DIR instead of the flat data/ paths

The startup banner must show the active realm:
```
Phase: Cycle 3 - Phase 1 - The Realm Boundary
Realm: default
Session ID: ...
```

Add a "realms" command that lists available realms:
```
realms > Available realms (2):
  [default]  The default operational context.
  [work]     Work-related conversations and analysis.
  Active: default
```

### Task 3 - Realm-scoped data in server.py

Same as main.py — InterfaceServer uses realm data directories.
INANNA_REALM env var determines active realm at server startup.

Add "realms" command to the WebSocket protocol.
Broadcast realm info in the initial status payload:
```json
{"type": "status", "data": {"realm": "default", "realm_purpose": "...", ...}}
```

### Task 4 - Realm display in index.html

Add a realm indicator to the header bar, between the phase name
and the mode indicator:

```
INANNA NYX    [phase name]  [realm: default]  [mode dot] CONNECTED
```

CSS for realm indicator:
```css
.realm-indicator {
    color: #7a6a5a;  /* warm dim — earthy, grounded */
    font-size: 0.78rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}
```

The realm name updates when the status payload includes realm data.

### Task 5 - Migrate existing flat data to default realm

On first startup after Phase 3.1, if flat data directories
(inanna/data/sessions/, inanna/data/memory/, etc.) contain files
AND the default realm is empty, migrate those files into the
default realm automatically.

This preserves all existing session history, memory, and proposals.

Migration logic in main.py and server.py:
```python
def migrate_flat_data_to_default_realm(
    data_root: Path,
    realm_dirs: dict[str, Path],
) -> int:
    migrated = 0
    for key in ("sessions", "memory", "proposals"):
        flat_dir = data_root / key
        realm_dir = realm_dirs[key]
        if flat_dir.exists():
            for f in flat_dir.iterdir():
                if f.is_file():
                    dest = realm_dir / f.name
                    if not dest.exists():
                        f.rename(dest)
                        migrated += 1
    return migrated
```

If migration occurs, print:
```
Migrated N files to default realm.
```

### Task 6 - Update identity.py

Update CURRENT_PHASE:
```python
CURRENT_PHASE = "Cycle 3 - Phase 1 - The Realm Boundary"
```

Add to STARTUP_COMMANDS in main.py: "realms"
Add to capabilities line in state.py: "realms"

### Task 7 - Tests

Create inanna/tests/test_realm.py:
- RealmManager can be instantiated with a temp directory
- ensure_default_realm() creates default realm if absent
- create_realm() creates all required subdirectories
- list_realms() returns correct realm names
- realm_exists() returns True/False correctly
- load_realm() returns RealmConfig with correct fields
- realm_data_dirs() returns dict with all four keys

Update test_identity.py:
- Update CURRENT_PHASE assertion

Update test_state.py and test_commands.py:
- Add "realms" to capabilities assertions

---

## Permitted file changes

```
inanna/
  identity.py              <- MODIFY: update CURRENT_PHASE
  config/                  <- no changes
  main.py                  <- MODIFY: realm manager, realm dirs,
                                      realms command, migration
  core/
    session.py             <- no changes
    memory.py              <- no changes
    proposal.py            <- no changes
    state.py               <- MODIFY: add realms to capabilities
    nammu.py               <- no changes
    governance.py          <- no changes
    operator.py            <- no changes
    guardian.py            <- no changes
    nammu_memory.py        <- no changes
    realm.py               <- NEW: RealmManager, RealmConfig
  ui/
    server.py              <- MODIFY: realm manager, realm dirs,
                                      realm in status payload,
                                      realms command, migration
    static/
      index.html           <- MODIFY: add realm indicator to header
  tests/
    test_realm.py          <- NEW
    test_identity.py       <- MODIFY: update phase assertion
    test_state.py          <- MODIFY: add realms to capabilities
    test_commands.py       <- MODIFY: add realms to capabilities
    (all others)           <- no changes
  data/
    realms/                <- NEW directory (auto-created)
      default/             <- auto-created by ensure_default_realm()
```

---

## What You Are NOT Building in This Phase

- No mid-session realm switching — realm is set at startup
- No realm-specific Faculty configuration
- No realm security or access control
- No realm sharing or network distribution
- No realm deletion (that is a future phase with a consent flow)
- No change to core Faculty, governance, or NAMMU logic
- No new Faculty classes

---

## Definition of Done for Phase 3.1

- [ ] inanna/core/realm.py exists with RealmManager and RealmConfig
- [ ] All data directories are realm-scoped at startup
- [ ] INANNA_REALM env var selects active realm
- [ ] Default realm created automatically if absent
- [ ] Existing flat data migrated to default realm on first run
- [ ] Realm name shown in CLI banner and UI header
- [ ] "realms" command lists available realms
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] CURRENT_PHASE updated

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle3-phase1-complete
2. Write docs/implementation/CYCLE3_PHASE1_REPORT.md
3. Stop. Do not begin Phase 3.2 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*A realm is not a folder.*
*It is a domain of meaning.*
*Every conversation happens somewhere.*
*Phase 3.1 makes that somewhere named.*

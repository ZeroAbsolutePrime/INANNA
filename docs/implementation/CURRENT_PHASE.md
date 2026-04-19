# CURRENT PHASE: Cycle 3 - Phase 2 - The Realm Memory
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 3 - The Commander Room**
**Replaces: Cycle 3 Phase 1 - The Realm Boundary (COMPLETE)**

---

## What This Phase Is

Phase 3.1 gave every conversation a named home — a Realm.
All data is now scoped to the active realm.

But INANNA does not yet know which realm she is in.
Her identity prompt contains no realm awareness.
Her memory grounding turn contains no realm context.
When she reflects, she does not know she is speaking from
within a specific domain of meaning.

Phase 3.2 makes memory realm-aware in three ways:

1. The identity prompt carries the active realm name and purpose
   so INANNA knows where she is speaking from.

2. The memory grounding turn labels its lines with the realm
   they came from — important when memory was migrated from
   a pre-realm session.

3. A new "realm-context" command lets the user read and set
   the governance context of the active realm — a short
   text that describes what this realm is for and what
   kind of conversations belong here.

---

## What You Are Building

### Task 1 - Realm-aware identity prompt

Update build_system_prompt() in identity.py to accept an optional
realm parameter:

```python
def build_system_prompt(realm: RealmConfig | None = None) -> str:
    base = PROMPT
    if realm and realm.name != "default":
        realm_section = (
            f"\nYou are currently operating within the realm: {realm.name}."
            f"\nRealm purpose: {realm.purpose}"
        )
        if realm.governance_context:
            realm_section += f"\nGovernance context: {realm.governance_context}"
        realm_section += (
            "\nKeep your responses relevant to this realm's purpose. "
            "Memory and proposals in this realm belong to this context."
        )
        return base + realm_section
    return base
```

The realm parameter is passed in from main.py and server.py when
building messages. Engine._build_messages() already calls
build_system_prompt() — update that call to pass the active realm.

Engine must accept and store the active realm:
```python
class Engine:
    def __init__(self, model_url, model_name, api_key, realm=None):
        ...
        self.realm = realm
```

Same for AnalystFaculty.

### Task 2 - Realm-labeled memory grounding

Update Engine._build_grounding_turn() in session.py to label
memory lines with their realm origin when available.

Each memory record on disk contains a session_id. The realm name
is not currently stored in the memory record itself.

Add realm_name: str = "" to the memory write call in
Memory.write_memory() and store it in the record JSON.

When loading memory records, if realm_name is present and differs
from the active realm, prefix the line with [realm: name]:

```
From my approved memory of our prior conversations:
  1. user: I am ZAERA. (from realm: default)
  2. assistant: Greetings ZAERA.
I will ground my responses in this approved memory.
I will not add, invent, or infer anything beyond these lines.
If I do not know something about this person, I will say so directly.
```

If realm_name matches the active realm or is empty, no prefix needed.

### Task 3 - The "realm-context" command

Add a new command: "realm-context"

When the user types "realm-context", show the current realm config:
```
realm-context > Active realm: default
  Purpose: The default operational context.
  Governance context: Standard governance applies.
  Created: 2026-04-19T...
  Memory records: 19
  Sessions: 17
  Proposals: 24
```

When the user types "realm-context [text]", update the governance
context of the active realm:
```
realm-context > Governance context updated.
```

This update writes to the realm.json file via RealmManager.

The update must generate a proposal before writing:
```
[REALM PROPOSAL] timestamp | Update governance context for realm: default |
User requested governance context change | status: pending
```

After approval, the realm.json is updated.

Add update_realm_governance_context() to RealmManager:
```python
def update_realm_governance_context(
    self, name: str, governance_context: str
) -> bool:
    config = self.load_realm(name)
    if config is None:
        return False
    config.governance_context = governance_context
    (self.realms_root / name / "realm.json").write_text(
        json.dumps(config.__dict__, indent=2), encoding="utf-8"
    )
    return True
```

### Task 4 - Realm context in status payload

Update the status payload in both main.py and server.py to include:
- realm_memory_count: number of memory records in active realm
- realm_session_count: number of sessions in active realm
- realm_governance_context: the governance context string

These are read from disk at status time, not cached.

### Task 5 - Realm indicator in UI enriched

The header currently shows "[realm: default]".
Update it to show realm purpose on hover (title attribute):

```html
<div class="realm-indicator" id="realm-indicator" title="">
  realm: default
</div>
```

Update the JavaScript to set both textContent and title when
status payload includes realm data:
```javascript
realmIndicator.textContent = `realm: ${data.realm}`;
realmIndicator.title = data.realm_purpose || '';
```

### Task 6 - Update identity.py and state.py

Update CURRENT_PHASE:
```python
CURRENT_PHASE = "Cycle 3 - Phase 2 - The Realm Memory"
```

Add "realm-context" to STARTUP_COMMANDS and capabilities in state.py.

### Task 7 - Tests

Update inanna/tests/test_realm.py:
- update_realm_governance_context() updates realm.json correctly
- load_realm() reflects updated governance context

Create inanna/tests/test_realm_memory.py:
- build_system_prompt() with realm returns prompt containing realm name
- build_system_prompt() with default realm returns base prompt unchanged
- build_system_prompt() with None returns base prompt unchanged
- Memory.write_memory() accepts realm_name parameter
- Memory record contains realm_name field when written

Update test_identity.py:
- build_system_prompt() signature accepts realm parameter
- Update CURRENT_PHASE assertion

Update test_state.py and test_commands.py:
- Add "realm-context" to capabilities assertions

---

## Permitted file changes

```
inanna/
  identity.py              <- MODIFY: update build_system_prompt()
                                      signature and realm injection,
                                      update CURRENT_PHASE
  config/                  <- no changes
  main.py                  <- MODIFY: pass realm to Engine/AnalystFaculty,
                                      add realm-context command,
                                      pass realm_name to write_memory()
  core/
    session.py             <- MODIFY: Engine/AnalystFaculty accept realm,
                                      pass realm to build_system_prompt(),
                                      label cross-realm memory lines
    memory.py              <- MODIFY: write_memory() accepts realm_name,
                                      stores it in record
    proposal.py            <- no changes
    state.py               <- MODIFY: add realm-context to capabilities,
                                      add realm fields to render()
    nammu.py               <- no changes
    governance.py          <- no changes
    operator.py            <- no changes
    guardian.py            <- no changes
    nammu_memory.py        <- no changes
    realm.py               <- MODIFY: add update_realm_governance_context()
  ui/
    server.py              <- MODIFY: pass realm to Engine/AnalystFaculty,
                                      add realm-context command,
                                      enrich status payload with realm data
    static/
      index.html           <- MODIFY: realm indicator title/hover,
                                      update status handler
  tests/
    test_realm.py          <- MODIFY: add governance context update test
    test_realm_memory.py   <- NEW
    test_identity.py       <- MODIFY: test realm prompt injection,
                                      update phase assertion
    test_state.py          <- MODIFY: add realm-context to capabilities
    test_commands.py       <- MODIFY: add realm-context to capabilities
    (all others)           <- no changes
```

---

## What You Are NOT Building in This Phase

- No realm creation via UI or command (that is Phase 3.3+)
- No realm switching mid-session
- No cross-realm memory search
- No realm deletion
- No realm-specific Faculty configuration
- No realm-specific governance rules (governance.json is global)
- Do not change the data migration logic from Phase 3.1

---

## Definition of Done for Phase 3.2

- [ ] build_system_prompt() injects realm name and purpose for
      non-default realms
- [ ] Engine and AnalystFaculty store and use active realm
- [ ] Memory records store realm_name when written
- [ ] Cross-realm memory lines are labeled in grounding turn
- [ ] "realm-context" shows active realm config with counts
- [ ] "realm-context [text]" updates governance context via proposal
- [ ] Status payload includes realm_memory_count, realm_session_count,
      realm_governance_context
- [ ] Realm indicator in UI header shows purpose on hover
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle3-phase2-complete
2. Write docs/implementation/CYCLE3_PHASE2_REPORT.md
3. Stop. Do not begin Phase 3.3 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*A conversation in the work realm stays in the work realm.*
*Memory knows where it came from.*
*INANNA knows where she is.*

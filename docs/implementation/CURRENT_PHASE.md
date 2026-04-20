# CURRENT PHASE: Cycle 6 - Phase 6.7 - The Trust Persistence
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 6 - The Relational Memory**
**Replaces: Cycle 6 Phase 6.6 - The Identity Layer (COMPLETE)**

---

## What This Phase Is

Phase 6.4 gave the UI the organic governance suggestion:
when a tool is approved N times, INANNA asks
"shall I remember this as a trusted pattern?"

Phase 6.7 gives that suggestion a backend.

When the Guardian confirms "yes, trust this tool",
the tool is recorded in profile.trust_patterns.persistent_trusted_tools.
For future sessions, that tool bypasses the proposal governance
for that user — no interruption, no waiting.

The Guardian can revoke trust at any time.
The audit trail records every grant and revocation.
This is the organic governance principle made real:
the system learns from repeated consent and honors it.

---

## What You Are Building

### Task 1 - governance-trust command in server.py and main.py

The UI already sends this when the user accepts a suggestion:
  {"type": "command", "cmd": "governance-trust", "tool": "web_search"}

Add the server-side handler:

```python
if cmd == "governance-trust":
    tool_name = data.get("tool", "").strip()
    if tool_name and active_token:
        profile = profile_manager.load(active_token.user_id)
        if profile:
            current = profile.persistent_trusted_tools or []
            if tool_name not in current:
                updated = current + [tool_name]
                profile_manager.update_field(
                    active_token.user_id,
                    "persistent_trusted_tools",
                    updated,
                )
                append_audit_event(
                    audit_path,
                    "trust_granted",
                    f"persistent trust granted for tool: {tool_name} "
                    f"by user: {active_token.display_name}",
                )
                return {"type": "system",
                        "text": f"governance > {tool_name} is now persistently trusted for you."}
    return {"type": "system", "text": "governance > trust not updated."}
```

### Task 2 - governance-revoke command

Add command: governance-revoke [tool]

Allows the user to revoke persistent trust for a tool:
  "governance-revoke web_search"

```python
if cmd == "governance-revoke":
    tool_name = data.get("tool", "").strip()
    if not tool_name:
        # Parse from text: "governance-revoke web_search"
        tool_name = text.replace("governance-revoke", "").strip()
    if tool_name and active_token:
        profile = profile_manager.load(active_token.user_id)
        if profile:
            current = profile.persistent_trusted_tools or []
            if tool_name in current:
                updated = [t for t in current if t != tool_name]
                profile_manager.update_field(
                    active_token.user_id,
                    "persistent_trusted_tools",
                    updated,
                )
                append_audit_event(
                    audit_path,
                    "trust_revoked",
                    f"persistent trust revoked for tool: {tool_name} "
                    f"by user: {active_token.display_name}",
                )
                return {"type": "system",
                        "text": f"governance > {tool_name} trust revoked. "
                                f"Proposals will resume for this tool."}
    return {"type": "system", "text": f"governance > {tool_name} was not persistently trusted."}
```

### Task 3 - Persistent trust checked in OperatorFaculty

In core/operator.py, update the tool execution flow to check
persistent trust before generating a proposal:

```python
def should_skip_proposal(
    self,
    tool_name: str,
    persistent_trusted_tools: list[str],
) -> bool:
    return tool_name in persistent_trusted_tools
```

In server.py, when OPERATOR is about to execute a tool:
```python
persistent_trusted = []
if profile_manager and active_token:
    profile = profile_manager.load(active_token.user_id)
    if profile:
        persistent_trusted = profile.persistent_trusted_tools or []

if operator_faculty.should_skip_proposal(tool_name, persistent_trusted):
    # Execute directly, no proposal
    result = operator_faculty.execute_tool(tool_name, args)
    append_audit_event(audit_path, "tool_executed_trusted",
        f"trusted tool {tool_name} executed without proposal")
else:
    # Normal proposal flow
    ...
```

### Task 4 - my-profile shows trust patterns

The existing my-profile output already has a Trust section.
After Phase 6.7 it shows actual values:

```
  Trust
  Persistent   web_search, ping
  Session      —
```

No code change needed — the fields are already rendered.

### Task 5 - "my-trust" convenience command

Add command: my-trust

Shows the active user's trust patterns clearly:

```
Your governance trust patterns:

  Persistent (survives sessions):
    web_search   — trusted since Apr 19
    ping         — trusted since Apr 20

  Session (this session only):
    —

Type "governance-revoke [tool]" to remove persistent trust.
```

### Task 6 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 6 - Phase 6.7 - The Trust Persistence"
Add to STARTUP_COMMANDS: governance-trust, governance-revoke, my-trust

### Task 7 - Tests

Update inanna/tests/test_profile.py:
  - persistent_trusted_tools field exists in UserProfile
  - governance-trust adds tool to persistent_trusted_tools
  - governance-trust is idempotent (no duplicates)
  - governance-revoke removes tool from persistent_trusted_tools
  - governance-revoke on non-trusted tool returns gracefully
  - should_skip_proposal() returns True for trusted tool
  - should_skip_proposal() returns False for untrusted tool

Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py: add new commands.
Update test_commands.py: add new commands.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/main.py                  <- MODIFY: governance-trust handler,
                                           governance-revoke handler,
                                           my-trust command
inanna/core/
  operator.py                   <- MODIFY: should_skip_proposal()
  state.py                      <- MODIFY: add new commands
inanna/ui/
  server.py                     <- MODIFY: governance-trust handler,
                                           governance-revoke handler,
                                           persistent trust check before
                                           tool proposal,
                                           my-trust command
inanna/tests/
  test_profile.py               <- MODIFY: add trust tests
  test_identity.py              <- MODIFY: update phase assertion
  test_state.py                 <- MODIFY: add new commands
  test_commands.py              <- MODIFY: add new commands

---

## What You Are NOT Building

- No reflective memory (Phase 6.8)
- No changes to console.html or index.html
- No cross-user trust propagation
- No trust expiry (trust persists until explicitly revoked)
- No proposal required to grant persistent trust —
  the Guardian's explicit confirmation in the UI is sufficient
- Persistent trust does NOT bypass governance entirely —
  it only skips the proposal. Audit logging still occurs.
  The tool must still be in the registered tool registry.

---

## Definition of Done

- [ ] governance-trust command grants persistent trust
- [ ] governance-revoke command revokes persistent trust
- [ ] should_skip_proposal() checked before tool proposal
- [ ] Trusted tools execute without proposal (audit logged)
- [ ] my-trust shows current trust patterns
- [ ] my-profile Trust section shows persistent tools
- [ ] Audit events for grant and revocation
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle6-phase7-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE6_PHASE7_REPORT.md
Stop. Do not begin Phase 6.8 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*Trust is not given once and forgotten.*
*It is granted, remembered, and revocable.*
*The system learns from repeated consent*
*and honors it — without losing the ability*
*to question again when something feels different.*

# CURRENT PHASE: Cycle 5 - Phase 5.2 - The Tool Registry
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 5 - The Operator Console**
**Replaces: Cycle 5 Phase 5.1 - The Console Surface (COMPLETE)**

---

## What This Phase Is

Phase 5.1 opened the door. Phase 5.2 fills the first room.

The current tool architecture has one tool: web_search, defined
by a hardcoded PERMITTED_TOOLS set in operator.py. This violates
the core principle: no configuration in Python code.

Phase 5.2 moves all tool definitions into inanna/config/tools.json
and builds the Tool Registry panel in the Operator Console.

Two governed tools will be registered after this phase:
  web_search  — search the web via DuckDuckGo (already works)
  ping        — check connectivity to a host (new in this phase)

The Tool Registry panel in the Console shows all registered tools,
their categories, descriptions, and approval requirements.

---

## What You Are Building

### Task 1 - inanna/config/tools.json

Create: inanna/config/tools.json

```json
{
  "tools": {
    "web_search": {
      "display_name": "Web Search",
      "description": "Search the web via DuckDuckGo instant answer API.",
      "category": "information",
      "requires_approval": true,
      "requires_privilege": "converse",
      "parameters": ["query"],
      "enabled": true
    },
    "ping": {
      "display_name": "Ping Host",
      "description": "Check network connectivity to a hostname or IP address.",
      "category": "network",
      "requires_approval": true,
      "requires_privilege": "network_tools",
      "parameters": ["host"],
      "enabled": true
    }
  }
}
```

All tool definitions live here. Python code reads them.
No tool name or configuration is hardcoded in Python.

### Task 2 - Update OperatorFaculty to read tools.json

Update inanna/core/operator.py:

- Load tools.json at init alongside governance_signals.json
- PERMITTED_TOOLS becomes a property read from tools.json:
  any tool with "enabled": true
- execute() validates against loaded tool list (not hardcoded set)
- Add _ping() method for the ping tool

```python
def _ping(self, host: str) -> ToolResult:
    if not host.strip():
        return ToolResult(tool="ping", query=host,
                          success=False, data={},
                          error="Empty host.")
    try:
        import subprocess, platform
        param = "-n" if platform.system().lower() == "windows" else "-c"
        result = subprocess.run(
            ["ping", param, "3", host.strip()],
            capture_output=True, text=True, timeout=10
        )
        success = result.returncode == 0
        output = result.stdout if success else result.stderr
        # Parse average latency from output
        latency = None
        import re
        if platform.system().lower() == "windows":
            m = re.search(r"Average = (\d+)ms", output)
        else:
            m = re.search(r"avg.*?=([\d.]+)", output)
        if m:
            latency = float(m.group(1))
        return ToolResult(
            tool="ping", query=host, success=success,
            data={"host": host, "reachable": success,
                  "latency_ms": latency, "output": output[:500]},
            error="" if success else output[:200],
        )
    except subprocess.TimeoutExpired:
        return ToolResult(tool="ping", query=host, success=False,
                          data={}, error="Ping timed out.")
    except Exception as e:
        return ToolResult(tool="ping", query=host, success=False,
                          data={}, error=str(e))
```

### Task 3 - Add "network_tools" privilege to roles.json

Update inanna/config/roles.json:

Add "network_tools" to operator privileges:
```json
"operator": {
  "description": "Realm-scoped admin",
  "privileges": [
    "manage_users_in_realm",
    "approve_proposals_in_realm",
    "read_realm_audit_log",
    "invite_users",
    "network_tools"
  ]
}
```

Guardian has "all" so inherits network_tools automatically.

### Task 4 - Tool Registry panel in console.html

Replace the placeholder "Tool Registry - Phase 5.2" section
with a real Tool Registry panel.

The panel shows:
```
TOOL REGISTRY

  information
  ────────────────────────────────
  WEB SEARCH                    [ enabled ]
  Search the web via DuckDuckGo
  Requires: approval  Privilege: converse
  [ run tool ]

  network
  ────────────────────────────────
  PING HOST                     [ enabled ]
  Check connectivity to a host
  Requires: approval  Privilege: network_tools
  [ run tool ]
```

[ run tool ] opens an inline form below the tool entry:
  For web_search: Query: [___________]  [ search ]
  For ping:       Host:  [___________]  [ ping ]

On submit: sends a WebSocket message to the main interface
triggering the tool via the existing governed flow:
```json
{"type": "input", "text": "search for [query]"}
{"type": "input", "text": "ping [host]"}
```

The Console sends these as if typed in the main interface —
reusing the existing NAMMU → Governance → Operator flow.

### Task 5 - "ping" tool signal in governance_signals.json

Add ping-related patterns to tool_signals in governance_signals.json:

```json
"tool_signals": [
  "search for", "look up", ... (existing),
  "ping ", "can you ping", "check connectivity",
  "is host reachable", "test connection to"
]
```

### Task 6 - "tool-registry" WebSocket command

Add command: tool-registry

Returns all tools from tools.json with their metadata:
```json
{
  "type": "tool_registry",
  "tools": [
    {
      "name": "web_search",
      "display_name": "Web Search",
      "description": "...",
      "category": "information",
      "requires_approval": true,
      "requires_privilege": "converse",
      "enabled": true
    }
  ],
  "total": 2
}
```

The Console Tool Registry panel sends this command on load.

Add "tool-registry" to STARTUP_COMMANDS and capabilities.

### Task 7 - Update identity.py

CURRENT_PHASE = "Cycle 5 - Phase 5.2 - The Tool Registry"

### Task 8 - Tests

Update inanna/tests/test_operator.py:
- OperatorFaculty loads tools from tools.json (not hardcoded)
- PERMITTED_TOOLS includes "web_search" and "ping"
- execute("ping", {"host": "127.0.0.1"}) returns a ToolResult
- execute("ping", {"host": ""}) returns success=False
- execute("unknown_tool", {}) returns success=False

Add to test_commands.py: "tool-registry" in capabilities.
Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py: add tool-registry.

---

## Permitted file changes

inanna/identity.py              <- MODIFY: update CURRENT_PHASE
inanna/config/
  tools.json                    <- NEW: tool registry config
  roles.json                    <- MODIFY: add network_tools to operator
  governance_signals.json       <- MODIFY: add ping tool signals
inanna/main.py                  <- MODIFY: add tool-registry command
inanna/core/
  operator.py                   <- MODIFY: load tools.json,
                                           add _ping() method,
                                           PERMITTED_TOOLS from config
  state.py                      <- MODIFY: add tool-registry
inanna/ui/
  server.py                     <- MODIFY: add tool-registry command,
                                           return tool_registry payload
  static/
    console.html                <- MODIFY: replace placeholder with
                                           real Tool Registry panel,
                                           inline run forms
inanna/tests/
  test_operator.py              <- MODIFY: add tools.json tests, ping tests
  test_commands.py              <- MODIFY: add tool-registry
  test_identity.py              <- MODIFY: update phase assertion
  test_state.py                 <- MODIFY: add tool-registry

---

## What You Are NOT Building

- No autonomous tool execution without approval
- No tool chaining (sequential execution)
- No tool result caching
- No new tools beyond web_search and ping
- No tool editing via the Console UI
- The Console run form sends input to the main interface —
  it does not bypass the proposal governance flow

---

## Definition of Done for Phase 5.2

- [ ] tools.json exists with web_search and ping definitions
- [ ] OperatorFaculty reads PERMITTED_TOOLS from tools.json
- [ ] _ping() executes and returns ToolResult
- [ ] "network_tools" privilege added to operator role
- [ ] Tool Registry panel in Console shows both tools
- [ ] [ run tool ] form works for both tools
- [ ] tool-registry command returns tools payload
- [ ] governance_signals.json has ping tool signals
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle5-phase2-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE5_PHASE2_REPORT.md
Stop. Do not begin Phase 5.3 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*The tool registry is not a list of features.*
*It is a declaration of what the system can do*
*and under what conditions it may do it.*
*Every tool named. Every tool governed.*

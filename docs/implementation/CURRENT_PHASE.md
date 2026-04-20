# CURRENT PHASE: Cycle 5 - Phase 5.3 - The Network Eye
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 5 - The Operator Console**
**Replaces: Cycle 5 Phase 5.2 - The Tool Registry (COMPLETE)**

---

## What This Phase Is

Phase 5.2 registered tools and governed their invocation.
Phase 5.3 gives INANNA eyes on the network.

The Network Eye is the first surface in INANNA NYX that reaches
beyond the machine it runs on. Every action is proposal-governed.
Every result is audited. The Guardian sees everything.

Three governed capabilities are added in this phase:
  ping_host     — already exists in operator.py, now surfaced properly
  resolve_host  — resolve hostname to IP address
  scan_ports    — check a range of ports on a host

All three use Python standard library only. No nmap. No external deps.
All three require approval before execution.
All three append to the audit surface.

The Network panel in the Operator Console becomes functional.

---

## What You Are Building

### Task 1 - Add resolve_host and scan_ports to operator.py

Add two new tool implementations to OperatorFaculty:

```python
def _resolve_host(self, host: str) -> ToolResult:
    if not host.strip():
        return ToolResult(tool="resolve_host", query=host,
                          success=False, data={}, error="Empty host.")
    try:
        import socket
        ip = socket.gethostbyname(host.strip())
        hostname = socket.getfqdn(host.strip())
        return ToolResult(
            tool="resolve_host", query=host, success=True,
            data={"host": host, "ip": ip, "fqdn": hostname},
            error="",
        )
    except Exception as e:
        return ToolResult(tool="resolve_host", query=host,
                          success=False, data={}, error=str(e))

def _scan_ports(self, host: str, port_range: str = "1-1024") -> ToolResult:
    if not host.strip():
        return ToolResult(tool="scan_ports", query=host,
                          success=False, data={}, error="Empty host.")
    try:
        import socket, re
        m = re.match(r"(\d+)[-–](\d+)", port_range.strip())
        if m:
            start, end = int(m.group(1)), int(m.group(2))
        else:
            start = end = int(port_range.strip())
        # Cap range for safety
        end = min(end, start + 99)  # max 100 ports per scan
        open_ports = []
        for port in range(start, end + 1):
            try:
                with socket.create_connection((host.strip(), port), timeout=0.3):
                    open_ports.append(port)
            except Exception:
                pass
        return ToolResult(
            tool="scan_ports", query=f"{host}:{port_range}",
            success=True,
            data={"host": host, "port_range": port_range,
                  "open_ports": open_ports,
                  "scanned": end - start + 1},
            error="",
        )
    except Exception as e:
        return ToolResult(tool="scan_ports", query=host,
                          success=False, data={}, error=str(e))
```

### Task 2 - Register resolve_host and scan_ports in tools.json

Add to inanna/config/tools.json:

```json
"resolve_host": {
  "display_name": "Resolve Host",
  "description": "Resolve a hostname to its IP address and FQDN.",
  "category": "network",
  "requires_approval": true,
  "requires_privilege": "network_tools",
  "parameters": ["host"],
  "enabled": true
},
"scan_ports": {
  "display_name": "Port Scan",
  "description": "Scan open ports on a host (max 100 ports per scan).",
  "category": "network",
  "requires_approval": true,
  "requires_privilege": "network_tools",
  "parameters": ["host", "port_range"],
  "enabled": true
}
```

### Task 3 - Add tool signals to governance_signals.json

Add to tool_signals:
  "resolve ", "resolve host", "what is the ip",
  "scan ports", "port scan", "check ports on",
  "open ports", "what ports"

### Task 4 - Network Eye panel in console.html

Replace the placeholder content in the Network panel with
a functional Network Eye surface.

The panel has two sections:

**Discovery section** — quick action buttons:
  [ ping localhost ]  [ ping 8.8.8.8 ]
  [ resolve [input] ]  [ scan ports [host] [range] ]

**Results section** — a live host map:
When a ping, resolve, or scan result arrives via WebSocket
(operator message with tool result), parse and display it
as a host card:

```
HOST: 127.0.0.1
  name:    localhost
  status:  reachable
  latency: 0ms
  ports:   22, 80, 443  (from scan if done)
  last seen: 22:15
```

Host cards are added to the panel as results arrive.
Each card has buttons: [ ping ] [ resolve ] [ scan ports ]

The console.html listens for operator messages containing
tool results (JSON in the text or structured data) and
parses them to populate the host map.

**Inline forms for resolve and scan:**
  Resolve:   Host: [___________]  [ resolve ]
  Scan:      Host: [___________]  Range: [1-1024]  [ scan ]

These send inputs through the governed WebSocket flow.

### Task 5 - "network-status" WebSocket command

Add command: network-status

Returns a summary of recent network activity from the audit log:
```json
{
  "type": "network_status",
  "recent_scans": [
    {"tool": "ping", "host": "8.8.8.8", "result": "reachable", "ts": "..."},
    {"tool": "resolve_host", "host": "google.com", "result": "142.250.x.x", "ts": "..."}
  ],
  "total_scans": 5
}
```

Reads from the audit log, filters for tool_use events with
network tool names. Returns last 20.

Add "network-status" to STARTUP_COMMANDS and capabilities.

### Task 6 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 5 - Phase 5.3 - The Network Eye"

Add "network-status" to capabilities.

### Task 7 - Tests

Update inanna/tests/test_operator.py:
- resolve_host("localhost") returns success=True with ip field
- resolve_host("") returns success=False
- scan_ports("127.0.0.1", "80-80") returns success=True
- scan_ports("", "80-80") returns success=False
- scan_ports caps at 100 ports (start+99)
- PERMITTED_TOOLS includes resolve_host and scan_ports

Update test_commands.py: add network-status to capabilities.
Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py: add network-status.

---

## Permitted file changes

inanna/identity.py
inanna/main.py                  <- add network-status command
inanna/config/
  tools.json                    <- add resolve_host, scan_ports
  governance_signals.json       <- add network tool signals
inanna/core/
  operator.py                   <- add _resolve_host(), _scan_ports()
  state.py                      <- add network-status
inanna/ui/
  server.py                     <- add network-status command
  static/console.html           <- replace Network placeholder
                                   with functional Network Eye
inanna/tests/
  test_operator.py              <- add network tests
  test_commands.py              <- add network-status
  test_identity.py              <- update phase
  test_state.py                 <- add network-status

---

## What You Are NOT Building

- No automated network scanning (always proposal-governed)
- No topology visualization graph (future phase)
- No persistent host database (session-only in Phase 5.3)
- No service fingerprinting beyond port open/closed
- No ICMP raw sockets (use subprocess ping only)
- Do not modify index.html (main interface redesign is separate)

---

## Definition of Done

- [ ] resolve_host() and scan_ports() in operator.py
- [ ] resolve_host and scan_ports in tools.json
- [ ] Network Eye panel shows quick actions and host cards
- [ ] Inline forms for resolve and scan send governed input
- [ ] Host cards update from operator tool results
- [ ] network-status command returns audit-filtered results
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle5-phase3-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE5_PHASE3_REPORT.md
Stop. Do not begin Phase 5.4 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*The Network Eye sees what is connected.*
*Every host visible. Every port accountable.*
*Nothing scanned without consent.*

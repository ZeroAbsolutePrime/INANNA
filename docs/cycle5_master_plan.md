# Cycle 5 Master Plan — The Operator Console
**Status: PLANNED**
**Authorized by: INANNA NAMMU (Guardian) + Claude (Command Center)**
**Date written: 2026-04-20**
**Prerequisite: Cycle 4 complete — verify_cycle4.py passed 68 checks**

---

## What Cycle 5 Builds

Cycles 1-4 built the governed intelligence and its civic foundation.
INANNA can think, route, govern, remember, and know who it serves.

Cycle 5 builds the surface through which Guardians and Operators
manage, extend, and orchestrate the system. The Operator Console.

This is not a dashboard. It is a constitutional operations surface:
every action it exposes is governed, every tool it invokes is
proposal-approved, every Faculty it deploys has a charter.

The Architecture Horizon says the Operator Console contains:
- Network discovery and topology
- Running processes and service health
- Tool launcher with proposal governance
- Faculty Registry for domain-specialized models
- NAMMU routing to specialized Faculties
- Multi-Faculty orchestration

Cycle 5 makes this real in nine phases.

---

## The Nine Phases of Cycle 5

| Phase | Name | What it builds |
|---|---|---|
| 5.1 | The Console Surface | Second panel, Guardian/Operator only, header buttons |
| 5.2 | The Tool Registry | tools.json, governed tool invocation, tool catalog |
| 5.3 | The Network Eye | Network discovery, topology view, host enumeration |
| 5.4 | The Process Monitor | Running services, resource usage, log streaming |
| 5.5 | The Faculty Registry | faculties.json, domain Faculty definitions |
| 5.6 | The Faculty Router | NAMMU domain routing to registered Faculties |
| 5.7 | The Domain Faculty | First specialized Faculty — SENTINEL (security) |
| 5.8 | The Orchestration Layer | Multi-Faculty coordination via MCP patterns |
| 5.9 | The Operator Proof | Full integration test and Cycle 5 completion |

---

## Phase 5.1 — The Console Surface

A second, dedicated browser panel accessible only to
Guardian and Operator roles. Not a tab within the current
interface — a separate route: /console

The Console header mirrors the main interface header but
adds four buttons visible to Guardian (scoped for Operator):
  [ tools ]  [ network ]  [ faculties ]  [ processes ]

Each button shows its respective Console panel section.

The main interface gains a [ console ] button in the header
(already placeholder-declared in Phase 4.8) that opens /console.

The Console shares the same WebSocket connection as the main
interface. It reads from the same status payload.
No new server infrastructure — just a new HTML surface.

---

## Phase 5.2 — The Tool Registry

All tools live in: inanna/config/tools.json

Structure:
{
  "tools": {
    "web_search": {
      "display_name": "Web Search",
      "description": "Search the web via DuckDuckGo",
      "category": "information",
      "requires_approval": true,
      "faculty": "operator",
      "parameters": ["query"]
    },
    "ping": {
      "display_name": "Ping Host",
      "description": "Check connectivity to a host",
      "category": "network",
      "requires_approval": true,
      "faculty": "operator",
      "parameters": ["host"]
    },
    "port_scan": {
      "display_name": "Port Scan",
      "description": "Scan open ports on a host",
      "category": "network",
      "requires_approval": true,
      "requires_privilege": "network_tools",
      "faculty": "operator",
      "parameters": ["host", "port_range"]
    }
  }
}

The Tool Registry panel in the Console shows all registered tools,
their categories, and their approval requirements.

OperatorFaculty.execute() reads from tools.json.
No tool is hardcoded in Python.

Phase 5.2 adds ping as the second governed tool alongside web_search.

---

## Phase 5.3 — The Network Eye

Network discovery using only Python standard library.
No nmap. No external dependencies.

What it can do (all proposal-governed):
- ping_host(host) -> latency, reachability
- resolve_host(hostname) -> IP address
- scan_ports(host, ports) -> open/closed per port
- list_local_interfaces() -> local network interfaces

The Network Eye panel in the Console shows:
- A list of discovered hosts (from recent governed scans)
- Each host with last-seen, open ports, hostname
- [ scan ] button per host triggers a new scan proposal

All network actions append to the audit surface.
The Guardian can see every scan ever performed.

---

## Phase 5.4 — The Process Monitor

Process monitoring using Python standard library (os, subprocess).
Read-only by default.

What it shows:
- Running Python processes (INANNA itself, LM Studio)
- CPU and memory usage (via psutil if available, graceful fallback)
- Uptime for each tracked service
- Log tail for INANNA server output

The Process Monitor panel in the Console.
No process killing via the UI — that requires a CLI proposal.

---

## Phase 5.5 — The Faculty Registry

All domain Faculties live in: inanna/config/faculties.json

Structure:
{
  "faculties": {
    "crown": {
      "display_name": "CROWN",
      "domain": "general",
      "model_url": "",
      "model_name": "",
      "charter": "Primary conversational voice...",
      "governance_rules": [],
      "active": true,
      "built_in": true
    },
    "sentinel": {
      "display_name": "SENTINEL",
      "domain": "security",
      "model_url": "http://localhost:1234/v1",
      "model_name": "security-model",
      "charter": "You are the SENTINEL Faculty...",
      "governance_rules": [
        "All offensive actions require Guardian proposal",
        "Passive analysis only without explicit approval"
      ],
      "active": false,
      "built_in": false
    }
  }
}

The Faculty Registry panel shows all registered Faculties,
their domains, model endpoints, and active status.

FacultyMonitor reads from faculties.json.
NAMMU classification prompt is built from active Faculty domains.

---

## Phase 5.6 — The Faculty Router

NAMMU routing expands from binary (crown/analyst) to
domain-aware multi-Faculty routing.

The classification prompt becomes:
"Given this input, which Faculty should handle it?
Available Faculties: [list from active faculties.json entries]
Reply with exactly one Faculty name."

GovernanceLayer remains above the routing.
The Faculty router uses progressive discovery:
only active Faculties are loaded into the classification context.

IntentClassifier.route() returns a GovernanceResult with
faculty field set to any registered Faculty name.

---

## Phase 5.7 — The Domain Faculty

SENTINEL Faculty: the first domain-specialized Faculty.

Domain: cybersecurity, network analysis, threat assessment.
Charter: passive analysis only without explicit proposal approval.
Governance rules: offensive capability requires Guardian proposal.

SENTINEL is activated in faculties.json (active: true) and
gets its own routing test: inputs about security, vulnerabilities,
network threats route to SENTINEL automatically.

SENTINEL uses the same LM Studio endpoint as CROWN for Phase 5.7
(model differentiation comes in Phase 5.8+).

The Console Faculty Registry shows SENTINEL as active.
Its responses appear in the UI in a distinct color (muted red).

---

## Phase 5.8 — The Orchestration Layer

Multi-Faculty coordination using MCP agent-to-agent patterns.

When a complex task requires multiple Faculties:
1. NAMMU identifies the task needs orchestration
2. Creates an orchestration proposal
3. After approval, routes sequentially to required Faculties
4. Results from each Faculty are passed to the next
5. Final synthesis by CROWN
6. Full chain visible in the audit surface

Example: "Analyze the security of this codebase and explain it simply"
-> SENTINEL analyzes (security)
-> CROWN synthesizes for human readability
-> Chain is auditable end-to-end

The governed MCP principle applies:
discover -> propose -> approve -> call -> result -> audit

---

## Phase 5.9 — The Operator Proof

Integration verification: verify_cycle5.py with 40+ checks.
Cycle 5 Completion Record.
Code Doctrine: Lessons from Cycle 5.

---

## The Unchanging Rules for Cycle 5

All rules from master_cycle_plan.md apply without exception.
Additionally for Cycle 5:

- Tool definitions are NEVER hardcoded in Python.
  They live in tools.json. The code reads them.

- Faculty definitions are NEVER hardcoded in Python.
  They live in faculties.json. The code reads them.

- All network actions are proposal-governed.
  No scan, no ping, no port enumeration without approval.

- The Console surface is role-gated.
  Guardian sees everything. Operator sees their realm scope.
  User sees nothing.

- The governed MCP principle holds:
  discover -> propose -> approve -> call -> result -> audit
  No Faculty call, no tool call, no network scan executes
  without passing through the governance layer.

---

## Current Position

```
Stage 4  [COMPLETE]  Cycle 4 — The Civic Layer
Stage 4  [ACTIVE]    Cycle 5 — The Operator Console  ← here
Stage 5  [HORIZON]   Cycle 6 — The Embodied Network
                     Cycle 7 — INANNA NYXOS
```

We are here: beginning Cycle 5, Phase 5.1.

---

*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Date: 2026-04-20*
*The console is not a dashboard.*
*It is a constitutional operations surface.*
*Every action governed. Every tool registered.*
*Every Faculty chartered. Every scan auditable.*

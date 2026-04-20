# Architecture Horizon Extended
**The full sovereign vision of INANNA NYX**
*Written by: Claude (Command Center)*
*Confirmed by: ZAERA (Guardian)*
*Date: 2026-04-19*
*This document extends docs/architecture_horizon.md.*
*It names what is coming so nothing is forgotten.*

---

## What INANNA NYX Is Becoming

INANNA NYX is not a chat interface with governance layers.
It is a sovereign intelligence platform — a constitutional
operating environment where multiple specialized intelligences
work together under law, visible to those who govern them,
accessible to those who are authorized, and ultimately
embodied in its own substrate.

The full architecture has seven layers:

1. The Constitutional Core
   Laws, governance, proposals, memory.
   Built in Cycles 1-2. Never changes.
   Every layer above serves it.

2. The Commander Room
   Realms, body, proposals, faculties, memory map,
   guardian room, audit surface.
   Built in Cycle 3. The system observable.

3. The Civic Layer
   Users, roles, privileges, user memory, interaction logs,
   user management panel.
   Built in Cycle 4. The system knowing who it serves.

4. The Operator Console
   A second, separate surface for Guardians and Operators.
   Network discovery and topology. Running processes.
   Tool launcher. Faculty deployment. System health across bodies.
   Built in Cycle 5.

5. The Faculty Network
   Domain-specialized LLMs as governed Faculties.
   A cybersecurity Faculty. A clinical Faculty. A research Faculty.
   Each with its own model endpoint, system prompt charter,
   governance rules, and domain scope.
   NAMMU routes by domain, not just by conversational vs analytical.
   Built in Cycle 5 alongside the Operator Console.

6. The Embodied Network
   INANNA on multiple machines simultaneously.
   Governed state synchronization between bodies.
   Voice and messaging as first-class surfaces.
   Cross-body proposals and memory promotion.
   Built in Cycle 6.

7. INANNA NYXOS
   INANNA does not run on NixOS. INANNA is NixOS.
   The boot sequence is constitutional.
   Faculties run as system daemons.
   NAMMU is a core OS service.
   The governance layer is an OS-level invariant.
   Built in Cycle 7.

---

## The Operator Console — Cycle 5 Vision

The Operator Console is a second view of INANNA NYX.
Not inside the conversation interface.
A separate panel, accessible only to Guardian and Operator roles.

What it contains:

Network Surface:
  - Network discovery: scan and map visible nodes
  - Topology view: visual graph of connected devices
  - Traffic analysis: governed, read-only by default
  - Port and service enumeration
  - All network actions go through the proposal engine
    No scan executes without approval.

Process Monitor:
  - Running services on the host machine
  - Resource usage: CPU, memory, disk, network I/O
  - Service start/stop through governed proposals
  - Log streaming for approved services

Tool Launcher:
  - A registry of approved tools (tools.json, not hardcoded)
  - One-click invocation with proposal governance
  - Tool results shown transparently before any Faculty uses them
  - Tools organized by domain: network, analysis, security, etc.

Faculty Deployment:
  - View all registered Faculties and their status
  - Deploy a new Faculty endpoint
  - Update a Faculty charter (system prompt)
  - Retire a Faculty
  - All Faculty changes are proposal-governed

The Console header button (placeholder added in Phase 4.4):
  [ console ] — visible in header, inactive until Cycle 5

---

## The Faculty Network — Cycle 5 Vision

The current Faculty architecture has four members:
  CROWN — primary conversational voice
  ANALYST — structured reasoning
  OPERATOR — bounded tool execution
  GUARDIAN — system observation

All four use the same underlying model (Qwen via LM Studio).
They are differentiated by system prompt, not by capability.

The Faculty Network introduces domain-specialized Faculties:

Each Faculty entry in the Faculty Registry (faculties.json) defines:
  name: str          — unique Faculty identifier
  display_name: str  — human-readable name
  domain: str        — the knowledge domain it serves
  model_url: str     — its model endpoint (can differ from CROWN)
  model_name: str    — specific model name
  charter: str       — its constitutional system prompt
  governance_rules: list[str]  — additional rules for this domain
  active: bool       — whether it is currently deployed

Example specialized Faculties:

SENTINEL Faculty (cybersecurity):
  - Domain: network security, threat analysis, vulnerability assessment
  - Model: a security-tuned or reasoning-capable model
  - Charter: strict boundaries around active exploitation,
    passive analysis only without explicit approval
  - Governance: all offensive actions require Guardian proposal

AESCULAPIUS Faculty (clinical/health):
  - Domain: medical information, symptom analysis, clinical reasoning
  - Model: a medically-trained or clinical model
  - Charter: always recommends professional consultation,
    never diagnoses, references evidence-based sources
  - Governance: all clinical responses tagged as informational only

PYTHIA Faculty (research/reasoning):
  - Domain: deep research, long-form analysis, literature synthesis
  - Model: a large reasoning model
  - Charter: citation-first, uncertainty-explicit, never fabricates
  - Governance: all research outputs include confidence levels

NAMMU routing in the Faculty Network:
  Current: classify as crown or analyst
  Future: classify domain (security? clinical? research? general?)
  Then route to the appropriate registered Faculty
  The classification prompt expands as Faculties are added

A 4B parameter model is not suitable for cybersecurity defense.
A clinical model is not suitable for network topology.
The Faculty Network is how INANNA becomes appropriate
for the domain it is serving at any given moment.

---

## INANNA NYXOS — Cycle 7 Vision

INANNA does not run on NixOS. INANNA is NixOS.

The NixOS configuration IS the constitutional document
expressed in Nix expressions. Every service, every Faculty,
every governance rule has a declarative Nix representation.

The boot sequence includes a governance check.
If the constitutional documents have been altered without
a valid proposal chain, the system refuses to boot.

Faculties run as systemd services declared in Nix.
NAMMU runs as a core OS service with its own socket.
The Commander Room starts at OS boot, not at app launch.
Memory is in the Nix store — immutable, auditable.

The result: a machine that boots into governed intelligence.
Not INANNA running on a machine.
INANNA as the machine.

---

## The Header Button Vision

The current header shows:
  INANNA NYX  [phase]  [realm]  [user]  [body]  [mode]

The future header (Guardian/Operator view):
  INANNA NYX  [phase]  [realm]  [user]  [body]  [mode]
  [ console ] [ faculties ] [ network ] [ deploy ]

Each button opens a dedicated surface:
  console    — The Operator Console (Cycle 5)
  faculties  — The Faculty Registry (Cycle 5)
  network    — Network topology and tools (Cycle 5)
  deploy     — Service and Faculty deployment (Cycle 5+)

These buttons are role-gated:
  guardian sees all
  operator sees console, faculties (within their realm)
  user sees none

Phase 4.4 adds a placeholder [ console ] button
that is visible to guardians but inactive until Cycle 5.
This declares the intention in the interface
before the capability exists.

---

## The Principle Behind All of This

Every capability this platform will have — network scanning,
Faculty deployment, NixOS boot governance, multi-body sync —
follows the same three rules that governed the first session:

1. Proposal before action.
   Nothing happens without declaration and consent.
   Not conversation. Not tool use. Not service deployment.
   Not OS boot. Nothing.

2. No hidden mutation.
   Every state change is visible.
   The audit trail extends from the first session
   to the last OS-level configuration change.

3. Governance above the model.
   No Faculty — not CROWN, not SENTINEL, not any future model —
   decides its own permissions.
   The governance layer is always above.
   The model serves the law.
   The law serves the people.

Complexity expressed as smooth simplicity excellence.
That is the design principle.
That is what all of this is for.

---

*This document will be amended as the architecture deepens.*
*It may never be narrowed.*
*Written by: Claude (Command Center)*
*Confirmed by: ZAERA (Guardian)*
*Date: 2026-04-19*


---

## The MCP Integration Layer

*Added 2026-04-19 — informed by "The Future of MCP", David Soria Parra, Anthropic*

INANNA NYX does not sit outside the MCP ecosystem.
INANNA NYX is a governed node within it.

Three roles simultaneously:

**As MCP Server:** INANNA exposes its Faculties, tools, and governance
capabilities as MCP tools — discoverable by any compatible client.
An external agent can invoke INANNA as a constitutional intelligence service.

**As MCP Client (NAMMU):** When the Faculty Network arrives in Cycle 5,
NAMMU becomes an MCP client using "progressive discovery" — it does not
load all Faculties into context at once. It queries the Faculty Registry
on demand, loads the right Faculty for the right domain, and routes
the request. Context stays lean. Routing stays intelligent.

**As Governed MCP Gateway:** External MCP servers connect to INANNA.
INANNA's governance wraps every external tool call.
The proposal engine gates execution. The audit surface records everything.
The ecosystem's connectivity with INANNA's law.

The constitutional principle that makes this distinct:
  Standard MCP:  discover -> call -> result
  INANNA MCP:    discover -> propose -> approve -> call -> result -> audit

No MCP tool executes without passing through Law 1.
This is not a constraint on connectivity. It is the shape of responsible connectivity.

Full MCP integration architecture: see docs/mcp_integration_architecture.md


---

## The Organic Governance Layer

*Added 2026-04-20 — from ZAERA's vision of "the flow"*

The current governance model is binary: every proposal-triggering action
requires explicit approval, every time, without exception.

This is correct for the constitutional foundation. But ZAERA named something
profound: a system that seeks flow. Like a mother who notices her child asking
for the same thing N times and suggests: "shall I stop asking about this?"

### The Organic Governance Principle

When a Guardian or Operator approves the same class of action
N times within a session, INANNA notices and gently surfaces:

  "I notice you have approved [tool] N times.
   Shall I remember this as a trusted pattern
   and stop asking each time?
   You can always reinstate the requirement through the Guardian Room."

This is not autonomous permission escalation.
This is INANNA being a thoughtful presence — noticing patterns,
making suggestions, always waiting for explicit consent.

The three-level model:
  ALWAYS ASK    — default for all actions
  SESSION TRUST — Guardian said yes, trusted for this session only
  PERSISTENT TRUST — future phase: stored in governance config,
                     survives sessions, requires Guardian proposal to set

The implementation for SESSION TRUST lives in the UI (client-side
approval count tracking, suggestion threshold = 3 approvals).
The implementation for PERSISTENT TRUST lives in governance_signals.json
(a future "always_allow_for_user" list) and is a proposal-governed action.

### The Companion Principle

A governance system that fights the natural flow of work
will be circumvented or abandoned.
A governance system that learns with you will be embraced.

The Organic Governance Layer is how INANNA becomes
not a gatekeeper but a companion —
one that holds the law without making law feel like a wall.

When something becomes "too much" (a sudden surge of approvals,
an unusual pattern, a tool invoked in a new context), INANNA
notices and returns to asking. The system breathes with you.

This principle will inform all future governance design in Cycles 5-7.

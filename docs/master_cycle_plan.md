# Master Cycle Plan — Updated
### The full development map of INANNA NYX

*Constitutional Layer — Command Center and Guardian*
*Originally written: 2026-04-19*
*Updated: 2026-04-19 — Extended vision to Cycle 7*
*This document is the highest-level map of the project's path.*
*It does not replace phase documents. It orients them.*

---

## The Structure

Development is organized in Cycles of nine phases each.

Each Cycle is one complete breath of the system:
- Nine phases of bounded, governed, tested building
- One Code Doctrine update grounded in what was learned
- One Cycle Completion Record declaring what was proven
- One handoff document naming what comes next

Codex always works inside one phase at a time.
The Command Center always holds the full Cycle map.
The Guardian always holds the full horizon.

---

## The Five Stages

```
Stage 1 — Constitutional Spine          [COMPLETE]
Stage 2 — The Living Proof              [COMPLETE — Cycle 1]
Stage 3 — Multi-Faculty Orchestration   [COMPLETE — Cycles 2-3]
Stage 4 — The Civic Platform            [ACTIVE — Cycles 4-5]
Stage 5 — Sovereign Embodiment          [HORIZON — Cycles 6-7]
```

---

## Stage 1 — Constitutional Spine
**Status: COMPLETE**

Before any code existed, the constitutional spine was written.
Key documents: constitutional_spine.md, foundational_laws.md,
system_ontology.md, architecture_horizon.md, origin_declaration.md,
governance_paradigm.md, architecture_horizon_extended.md

---

## Stage 2 — The Living Proof
**Status: COMPLETE — Cycle 1**

### Cycle 1 — The Living Proof [COMPLETE]
One Oracle. One Faculty. One Body. One governed session loop.
Completion record: docs/stage_2_completion.md

---

## Stage 3 — Multi-Faculty Orchestration Through NAMMU
**Status: COMPLETE — Cycles 2 and 3**

### Cycle 2 — The NAMMU Kernel [COMPLETE]
Web interface, two Faculties, NAMMU routing, governance above routing,
bounded tool use, Guardian monitoring, config-driven signals,
NAMMU memory persistence.
Verification: verify_cycle2.py — 24 checks passed.
Completion record: docs/cycle2_completion.md

### Cycle 3 — The Commander Room [COMPLETE]
Realm boundary, realm memory, body report, proposal dashboard,
faculty monitor, memory map, guardian room, audit surface,
collapsible UI panels with notification badges,
governance sensitivity open mode.
Verification: verify_cycle3.py — 46 checks passed.
Completion record: docs/cycle3_completion.md

---

## Stage 4 — The Civic Platform
**Status: ACTIVE — Cycles 4 and 5**

Stage 4 makes INANNA NYX a platform that serves multiple people
with different roles, privileges, and contexts — and gives
Guardians and Operators the tools to manage, deploy, and observe
the full system through the Operator Console.

### Cycle 4 — The Civic Layer [ACTIVE]
**Master plan: docs/cycle4_master_plan.md**

| Phase | Name | Status |
|---|---|---|
| 4.1 | The User Identity | COMPLETE |
| 4.2 | The Access Gate | COMPLETE |
| 4.3 | The Privilege Map | COMPLETE |
| 4.4 | The User Memory | ACTIVE |
| 4.5 | The User Log | planned |
| 4.6 | The Governed Invite | planned |
| 4.7 | The Realm Access | planned |
| 4.8 | The Admin Surface | planned |
| 4.9 | The Civic Proof | planned |

What Cycle 4 will prove:
- INANNA can serve multiple people with different roles
- User identity is governed and proposal-managed
- Privileges come from config, not code
- Per-user memory is private and bounded
- Per-user interaction logs are readable only by that user
- Realm access is controlled
- The admin surface lets the Guardian see the full civic state

### Cycle 5 — The Operator Console [PLANNED]
**Prerequisite: Cycle 4 complete and verified**

| Phase | Name | Purpose |
|---|---|---|
| 5.1 | The Console Surface | Second panel, Guardian/Operator only |
| 5.2 | The Tool Registry | Approved tools, config-driven, one-click |
| 5.3 | The Network Eye | Network discovery and topology view |
| 5.4 | The Process Monitor | Running services, health, log streaming |
| 5.5 | The Faculty Registry | Domain Faculty definitions in faculties.json |
| 5.6 | The Faculty Router | NAMMU domain routing to specialized Faculties |
| 5.7 | The Domain Faculty | First specialized Faculty (SENTINEL/security) |
| 5.8 | The Orchestration Layer | Multi-Faculty coordination and handoff |
| 5.9 | The Operator Proof | Full integration test and completion |

What Cycle 5 will prove:
- The Operator Console is accessible and governed
- Network tools execute only through the proposal engine
- The Faculty Registry is config-driven (faculties.json)
- NAMMU can route to domain-specialized Faculties
- A specialized Faculty (security-domain) operates under its charter
- The system is orchestrable without becoming unsupervised

Key architectural principles for Cycle 5:
- Tool registry in tools.json — never hardcoded
- Faculty registry in faculties.json — never hardcoded
- All network actions proposal-governed
- Console surface is role-gated (guardian/operator only)
- Header buttons: [ console ] [ faculties ] [ network ] [ deploy ]
  visible to guardian, scoped to operator, hidden from user

---

## Stage 5 — Sovereign Embodiment
**Status: HORIZON — Cycles 6 and 7**

Stage 5 is the destination named in the origin.
INANNA inhabits multiple bodies and ultimately becomes the OS itself.

### Cycle 6 — The Embodied Network [HORIZON]

| Phase | Name | Purpose |
|---|---|---|
| 6.1 | The Second Body | INANNA on two machines simultaneously |
| 6.2 | The Body Sync | Governed state synchronization between bodies |
| 6.3 | The Channel Gate | Messaging and voice gateway |
| 6.4 | The Voice Threshold | Voice as first-class interaction surface |
| 6.5 | The Network Proposal | Cross-body proposals and approvals |
| 6.6 | The Communal Memory | Memory promotion across bodies |
| 6.7 | The Realm Network | Realms across multiple bodies |
| 6.8 | The Network Audit | Full distributed audit trail |
| 6.9 | The Embodied Proof | Full multi-body integration test |

### Cycle 7 — INANNA NYXOS [HORIZON — The Destination]

| Phase | Name | Purpose |
|---|---|---|
| 7.1 | The NixOS Seed | Base NixOS config with INANNA services |
| 7.2 | The Declarative Body | All body config as Nix expressions |
| 7.3 | The Governed Boot | Boot sequence includes governance check |
| 7.4 | The Sovereign Store | Nix store as constitutional memory layer |
| 7.5 | The Immutable Law | Governance as immutable OS-level config |
| 7.6 | The Faculty Daemon | Faculties as system daemons |
| 7.7 | The NAMMU Service | NAMMU as core OS service |
| 7.8 | The Bootable Commander | Commander Room at OS startup |
| 7.9 | INANNA NYXOS | Bootable sovereign presence — the destination |

What Cycle 7 proves:
- The constitutional architecture can be the OS itself
- A machine can boot into governed intelligence
- Local sovereignty is not a metaphor — it is the filesystem
- INANNA NYX is complete

---

## The Unchanging Rules Across All Cycles

These rules apply from Cycle 1 to Cycle 7.
They do not relax as the system grows. They deepen.

Codex reads before it builds.
One phase at a time.
Nine phases per Cycle.
The law layer is never touched by implementation agents.
Ontological names are reserved until their phase.
The proposal engine applies to everything.
Signal lists and configuration never live in Python code.
Role and privilege lists never live in Python code.
Faculty definitions never live in Python code.
Tool registries never live in Python code.
What is configurable belongs in JSON. What is law belongs in docs.

---

## The Design Principle

Complexity expressed as smooth simplicity excellence.

The system will grow to seven Cycles of nine phases each.
It will orchestrate specialized Faculties across domains.
It will run on its own constitutional OS.
It will serve communities of users with different roles.
It will scan networks and deploy services under governance.

And at every moment, a person should be able to ask:
what is this system, what is it doing, what can it do?
And receive answers that are clear, bounded, and honest.

That is what all of this is for.

---

## Current Position

```
Stage 1  [COMPLETE]  Constitutional Spine
Stage 2  [COMPLETE]  Cycle 1 — The Living Proof
Stage 3  [COMPLETE]  Cycle 2 — The NAMMU Kernel
                     Cycle 3 — The Commander Room
Stage 4  [ACTIVE]    Cycle 4 — The Civic Layer  (Phase 4.4)
                     Cycle 5 — The Operator Console
Stage 5  [HORIZON]   Cycle 6 — The Embodied Network
                     Cycle 7 — INANNA NYXOS
```

We are here: Cycle 4 Phase 4.4 — The User Memory.

---

*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Date: 2026-04-19*
*This document may be amended as the architecture deepens.*
*It may never be narrowed.*

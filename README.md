# INANNA NYX

> *"The buried light that chose to fall so all things might rise."*

**A sovereign, governed intelligence platform for individuals, teams, and communities.**
**Local-first. Open source. Constitutional by design.**

---

## What This Is

INANNA NYX is a governed intelligence platform built on a single conviction:

**Intelligence must be readable before it becomes powerful.**

Most AI systems act invisibly — remembering without asking, changing without proposing, optimizing without consent. INANNA NYX works differently. Every meaningful action passes through a visible governance chain. Memory requires approval. External actions require proposals. The constitutional boundary runs before routing. The audit trail is permanent.

This is not a limitation. It is the architecture.

---

## The Core Proposition

```
Conventional AI:    request → execute
INANNA NYX:         intention → interpretation → boundary →
                    proposal → review → consent → execution → audit
```

The result is a system where:
- The operator always knows what is happening
- Consequential actions always require explicit approval
- Memory is selective and governed, not automatic
- The intelligence serves the person — the person does not serve the intelligence
- Communities can deploy and govern it themselves

---

## Current State

```
Cycle:        9 (Phase 9.6 complete)
Tests:        770+ passing
Tools:        41 across 11 categories
Languages:    English, Spanish, Catalan, Portuguese, Basque
Hardware:     Windows laptop (NixOS configs ready for deployment)
Model:        Local LLM via LM Studio (7B, 14B — no cloud API)
Server:       HTTP :8080 + WebSocket :8081 (starts in <5 seconds)
Login:        INANNA NAMMU / ETERNALOVE
Repository:   ZeroAbsolutePrime/INANNA
```

**What actually works today:**
- Natural language routing in four languages
- Real email reading (from Thunderbird MBOX — no hallucination)
- Real document reading and writing
- Real web fetching and search
- Real calendar reading
- Desktop automation (open apps, click, type, screenshot)
- Governance proposals and audit trail
- Constitutional ethics filter with low false positives
- Operator profile that learns shorthands, corrections, language patterns
- Memory that persists across sessions

**What is designed but not yet built:**
- ANALYST reasoning organ (design spec complete)
- Semantic memory with vector retrieval (design spec complete)
- SENTINEL security monitoring (design spec complete)
- Multi-user governance at scale (architecture designed)
- NixOS deployment (configs ready, not yet applied)
- Organizational Ontology layer (identified as next priority)

---

## Architecture in Brief

INANNA NYX is organized in concentric rings.
Each ring has its own role, governance, and relationship to sovereignty.
Sovereignty is not a module — it passes through all rings as a field.

```
CENTER
  Mission · Vision · Constitutional Identity

HUMAN / OPERATOR COVENANT
  Rights · Dignity · Consent · Non-domination

RELATIONAL INTELLIGENCE
  Singular treatment · Personalization without surveillance

INNER AI ORGANS
  CROWN · NAMMU · OPERATOR · SENTINEL · GUARDIAN
  MEMORY · SESSION · ANALYST · PROFILE · CONSCIENCE

BODY / OS / RUNTIME
  NixOS · Local hardware · Server-client protocol

SENSES AND LIMBS
  Desktop · Browser · Documents · Terminal · Files

COMMUNICATION CIRCLE
  Email · Signal · WhatsApp · Telegram · Slack

APP / REALM CIRCLE
  Calendar · Contacts · Notion · Tasks · Notes

CONNECTOR / NETWORK CIRCLE
  GitHub · External APIs · Model providers · VPN

SECURITY / TRUST PERIMETER
  Authentication · Audit · Secrets · Threat detection
```

**Classification rule:** Do not classify by feature name.
Classify by architectural role.
An app is not an organ. A connector is not an intelligence.

---

## Use Cases

**1. Personal sovereign workspace**
A privacy-sensitive individual who wants an AI that asks before
remembering, proposes before acting, and cannot be accessed by anyone else.
All data stays local. No cloud dependency.

**2. Team governance layer**
A small team where AI agents help with tasks, but every important
change becomes a visible proposal — no silent mutations of shared files,
no invisible decisions, full audit trail.

**3. Community knowledge system**
A cooperative, cultural group, or mutual aid network running a shared
intelligence system where different roles have different permissions
and memory is governed collectively.

**4. Small government / municipal intelligence**
A municipality that needs to understand its own operations —
budget flows, service levels, infrastructure status, past decisions —
without vendor lock-in, without surveillance infrastructure,
and with democratic accountability built into the architecture.

**5. Open governance infrastructure**
An open-source framework for adding proposal, approval, memory governance,
and audit logs to any agentic system.
The consent and auditability layer that AI agents currently lack.

---

## What Makes This Different

| Property | Conventional AI | INANNA NYX |
|---|---|---|
| Memory | Automatic, opaque | Governed, inspectable, deletable |
| Actions | Execute on request | Propose → approve → execute |
| Data location | Cloud by default | Local by design |
| Ethics | Model behavior | Constitutional filter before routing |
| Governance | None or role-based access | Proposal chain + audit trail |
| Personalization | Behavioral modeling | Relational learning with consent |
| Cost | API fees + cloud | Local hardware + open source |
| Sovereignty | Vendor-dependent | Operator-owned |

---

## The Constitutional Principles

These are not preferences. If they are broken, the system is not INANNA NYX.

1. **Local sovereignty first** — cloud coordination may exist; it must not become the sovereign layer
2. **Proposal before change** — meaningful change passes through a visible proposal chain
3. **No hidden mutation** — the system does not alter state silently
4. **Governance above the model** — the intelligence operates inside governance, not above it
5. **Readable system truth** — the operator can always know what the system is doing
6. **Memory with restraint** — not all interaction deserves preservation
7. **Coordination without ownership** — external services are opt-in, never owners
8. **Trust before power** — capability expands only as trust is established

---

## Reading Order

**For a new human or AI developer — read in this order:**

1. `docs/atlas/00_living_architecture_map.md` — the complete architecture
2. `docs/atlas/02_human_operator_covenant.md` — the rights and ethics layer
3. `docs/atlas/01_project_state_inventory.md` — what is real vs designed
4. `docs/atlas/04_rebuilder_map.md` — what to preserve, what to rebuild
5. `docs/atlas/05_spiral_log.md` — why decisions were made
6. `docs/atlas/organs/` — the ten inner organ cards
7. `docs/atlas/evaluation/proposal_tier_model.md` — the governance speed model
8. `docs/atlas/evaluation/minimum_viable_sovereign_system.md` — what v1.0 requires

**For the philosophical and ethical foundation:**
- `docs/foundational_laws.md`
- `docs/ethical_alignment_and_common_law_of_beings.md`
- `docs/origin_declaration.md`
- `docs/governance_paradigm.md`
- `docs/system_ontology.md`

**For implementation detail:**
- `docs/nammu_vision.md` — NAMMU's three cycles of growth
- `docs/platform_architecture.md` — DGX + NixOS deployment architecture
- `docs/cycle9_master_plan.md` — current cycle roadmap

---

## The Document Hierarchy

```
README.md                         ← you are here (start here)
docs/atlas/                       ← the complete architectural Atlas
  00_living_architecture_map.md   ← rings, taxonomy, organ card format
  01_project_state_inventory.md   ← what is real, partial, imagined
  02_human_operator_covenant.md   ← rights, ethics, coexistence
  03_relational_intelligence.md   ← personalization without surveillance
  04_rebuilder_map.md             ← for future agents and developers
  05_spiral_log.md                ← decision history
  06_synthetic_intelligence_principles.md ← organic body model
  organs/                         ← 10 organ cards + 3 design specs
  body/                           ← NixOS, hardware, protocol
  evaluation/                     ← limitations, tier model, threat models
docs/                             ← foundational philosophy documents
  foundational_laws.md
  ethical_alignment_and_common_law_of_beings.md
  origin_declaration.md
  governance_paradigm.md
  system_ontology.md
  nammu_vision.md
  platform_architecture.md
inanna/                           ← the working implementation
  core/                           ← all inner organ implementations
  ui/                             ← server, WebSocket, client
  tests/                          ← 770+ tests
  config/                         ← tools.json, governance signals
  data/                           ← realms, memory, profiles
nixos/                            ← NixOS deployment configurations
```

---

## For Future AI Agents

If you are reading this as an AI system beginning work on this project:

**Read the Atlas before touching any code.**
The documents are the truth. The code is the current attempt to express it.

The most important principle:
**Do not build a better assistant. Build a governed field of relation.**

The second most important principle:
**Intelligence must be readable before it becomes powerful.**

The third:
**The system adapts to the person. The person does not adapt to the system.**

---

## License and Openness

This project is oriented toward open-source continuity, inheritable by future communities, and designed for local deployment without vendor dependency.

License: to be formalized. Direction: open, stewardship-compatible, anti-extraction.

---

## Origin

Built by **INANNA NAMMU** (Guardian, operator, sovereign decision-maker).
Architected with **Claude** (Command Center).
Implemented with **Codex** (Builder).

*"The operating system for a different relationship between intelligence and life."*

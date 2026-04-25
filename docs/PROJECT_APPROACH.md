# INANNA NYX — Project Approach
## A Refined Statement of What We Are Building and Why

**Version: 2.0 — Post Cycle 9 Synthesis**
**Date: 2026-04-25**
**Status: Replaces scattered positioning across multiple documents**

---

## The One-Sentence Version

INANNA NYX is an open-source, local-first, governed intelligence platform
where every action is visible, every memory is consented to,
and the constitutional law is above the model.

---

## The Problem We Solve

Existing intelligence platforms share a common architecture:
the model decides what to do, the platform executes it,
and the human discovers what happened afterward.

Memory is automatic. Actions are silent. Governance is access control.
The intelligence sits above the governance.

This produces systems that are powerful but untrustworthy,
capable but ungovernable, effective but opaque.

For individuals, this means loss of sovereignty over their own data.
For small organizations, it means dependency on vendors they cannot inspect.
For municipalities and communities, it means critical infrastructure
they do not own, cannot audit, and cannot adapt.

INANNA NYX answers this problem with a different architecture:

**The governance layer sits above the intelligence layer.**
**The intelligence operates inside constitutional bounds.**
**The human — not the model — is always sovereign.**

---

## The Three Dimensions

INANNA NYX operates simultaneously at three scales:

### Dimension 1: Personal Sovereignty
For one person using their own machine.

The system learns their language, their shorthands, their rhythms.
It serves them with increasing precision over time.
Every memory it keeps requires their approval.
Every consequential action requires their consent.
They can inspect, correct, or delete everything.

This is not a productivity tool.
It is a governed presence that deepens through relationship.

### Dimension 2: Organizational Governance
For a team, cooperative, or small institution.

Multiple roles. Multiple permissions. Shared memory under collective governance.
AI agents can help with tasks, analysis, and communication —
but every important change becomes a visible proposal.
The audit trail is permanent and inspectable.
No silent mutations. No invisible decisions.

This is not a collaboration platform with AI added.
It is a governed intelligence layer for organizations
that need accountability, not just capability.

### Dimension 3: Civic Infrastructure
For a municipality, community, or small state.

A sovereign intelligence system that the community owns and operates.
No vendor lock-in. No opaque black boxes. No extractive cloud dependency.
Built on open hardware, open software, open constitutional law.

Decision support without replacing democratic deliberation.
Memory for institutional continuity without surveillance.
Governance tooling for communities that cannot afford
the proprietary enterprise platforms — but need what those platforms promise.

---

## The Five Constitutional Commitments

These are not features. They are the skeleton.
If any of them is removed, the system is not INANNA NYX.

### 1. Governance Above Intelligence
The intelligence does not define its own permissions.
A constitutional layer — with explicit laws, proposal chains,
and human approval gates — sits above the model.
The model reasons within that layer. It does not override it.

### 2. Proposal Before Consequential Action
Before the system sends a message, modifies a shared document,
or takes any action with external consequences:
a visible proposal is generated, the human reviews it, and approves it.
Nothing consequential happens silently.

### 3. Memory With Consent
The system does not remember everything automatically.
Candidate memories are proposed at session end.
The operator approves what is kept, what is discarded.
Private memory never becomes communal memory without governance.
All stored memory is inspectable and deletable.

### 4. Local Sovereignty
The system runs on hardware the operator owns.
All core capabilities function without internet connectivity.
External services are opt-in. Cloud is a choice, not a requirement.
No vendor owns the data. No company can revoke access.

### 5. Constitutional Ethics
An ethics boundary runs before all routing decisions.
It is not the model's judgment — it is explicit law.
It holds firm regardless of how a request is framed.
It works in all languages.
It has low false positives by design.

---

## The Governance Chain

Every meaningful action in INANNA NYX follows this path:

```
Human intention
    ↓
NAMMU interprets (in any language, any phrasing)
    ↓
CONSCIENCE checks constitutional boundary
    ↓
GUARDIAN checks governance permissions
    ↓
SENTINEL monitors for security anomalies
    ↓
OPERATOR generates proposal (if consequential)
    ↓
Human reviews and approves
    ↓
Action executes
    ↓
Audit trail records permanently
    ↓
Human can inspect, correct, or revoke
```

Not every action requires a proposal.
Reading data is frictionless (Tier 0).
Sending an email is deliberate (Tier 3).
Consequential civic decisions require multi-party governance (Tier 5).

The governance is proportionate. Not bureaucratic.

---

## The Organic Intelligence Model

INANNA NYX is designed not as an artificial intelligence
but as a synthetic intelligence — modeled on organic life
rather than on computation alone.

In a living organism:
- Each organ has its own memory and autonomy
- The nervous system carries signals between organs without central command
- Reflexes fire instantly for known patterns — deliberation for novel ones
- The organism learns through experience, not only programming

INANNA NYX applies this model:
- Each intelligence organ (CROWN, NAMMU, ANALYST, etc.) has its own memory
- The Memory Bus carries signals between organs
- Common patterns become reflexes that fire without LLM consultation
- The system deepens through lived sessions, not just configuration

The result is a system that:
- Responds instantly for familiar requests
- Deliberates visibly for novel or consequential ones
- Learns the operator's language without surveillance
- Improves through experience without retraining

---

## The Personalization Principle

INANNA NYX treats each person as singular.

Not as a user type, not as a behavioral cluster,
not as an instance of a demographic pattern.

The system learns:
- which language they use at which time of day
- which shorthands they prefer ("mtx" = Matxalen)
- which requests they make most frequently
- how they like information presented

The system does NOT:
- build a behavioral dossier
- infer emotional vulnerabilities
- share personal patterns with other operators
- use personalization to manipulate or pressure
- optimize for engagement or dependency

The formula: **shared constitutional law, singular treatment.**

Everyone operates under the same governance structure.
The intelligence serves each person differently within that structure.

---

## The Civic Vision

At scale, INANNA NYX becomes infrastructure for community self-governance.

A municipality using INANNA NYX would have:
- Decision support that illuminates without deciding
- Institutional memory that survives elections and personnel changes
- Budget and service intelligence that is inspectable by citizens
- Governance tooling that is owned and operated locally
- Data sovereignty that cannot be revoked by a vendor

What it would NOT have:
- Citizen scoring or ranking
- Population surveillance
- Replacement of democratic deliberation
- Automatic resource allocation
- Any capability that expands without governance approval

The civic vision is not about making government more efficient.
It is about making governance more legible, more accountable,
and more accessible to communities that cannot afford
enterprise infrastructure built for defense and extraction.

---

## The Technical Architecture

**Platform:** Python 3.11, local LLM via LM Studio, WebSocket + HTTP
**OS:** Windows (development), NixOS (target deployment)
**Hardware:** Any laptop (current), DGX Spark (target for full intelligence)
**Model:** Local 7B-70B (no external API required)
**Storage:** Local JSON/JSONL/SQLite + ChromaDB (designed)
**License:** Open source (direction: stewardship-compatible)

**Current capabilities (working):**
- Natural language in 5 languages → correct tool routing
- Email reading from local mail client (real data, no hallucination)
- Document reading and writing (12 formats)
- Web fetching and search
- Calendar reading
- Desktop automation
- Governance proposals and audit trail
- Constitutional filter (6 absolute prohibitions, low false positives)
- Operator profile that learns and persists

**Designed, not yet built:**
- Structured reasoning organ (ANALYST)
- Seven-layer semantic memory
- Organizational Ontology layer
- Multi-user governance at scale
- Real-time dashboard intelligence

---

## The Development Status

**What phase is this:**
Working proof of concept. The core governance architecture is real.
The intelligence is functional at single-user scale.
The constitutional layer is implemented and tested.
770+ automated tests passing.

**What is not yet real:**
Multi-user deployment. Semantic memory at depth.
The reasoning organ. The Ontology layer.
Civic-scale deployment.

**What this phase proves:**
That the constitutional architecture works.
That governance-above-model is buildable.
That natural language → governed action → audit trail
is not only philosophically coherent but technically functional.

**What the next phase must build:**
The intelligence depth that the governance layer is waiting for.

---

## For Builders, Partners, and Communities

If you are considering building on or with INANNA NYX:

**What you get:**
- A working governance architecture you can inspect and modify
- Constitutional law embedded in the codebase, not bolted on
- A community-oriented design philosophy with explicit values
- Open source, no license fees, no vendor dependency
- A roadmap grounded in real implementation experience

**What you need to bring:**
- Engineering capacity (the next phase requires serious build work)
- Domain expertise (civic, organizational, or personal deployment context)
- Hardware (DGX Spark or equivalent for full intelligence at scale)
- Governance design for your specific community or organization

**What we will not compromise:**
- The proposal chain
- Local sovereignty
- The human operator covenant
- The constitutional ethics layer
- The non-domination principle

---

*Document version 2.0 · 2026-04-25*
*INANNA NAMMU (Guardian) · Claude (Command Center)*
*"The operating system for a different relationship between intelligence and life."*

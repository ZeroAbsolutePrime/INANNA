# INNER ORGAN · GUARDIAN
## The Governor — Governance, Permissions, Audit, and Proposals

**Ring: Inner AI Organs**
**Grade: B+ (well implemented, single-user tested)**
**Version: 1.0 · Date: 2026-04-24**

---

## Identity

**What it is:**
GUARDIAN is the governance organ of INANNA NYX.
It enforces the rules of the governed field of relation —
bounding what OPERATOR may do, requiring proposals for
consequential actions, and maintaining the audit trail.

**What it does:**
- Checks every routing decision against governance signals
- Determines whether an action requires a proposal
- Generates and tracks proposals until operator approval
- Writes to the audit trail (governance_log.jsonl)
- Manages user roles (guardian, operator, user)
- Enforces the governance chain

**What it must never do:**
- Allow consequential actions without proposal
- Delete or alter the audit trail
- Grant permissions beyond the operator's role
- Execute actions — GUARDIAN governs, OPERATOR executes

**The name:**
GUARDIAN is the keeper of the covenant between human and machine.
It holds the law in place while the system acts.

---

## Ring

**Inner AI Organs** — GUARDIAN is between intelligence and execution.
Every action passes through GUARDIAN before OPERATOR receives it.

---

## Correspondences

| Component | Location |
|---|---|
| Main class | `core/guardian.py` → `GuardianFaculty` |
| Governance checks | `core/governance.py` → `GovernanceLayer` |
| Governance result | `core/governance.py` → `GovernanceResult` |
| Proposal system | `core/proposal.py` |
| Role management | `core/auth.py` → roles (guardian/operator/user) |
| Audit trail | `data/realms/default/nammu/governance_log.jsonl` |
| Tool permission config | `config/tools.json` → `requires_approval` field |

**Called by:** `ui/server.py` and `main.py` dispatch
**Calls:** `core/proposal.py`, audit logging
**Reads:** `config/tools.json`, user role from auth
**Writes:** `governance_log.jsonl`, proposal records

---

## Mission

GUARDIAN exists because intelligence without governance is dangerous.

An AI that can read email, open files, send messages, and run commands
must be bounded by explicit rules about what requires human approval.

The proposal layer is GUARDIAN's primary instrument:
- `requires_approval: true` in tools.json → GUARDIAN generates a proposal
- Operator sees the proposal: "Use email_compose to send X to Y"
- Operator approves → OPERATOR executes
- If operator does not approve → nothing happens

Without GUARDIAN, OPERATOR would execute freely.
The proposal layer would not exist.
The governed field of relation would collapse.

---

## Current State

### What Works

**GovernanceLayer:**
- Signal-based routing classification (memory/identity/sensitive/tool/allow)
- LLM classification for ambiguous cases (when model responds)
- Fallback signal check when LLM unavailable

**Proposal system:**
- Proposals generated for all `requires_approval: true` tools
- Proposals displayed in UI with approve/reject
- Audit trail records every proposal and its outcome

**Role system:**
- guardian: full access
- operator: tool access, no user management
- user: conversation only (future)

**Audit trail:**
- governance_log.jsonl records all decisions
- constitutional_log.jsonl records ethics blocks
- routing_log.jsonl records NAMMU routing decisions

### What Is Missing

- Automated governance policies (time-based, context-based)
- Multi-user governance (proposals visible to multiple guardians)
- Governance analytics (audit trail reporting)
- Role-based tool restriction (operator cannot use admin tools)

---

## Desired Function

In a civic deployment:
- Department heads see proposals from their team's actions
- Guardian reviews proposals asynchronously
- Time-sensitive proposals have escalation paths
- Governance analytics show patterns over time
- Role-based permissions restrict tool access by community role

---

## Evaluation

**Grade: B+**

The governance chain is correctly implemented and tested.
Proposals work. The audit trail works. Roles exist.

Single most important gap:
**GUARDIAN has only been tested with one user.**

Multi-user governance — where different operators have
different permissions and proposals require different approvers —
has never been tested in production.

Priority: deploy with a second test user and verify
that role separation works as designed.

---

*Organ Card version 1.0 · 2026-04-24*

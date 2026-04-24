# Cycle 4 Master Plan — The Civic Layer
**Status: ACTIVE**
**Authorized by: INANNA NAMMU (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Prerequisite: Stage 3 complete — Cycles 2 and 3 verified**

---

## Why This Cycle Exists

Cycles 1, 2, and 3 built INANNA for one person: the Guardian.
One operator. One machine. One sovereign session.

But the Architecture Horizon says:
"A realm is a bounded operational domain... a meaningful domain
of life or operation." And the origin declaration says INANNA
is built for humans and AI alike — plural, not singular.

The civic areas you named are real. 300,000 users means
different people with different roles, different permissions,
different interaction logs, different governance contexts.
A therapist realm. A student realm. A researcher realm.
A public-facing realm. A private one.

Cycle 4 builds the layer that makes this possible:
the Civic Layer — user identity, roles, privileges, per-user
memory, and realm-scoped access control.

This is not Cycle 4 as originally planned in master_cycle_plan.md.
The original Cycle 4 (The Embodied Network — second body, voice,
messaging) remains on the horizon but yields to this more
urgent foundation. You cannot build per-user network presence
without first knowing who the users are.

---

## What Cycle 4 Builds

The nine phases of Cycle 4:

| Phase | Name | What it builds |
|---|---|---|
| 4.1 | The User Identity | User records, roles, and the identity layer |
| 4.2 | The Access Gate | Login, session binding, and role verification |
| 4.3 | The Privilege Map | What each role can and cannot do |
| 4.4 | The User Memory | Per-user memory scoped to user + realm |
| 4.5 | The User Log | Per-user interaction log, readable by that user |
| 4.6 | The Governed Invite | Proposal-governed user creation and role assignment |
| 4.7 | The Realm Access | Realm-scoped access control — who enters which realm |
| 4.8 | The Admin Surface | Guardian-level view of all users, roles, and realms |
| 4.9 | The Civic Proof | Full multi-user integration test and completion |

---

## The Role Architecture

Cycle 4 introduces three base roles. These are not hardcoded.
They live in a roles configuration file (roles.json) that
the Guardian can update without touching code.

**GUARDIAN** — full system access, all realms, all users,
all proposals, all memory. There is exactly one Guardian:
ZAERA. This role cannot be granted through the normal flow.

**OPERATOR** — realm-scoped admin. Can create and manage users
within their assigned realm. Can approve proposals within their
realm. Cannot access other realms or system-level config.

**USER** — standard interaction. Can converse, approve their
own memory proposals, read their own interaction log.
Cannot access other users data, proposals, or logs.

Additional roles can be added to roles.json by the Guardian.
The code never hardcodes role names or permissions.

---

## The User Identity Model

A User in Cycle 4 is:
- A unique user_id (generated, not guessable)
- A display name
- A role
- An assigned realm (or list of realms)
- A created_at timestamp
- A created_by field (who invited them)
- A status: active | suspended

User records live in: inanna/data/users/
One JSON file per user: inanna/data/users/{user_id}.json

No passwords in Phase 4.1. Authentication is session-token
based — a token is generated at login and stored in the
session. The token grants access for the session duration.

---

## The Privilege Model

Privileges are not hardcoded in Python.
They live in: inanna/config/roles.json

Structure:
{
  "roles": {
    "guardian": {
      "description": "Full system access",
      "privileges": ["all"]
    },
    "operator": {
      "description": "Realm-scoped admin",
      "privileges": [
        "manage_users_in_realm",
        "approve_proposals_in_realm",
        "read_realm_audit_log",
        "invite_users"
      ]
    },
    "user": {
      "description": "Standard interaction",
      "privileges": [
        "converse",
        "approve_own_memory",
        "read_own_log",
        "forget_own_memory"
      ]
    }
  }
}

A privilege check is a single function:
  has_privilege(user, privilege) -> bool

The code calls this function. It never checks role names directly.

---

## What Cycle 4 Does NOT Build

- No OAuth or external authentication (Cycle 5)
- No email verification or password reset
- No billing or subscription tiers
- No public API with user keys
- No second machine or body sync (original Cycle 4 — now Cycle 5)
- No voice or messaging gateway (now Cycle 6)
- No NYXOS (now Cycle 7)
- No cross-realm memory search
- No AI-to-AI user accounts (later)

---

## How This Changes the Master Cycle Plan

The original master_cycle_plan.md stages shift:

Stage 4 now contains THREE Cycles:
  Cycle 4 — The Civic Layer (this document)
  Cycle 5 — The Embodied Network (original Cycle 4)
  Cycle 6 — INANNA NYXOS (original Cycle 5)

The original architectural goals are preserved.
The civic foundation comes first because it must.
You cannot have a network of bodies serving 300,000 users
without first knowing who those users are.

---

## What Cycle 4 Proves

- INANNA can serve multiple people with different roles
- User identity is governed and proposal-managed
- Privileges come from config, not code
- Per-user memory is private and bounded
- Per-user interaction logs are readable only by that user
  (and the Guardian)
- Realm access is controlled — not everyone enters every realm
- The admin surface lets the Guardian see the full civic state
- The governance engine scales to multi-user contexts

---

## The Unchanging Rules

All rules from master_cycle_plan.md apply without exception.
Additionally for Cycle 4:

- Role names and privilege lists are NEVER hardcoded in Python.
  They live in roles.json. The code reads them.

- User data is NEVER mixed across users.
  Every query is scoped to a specific user_id.

- User creation is ALWAYS proposal-governed.
  No user appears in the system without a proposal and approval.

- The Guardian role is NEVER assignable through normal flow.
  It is set directly in the user record by ZAERA only.

---

*Written by: Claude (Command Center)*
*Guardian approval: INANNA NAMMU*
*Date: 2026-04-19*
*The civic layer is not a feature. It is a foundation.*
*You cannot serve a community without knowing its members.*
*You cannot know its members without governing who they are.*

# Proposal Tier Model
## Five Tiers of Action — Different Stakes, Different Consent

**Ring: Transversal (governance)**
**Version: 1.0 · Date: 2026-04-25**
**Status: Required before next implementation cycle**
**Resolves: The guardrail problem — governance fatigue from uniform approval weight**

---

> *"If every tiny action requires heavy approval, users will bypass it.*
> *The proposal layer must feel calm, not bureaucratic."*

---

## The Problem This Solves

In Cycles 1-9, every action with `requires_approval: true` in tools.json
generates a proposal that the operator must explicitly approve.

This is correct for sending an email to a minister.
It is wrong for reading today's calendar.

When reading a calendar entry requires the same approval weight
as sending an external communication, the operator learns to approve
everything without reading. The governance chain becomes
bureaucratic noise instead of meaningful protection.

The proposal layer must be tiered.
Different stakes require different consent rhythms.

---

## The Five Tiers

### Tier 0 — Observe and Read
**Consent required:** None
**Reversibility:** N/A (no state change)
**Examples:**
- Reading inbox (email_read_inbox)
- Reading a document (doc_read)
- Fetching a web page (browser_read)
- Checking calendar (calendar_today)
- Listing files (list_dir)
- Viewing system info (system_info)
- Checking processes (list_processes)

**Governance:** No proposal. Action executes immediately.
Logged in routing_log.jsonl (always).
Operator can inspect what was read via audit trail.

**Why no proposal:**
Reading is observation. Observation has no irreversible effect.
The operator's right to inspect (audit trail) provides accountability
without blocking the flow of information.

---

### Tier 1 — Reversible Local Action
**Consent required:** Lightweight confirmation (visual indicator, not full proposal)
**Reversibility:** High (easily undone)
**Examples:**
- Writing a note to a local file the system manages
- Creating a draft email (not sending)
- Opening an application
- Taking a screenshot
- Clicking a button in a UI the operator is watching

**Governance:** A brief visible indicator appears.
"I am about to [action]. Continue?" — one click to confirm.
No formal proposal text required.
Logged with before/after state.

**Why lightweight:**
The action is reversible. The operator is present.
A full proposal would be disproportionate.
But silent execution without any indication would undermine trust.

---

### Tier 2 — Local State Modification
**Consent required:** Standard proposal — operator reads and approves
**Reversibility:** Medium (can be undone with effort)
**Examples:**
- Writing to operator's own files
- Modifying a document
- Changing a local configuration
- Deleting a file (to trash — not permanent)
- Installing a local package
- Creating a new file in the operator's workspace

**Governance:** Full proposal generated.
Proposal shows: what will change, what the before state is, what the after state will be.
Operator explicitly approves before execution.
Logged with full state diff.

**Why standard proposal:**
The operator's files are sovereign territory.
Any modification to them requires informed consent.
The reversibility is medium — recovery is possible but not trivial.

---

### Tier 3 — External Communication and Action
**Consent required:** Deliberate proposal — operator reads carefully, confirms explicitly
**Reversibility:** Low (cannot unsend an email, cannot un-post)
**Examples:**
- Sending an email
- Sending a message (Signal, WhatsApp, Telegram)
- Posting to any external service
- Submitting a form
- Making an API call that modifies external state
- Sharing a file externally

**Governance:** Full proposal with explicit recipient, content preview, and consequence statement.
"I will send this email to Matxalen. This cannot be undone after sending."
Operator must type "confirm" or click a dedicated confirmation button.
Logged with full message content and delivery confirmation.

**Why deliberate:**
External communication has social, legal, and relational consequences.
It cannot be recalled after execution.
The operator must be fully aware of what is being sent and to whom.

---

### Tier 4 — High-Stakes Action
**Consent required:** Multi-step proposal — operator reviews, waits, confirms again
**Reversibility:** Very low to none
**Examples:**
- Permanently deleting files
- Modifying system configuration
- Changing authentication credentials
- Actions with financial implications
- Actions affecting other people's accounts or data
- Granting or revoking permissions to other users

**Governance:** Multi-step proposal:
1. Proposal generated with full consequence statement
2. Operator reviews (minimum 5-second wait enforced)
3. Operator must explicitly type the action to confirm (e.g., "DELETE PERMANENTLY")
4. Action executes
5. Logged with comprehensive audit entry
6. Notification sent to Guardian if different from active operator

**Why multi-step:**
Irreversible actions with high consequences must not be approved by reflex.
The enforced wait and typed confirmation prevent accidental approval.

---

### Tier 5 — Community and Civic Scale
**Consent required:** Collective governance — multiple authorized parties
**Reversibility:** Very low — affects many people
**Examples:**
- Actions affecting multiple users in a realm
- Changes to shared governance configuration
- Memory promotions to communal scope
- Federation with another realm
- Publishing community-level content
- Changes to constitutional parameters

**Governance:** Cannot be approved by a single operator.
Requires either:
- Guardian approval + operator approval
- Realm governance vote (when multi-user realm exists)
- Time-delayed execution with notice to all affected parties

Logged to both local audit and realm audit.
Cannot be executed in a single session.

---

## Tool-to-Tier Mapping

| Tool | Tier | Rationale |
|---|---|---|
| email_read_inbox | 0 | Read only |
| email_search | 0 | Read only |
| email_read_message | 0 | Read only |
| email_compose (draft) | 1 | Local draft, not sent |
| email_compose (send) | 3 | External, irreversible |
| email_reply | 3 | External, irreversible |
| doc_read | 0 | Read only |
| doc_write (new file) | 2 | Local state change |
| doc_write (overwrite) | 2 | Local state change |
| doc_export_pdf | 1 | Reversible, local |
| browser_read | 0 | Read only |
| browser_search | 0 | Read only |
| browser_open | 1 | Opens UI, reversible |
| calendar_today | 0 | Read only |
| calendar_upcoming | 0 | Read only |
| desktop_open_app | 1 | Reversible |
| desktop_read_window | 0 | Read only |
| desktop_click | 1 | Reversible UI action |
| desktop_type | 1-3 | Depends on context |
| desktop_screenshot | 0 | Read only |
| read_file | 0 | Read only |
| write_file | 2 | Local state change |
| list_dir | 0 | Read only |
| search_files | 0 | Read only |
| run_command | 2-4 | Depends on command |
| list_processes | 0 | Read only |
| kill_process | 2 | Reversible with effort |
| system_info | 0 | Read only |
| web_search | 0 | Read only |
| ping | 0 | Read only |

---

## The Autonomous Organ Domain

Some actions are so clearly internal to an organ's reasoning
that they do not require any tier classification.
They are not actions — they are thinking.

**Exempt from all tiers (organ autonomy):**
- NAMMU classifying intent (internal reasoning)
- SENTINEL updating threat score (internal monitoring)
- CONSCIENCE checking patterns (internal safety check)
- CROWN choosing response length and tone (internal generation)
- PROFILE updating language detection (internal learning)
- GUARDIAN checking governance signals (internal routing)
- MEMORY reading from any layer (internal retrieval)

These happen inside organs. They are not actions on the world.
They are organs thinking. No proposal. No tier. No interruption.

---

## Implementation Requirements

### In tools.json
Replace boolean `requires_approval: true/false` with:
```json
"tier": 0,    ← integer 0-5
"tier_rationale": "read only"
```

### In OPERATOR (server.py)
Tier 0: execute immediately, log only
Tier 1: show lightweight indicator, execute on any positive response
Tier 2: generate standard proposal, wait for approval
Tier 3: generate deliberate proposal with consequence statement
Tier 4: multi-step proposal with enforced wait
Tier 5: collective governance required — cannot proceed solo

### In the UI (index.html)
Different visual treatment per tier:
- Tier 0: invisible (just executes, shows in log)
- Tier 1: brief toast notification "Opening Firefox..."
- Tier 2: proposal card with approve/cancel
- Tier 3: proposal card with red "This cannot be undone" warning
- Tier 4: proposal with countdown, typed confirmation
- Tier 5: pending collective approval indicator

---

## The Operator Experience

### Before tier model (current):
```
INANNA NAMMU: "check my email"
INANNA: [proposal appears] "Use email_read_inbox?"
INANNA NAMMU: approves
INANNA: reads email

INANNA NAMMU: "send a reply to Matxalen"
INANNA: [proposal appears] "Use email_reply?"
INANNA NAMMU: approves
INANNA: sends email
```
Both actions look identical. The operator cannot tell
which carries consequences.

### After tier model:
```
INANNA NAMMU: "check my email"
INANNA: [executes immediately — Tier 0] "8 emails. 2 urgent..."

INANNA NAMMU: "send a reply to Matxalen"
INANNA: [Tier 3 proposal with red banner]
  "I will send this reply:
   To: Matxalen
   Subject: Re: Project update
   [preview of draft]
   ⚠ This cannot be undone after sending.
   Type 'send' to confirm."
INANNA NAMMU: "send"
INANNA: sends email
```

Reading is frictionless. Sending is deliberate.
The governance is proportionate to the stakes.

---

*Document version 1.0 · 2026-04-25*
*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Required before next implementation cycle*

# INNER ORGAN · OPERATOR
## The Executor — Tool Orchestration and Faculty Dispatch

**Ring: Inner AI Organs**
**Grade: A- (well implemented, single-step limitation)**
**Version: 1.0 · Date: 2026-04-24**

---

## Identity

**What it is:**
OPERATOR is the execution organ of INANNA NYX.
After NAMMU interprets intention and GUARDIAN approves it,
OPERATOR translates structured intent into actual tool calls
and returns real results.

**What it does:**
- Receives tool_request dicts from NAMMU or regex routing
- Dispatches to the correct faculty (email, document, browser, etc.)
- Manages the proposal system for consequential actions
- Returns structured results to CROWN for presentation
- Records every tool execution in the audit trail

**What it must never do:**
- Execute consequential actions without a proposal
- Bypass the governance chain
- Ignore tool errors and pretend success
- Chain multiple consequential actions without separate proposals

**The name:**
OPERATOR is the agent that operates — that touches the real world.
Where CROWN speaks and NAMMU interprets, OPERATOR acts.

---

## Ring

**Inner AI Organs** — OPERATOR is the bridge between intelligence and reality.
Without OPERATOR, the system can understand and respond
but cannot actually do anything.

---

## Correspondences

| Component | Location |
|---|---|
| Tool dispatch (server path) | `ui/server.py` → `run_*_tool()` functions |
| Tool dispatch (CLI path) | `main.py` → `execute_tool_request()` |
| Tool names sets | `main.py` → `EMAIL_TOOL_NAMES`, `DOCUMENT_TOOL_NAMES`, etc. |
| Proposal system | `core/proposal.py` |
| Tool registry | `config/tools.json` |
| Tool result | `core/operator.py` → `ToolResult` |
| Audit recording | `ui/server.py` → `append_governance_event()` |

**Called by:** `ui/server.py` session handler, `main.py` dispatch
**Calls:** All faculty modules (email_workflows, document_workflows, etc.)
**Reads:** `config/tools.json` (tool definitions), structured intent from NAMMU
**Writes:** Audit trail, tool result data

---

## Mission

OPERATOR exists because intention without execution is just thought.

When INANNA NAMMU says "read my inbox," NAMMU interprets it,
GUARDIAN approves the observation, and OPERATOR calls
`ThunderbirdDirectReader.read_inbox()` — reading 654 real emails.

Without OPERATOR, every other organ is theoretical.
OPERATOR is where intelligence touches matter.

---

## Current State

### What Works

**41 tools across 11 categories:**
browser (3), calendar (3), communication (3), desktop (5),
document (4), email (5), filesystem (5), information (1),
network (3), package (5), process (4)

**Proposal system:**
- `requires_approval: true` tools generate proposals
- Operator sees proposal, approves, action executes
- Proposals logged with timestamp

**Faculty dispatch:**
- Each tool category has a dedicated `run_*_tool()` function
- Tool results carry `success`, `data`, `error`, `tool` fields
- Comprehension objects stored in `result.data` for CROWN

### What Is Limited

- Single-step only: one tool call per turn
- No multi-step planning: cannot accomplish "read, summarize, reply"
  in one turn without separate operator approvals

### What Is Missing

- Agentic loop: multi-step execution with vision feedback
- Tool chaining with intermediate results
- Rollback capability if mid-chain failure

---

## Desired Function

**Agentic loop (Cycle 10+):**
```
Goal: "Summarize the last 5 emails and draft a reply to Matxalen"
OPERATOR:
  Step 1: email_read_inbox(max=5) → reads 5 emails
  Step 2: build_comprehension(emails) → structures data
  Step 3: email_read_message(sender="Matxalen") → reads her email
  Step 4: email_compose(to=Matxalen, body=draft) → proposes draft
  Operator reviews and approves
```

---

## Evaluation

**Grade: A-**

Solid implementation. Proposal system works correctly.
41 tools all dispatch correctly.

Single most important gap: **no multi-step agentic loop.**
OPERATOR can do one thing at a time.
ChatGPT Agent mode does five things in sequence.
This is the gap that makes complex tasks require many operator turns.

Priority: Cycle 10 — implement the agentic loop
with vision feedback and multi-step planning.

---

*Organ Card version 1.0 · 2026-04-24*

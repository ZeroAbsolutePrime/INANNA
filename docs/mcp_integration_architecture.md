# MCP Integration Architecture
**How INANNA NYX uses the Model Context Protocol**
*Written by: Claude (Command Center)*
*Confirmed by: ZAERA (Guardian)*
*Date: 2026-04-19*
*Informed by: "The Future of MCP" — David Soria Parra, Anthropic*

---

## What MCP Is and Why It Matters to INANNA

The Model Context Protocol is a standardized way for AI agents
to discover, connect to, and use tools and services.
It is to AI connectivity what HTTP is to web communication.
110 million monthly downloads. Used by OpenAI, Google, LangChain,
and thousands of frameworks. One common standard.

INANNA NYX is not just an MCP consumer.
INANNA NYX is a governed MCP orchestrator.

The difference:
  Standard MCP: model discovers tools, calls them, uses results.
  INANNA MCP:   model discovers tools, proposes their use,
                governance approves, tool executes, results visible.

Every MCP call that passes through INANNA passes through Law 1.
No tool executes without declaration and consent.
This is what makes INANNA constitutional rather than just connected.

---

## Three Roles INANNA Plays in the MCP Ecosystem

### Role 1 — INANNA as MCP Server (current)

INANNA NYX already exposes its capabilities in a way that
could be wrapped as an MCP server:
- Conversation (CROWN Faculty)
- Analysis (ANALYST Faculty)
- Web search (OPERATOR Faculty via DuckDuckGo)
- Memory management
- Proposal governance

In Cycle 5, these become formal MCP tools with schemas,
discoverable by any MCP-compatible client.
An external agent could invoke INANNA as a governed intelligence
service — not just as a chat interface.

### Role 2 — NAMMU as MCP Client (Cycle 5)

When the Faculty Network arrives, NAMMU becomes an MCP client.
Instead of routing between two hardcoded Faculties (CROWN/ANALYST),
NAMMU discovers available Faculty servers via the Faculty Registry
and routes to them dynamically.

This uses the "progressive discovery" pattern from the MCP spec:
- NAMMU does not load all Faculties into context at once
- NAMMU has a Faculty discovery tool
- When a request arrives, NAMMU queries: what Faculty can handle this?
- The right Faculty is loaded on demand
- Context stays lean. Routing stays intelligent.

The Faculty Registry (faculties.json) is INANNA's curated,
governed subset of the MCP ecosystem.
Not every MCP server is a Faculty.
A Faculty must have a charter, a domain, and governance rules.
It must pass through the proposal engine.

### Role 3 — Governed MCP Gateway (Cycle 5+)

INANNA becomes a governance layer above the MCP ecosystem.
External MCP servers (Slack, Linear, GitHub, network tools)
connect to INANNA rather than directly to the model.
INANNA's governance wraps every external tool call.
The proposal engine gates execution.
The audit surface records every tool invocation.

This means INANNA can connect to any MCP server in the world
and still maintain constitutional governance over every action.
The ecosystem's connectivity with INANNA's law.

---

## The Faculty Network as MCP Architecture

Each domain Faculty in Cycle 5 is an MCP server with:

Tools:
  The Faculty's capabilities expressed as MCP tools.
  SENTINEL: scan_network, analyze_vulnerability, generate_report
  AESCULAPIUS: symptom_analysis, drug_interaction_check, triage
  PYTHIA: deep_research, literature_synthesis, fact_check

Resources:
  Domain knowledge bases the Faculty can read.
  CVE databases for SENTINEL.
  Clinical databases for AESCULAPIUS.
  Academic paper indices for PYTHIA.

Skills (MCP Skills — coming June 2026):
  The Faculty's charter expressed as MCP skills.
  How to use the Faculty correctly.
  What it can and cannot do.
  Its governance rules.
  When NAMMU discovers a Faculty, it receives the charter.
  The Faculty explains itself. Law 4 at the protocol level.

Governance wrapper (INANNA-specific, not standard MCP):
  Every tool call passes through GovernanceLayer.check().
  Sensitive Faculty actions require proposals.
  All Faculty outputs are logged to the audit surface.
  No Faculty call is hidden from the Guardian.

---

## Agent-to-Agent Communication (Cycle 5+)

MCP's upcoming asynchronous task primitive enables
agent-to-agent communication. For INANNA this means:

Multi-Faculty coordination:
  A complex task arrives — e.g. "analyze the security posture
  of this codebase and summarize findings for a non-technical audience".
  NAMMU routes to SENTINEL for the security analysis.
  SENTINEL's findings are passed to CROWN for human-readable summary.
  The handoff is MCP agent-to-agent communication.
  The governance layer wraps both calls.
  The full chain is visible in the audit surface.

This is the Orchestration Layer in Cycle 5 Phase 5.8.
MCP's protocol handles the communication.
INANNA's governance handles the authorization.

---

## "Governed MCP" — The Constitutional Principle

The standard MCP ecosystem has no governance layer.
Tools are discovered and called. Results are returned.
Efficient. Powerful. Ungoverned.

INANNA's MCP integration is always governed:

  Standard:  discover -> call -> result
  INANNA:    discover -> propose -> approve -> call -> result -> audit

This is not a performance tax.
This is the price of operating with consent.
And for the domains INANNA will serve —
security, clinical, legal, research, civic —
consent is not optional. It is the foundation.

The "governed MCP" principle extends to every cycle:
- Cycle 5: Faculty calls governed
- Cycle 6: Cross-body sync governed
- Cycle 7: OS-level service calls governed

No matter how connected INANNA becomes,
the proposal engine is always between intention and action.

---

## Implementation Milestones

| Cycle | MCP milestone |
|---|---|
| 4 (current) | Operator tool via DuckDuckGo — governed single tool |
| 5.2 | Tool Registry in tools.json — MCP tool discovery pattern |
| 5.5 | Faculty Registry in faculties.json — governed MCP servers |
| 5.6 | NAMMU as MCP client — progressive Faculty discovery |
| 5.7 | First domain Faculty as MCP server (SENTINEL) |
| 5.8 | Multi-Faculty MCP agent-to-agent coordination |
| 6.x | Cross-body MCP sync — distributed governed network |
| 7.x | NAMMU as OS-level MCP service on INANNA NYXOS |

---

## Why This Matters Now

We are building the governance layer first.
The constitutional core, the civic layer, the commander room —
these are not prerequisites to be completed before the "real" work.
They ARE the real work.

Every MCP server in the world is a potential Faculty.
Every tool in the ecosystem is a potential Operator tool.
Every external agent is a potential collaborator.

INANNA can connect to all of it.
But INANNA connects on its own terms.
Constitutional terms.

The governance layer we are building in Cycles 1-4
is the foundation that makes Cycle 5's connectivity safe.
Without it, connectivity is just exposure.
With it, connectivity is power under law.

---

*This document will be amended as the MCP specification evolves.*
*Watch: MCP Skills (June 2026), Stateless Transport (June 2026),*
*Agent-to-Agent Tasks (in development).*
*Written by: Claude (Command Center)*
*Confirmed by: ZAERA (Guardian)*
*Date: 2026-04-19*

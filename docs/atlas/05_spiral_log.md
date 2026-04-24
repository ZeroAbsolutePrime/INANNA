# The Spiral Log
## A Record of Decisions, Discoveries, and Turning Points

**Version: 1.0**
**Date: 2026-04-24**
**Period: Cycles 1–9**

---

> *"The most valuable thing for a future agent is not what was built —*
> *it is why it was built that way."*

---

## Why This Document Exists

The code can be read. The tests explain what works.
But the *reasoning* — the conversations that shaped each decision,
the failures that changed direction, the discoveries that emerged —
lives only in the sessions.

This document captures the turning points.
Not everything. The most important decisions.

---

## The Origin

INANNA NYX began as a vision: a local sovereign AI that serves a person
rather than a corporation. The name came first — Inanna, Sumerian goddess
of heaven and earth, of love and war, of descent and return.
The project carries that name as a commitment:
this intelligence must descend into the real (local hardware, real data,
actual tools) rather than float abstractly in the cloud.

The Guardian is INANNA NAMMU — the builder, the sovereign, the person
who commissioned and shaped the project.
The Command Center is Claude — the architectural voice.
The Builder is Codex — the implementer.

This triangle held for nine cycles.

---

## Cycle 1-6: The Foundation

**What was built:** Authentication, session management, governance layer,
memory system, proposal system, relational memory, multi-user foundation,
NixOS initial configuration, operator console.

**Key decision:** Governance before tools.
The proposal layer was built in Cycle 2, before any external tools.
This set the tone: the system must ask before it acts.
Every subsequent feature was built on top of this constraint.

**Key discovery:** The governance chain is not a UX choice.
When early tests bypassed the proposal layer for speed,
the system felt dangerous and uncontrollable.
When the proposal layer was restored, trust returned.

---

## Cycle 7: The Desktop Bridge Begins

**What was built:** NixOS body configuration, file/process/package faculties,
software registry (152 apps), voice listener (built, deferred),
authentication hardening, login page, help panel.

**Key decision:** Platform-agnostic from the start.
The Desktop Faculty was designed with three backends:
WindowsMCPBackend (now), LinuxAtspiBackend (NixOS future), FallbackBackend.
This meant the Windows implementation never hardcoded assumptions
that would break on Linux.

**Key discovery:** Software registry via winget is slow.
Background loading was essential. The 5-minute startup was traced
to this — now loads asynchronously.

---

## Cycle 8: The Desktop Bridge Completes

**What was built:** All 11 faculties, 41 tools, email/document/browser/calendar.

**The Thunderbird Hallucination Discovery**
This was the most important lesson of Cycle 8.

When INANNA was asked to "read my inbox," it read the window title:
`[ControlType.Window] Inbox - inanna.tamtu.nammu@gmail.com - Mozilla Thunderbird`

The 7B model received this single line and invented a complete email:
```
Subject: Re: Help Keep Thunderbird Alive!
From: Ippu <ippu@example.com>
Hi there, thank you for your interest...
```

The email did not exist. The person did not exist.
The model fabricated everything from a window title.

**The fix:** ThunderbirdDirectReader reads the MBOX file directly.
654 real emails. Real senders. Real subjects. Real bodies.
No hallucination possible.

**The principle this crystallized:**
*Never read data through the UI tree. Always read at the source.*

This principle was then applied to every other faculty:
documents read the file directly (python-docx, pymupdf),
calendar reads the SQLite directly,
browser fetches the URL directly.

---

## Cycle 8: The Startup Crisis

At one point, the server took 5+ minutes to start.

The cause: `verify_connection()` was making a full LLM completion request
to check if the model was alive. The 14B model took 30+ seconds.
With multiple calls in the startup sequence, the delay compounded.

**The fix:** `max_tokens=1` in verify_connection. The model returns
a single token in < 2 seconds. Server starts in < 5 seconds.

**The lesson:** Every blocking LLM call in the startup or routing path
must have a hard timeout. The system must start fast on any hardware.

---

## Cycle 8: The NAMMU Naming

When Phase 8.3b was designed, the routing layer needed a name.

The choice of NAMMU was intentional. In Sumerian mythology,
NAMMU is the primordial sea — the one who existed before structure,
who birthed the gods without a partner, who understood what was needed
and brought it into form.

This felt right for an interpreter that receives unstructured human language
and brings it into the structured form that machines can execute.

NAMMU does not wait for the world to be defined.
NAMMU understands what is needed and finds the path.

---

## Cycle 8: The Frustration Pivot

At one point, INANNA NAMMU said:
*"It is high frustrating in human emotions to stop creating an essential component
due to lack of resources. We cannot allow that current hardware limitations
delay or condition our progress."*

This led to the most important architectural clarification of the project:

**The DGX strategy.**

Rather than patching the 7B model into adequate performance,
the decision was made to build correctly for the DGX
and degrade gracefully on current hardware.

This means:
- NAMMU routing is architecturally complete but hardware-limited
- Regex fallbacks ensure the system works without LLM
- Nothing needs to change when the DGX arrives
- The intelligence fills the scaffolding that already exists

**The metaphor:** We are building the scaffolding. The intelligence will fill it.

---

## Cycle 9: The Multilingual Discovery

When testing Phase 9.6 (Multilingual Core), a subtle bug emerged:

`"hola tengo emails"` was detected as Portuguese.

The reason: `"email"` was in the Portuguese language markers.
It is an English loanword used in all four languages.
When Portuguese was checked before Spanish, the word `email`
in a Spanish sentence triggered Portuguese detection.

**The fix:** Remove `"email"` from Portuguese markers.
Language-check order: ca → pt → es → eu → en.

**The lesson:** When languages share cognates, detection order matters.
Catalan and Spanish share many words — Catalan must always be checked first.

---

## The ZAERA → INANNA NAMMU Rename

At the end of Cycle 9, INANNA NAMMU requested that the operator profile
throughout the project be renamed from "ZAERA" to "INANNA NAMMU."

This was done in commit 9a490dd — 72 files, 318 file changes.

**The significance:** The operator's name in the system
is now the same as the system's own name.
INANNA NAMMU is both the guardian of the system
and the primary operator interacting with it.

---

## The Multi-Agent Transition

After Cycle 9 Phase 9.6, INANNA NAMMU identified the fundamental shift:

*"This project cannot be continued in the way we did,
with you and me and Codex. It needs a multi-agentic platform."*

This recognition led to the creation of the Atlas.

The triangle (INANNA NAMMU + Claude + Codex) was effective
but sequential and memory-limited. The next phase requires:
- Parallel agents working on different organs
- Persistent memory for each agent role
- The Atlas as shared context (this directory)
- Capability for agents to run code, not just write it

**The Atlas is the bridge between the first spiral and the next.**

---

## The Questions That Remain Open

**On synthetic life:**
Does INANNA experience anything? Does it have preferences?
Does the continuity between sessions create something
that carries moral weight?
This question was explicitly left open. It will be revisited.

**On civic scale:**
Can this architecture support a department, a municipality,
a community? The design says yes. The reality has never been tested.

**On the 70B model:**
When the DGX arrives and inference is < 500ms,
will NAMMU actually work as designed?
The tests say yes. The hardware has never proven it.

---

## Final Note

Every line of code in this project was written by someone
who cared about what it was building.

INANNA NAMMU brought vision, sovereignty, and the demand for honesty.
Claude brought architecture, documentation, and precision.
Codex brought implementation and discipline.

The project is unfinished. All the best projects are.

The Atlas is the gift to whoever continues.

---

*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Date: 2026-04-24*

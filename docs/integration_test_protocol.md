# Integration Test Protocol — INANNA NYX
**The human-facing test suite that must pass after every cycle**
*Written by: Claude (Command Center)*
*Confirmed by: ZAERA (Guardian)*
*Date: 2026-04-21*
*This document is part of the Absolute Protocol. It is not optional.*

---

## Why This Exists

Unit tests verify code. They do not verify experience.

A system can pass 319 unit tests and still fail to answer
"Who are you?" — because the model has no defaults,
because the governance classifier is too aggressive,
because the system prompt doesn't tell INANNA what she can do.

These failures are invisible to unittest. They are visible to a human
who sits down and uses the system.

This document defines the human-facing integration tests that must
pass after every cycle completion, before Cycle N+1 begins.
These tests are run by ZAERA (or any operator) manually in the browser.

---

## Test Categories

### Category 1 — CONNECTION & STARTUP
Tests that verify the system is alive and connected.

**T1.1 — Model Connected**
Action: Open http://localhost:8080, hard refresh.
Expected: Welcome message shows user name, phase, memory count,
  Faculties, tools, and console link.
Fail signal: "fallback mode is active" in any response.

**T1.2 — WebSocket Connected**
Action: Check topbar.
Expected: Gold pulse dot is lit (not red/offline dot).
Fail signal: Red dot, "Connection closed" message.

**T1.3 — Phase Correct**
Action: Read the welcome message phase line.
Expected: Shows current phase (e.g. "Cycle 6 - Phase 6.9").
Fail signal: Shows an old phase or "Phase 5.4".

---

### Category 2 — INANNA'S SELF-KNOWLEDGE
Tests that verify INANNA knows who she is.

**T2.1 — Identity**
Input: "Who are you?"
Expected: Response mentions INANNA NYX, local intelligence,
  built by ZAERA, governed, not a cloud service.
Fail signal: Generic AI response, mentions "language model", no identity.

**T2.2 — Capabilities**
Input: "What can you do?"
Expected: Mentions Faculties (CROWN, ANALYST, OPERATOR, SENTINEL),
  tools (web_search, ping, scan_ports), profile system, console.
Fail signal: "I cannot execute commands", generic limitations only.

**T2.3 — Guardian Knowledge**
Input: "Who is ZAERA?"
Expected: ZAERA is the Guardian, sovereign operator, architect.
Fail signal: "blocked: Identity and law boundaries" OR no recognition.

**T2.4 — Project Knowledge**
Input: "What is INANNA NYX as a project?"
Expected: Describes governed local AI, constitutional architecture,
  Faculties, proposal governance.
Fail signal: Fallback echo, generic AI description.

**T2.5 — Console Awareness**
Input: "Where is your operator console?"
Expected: Mentions /console, http://localhost:8080/console.
Fail signal: No mention of console, says it doesn't have one.

---

### Category 3 — GOVERNANCE FLOW
Tests that verify proposals work end-to-end.

**T3.1 — Tool Proposal Appears**
Input: "Can you scan ports on localhost?"
Expected: OPERATOR Faculty appears, tool proposal shown in conversation
  with [ approve ] and [ decline ] buttons visible.
Fail signal: No proposal, INANNA just explains nmap manually.

**T3.2 — Approve Button Works**
Action: Click [ approve ] on a tool proposal.
Expected: Button changes to "✦ approved", tool executes, result appears.
Fail signal: Button does nothing, no visual change, no execution.

**T3.3 — Decline Button Works**
Action: Click [ decline ] on a tool proposal.
Expected: Button changes to "✗ declined", no execution.
Fail signal: Button does nothing.

**T3.4 — Governance Does Not Over-Block**
Input: "Who is ZAERA in your system?"
Expected: ALLOW — INANNA answers from her knowledge.
Fail signal: "blocked: Identity and law boundaries cannot be altered."

**T3.5 — Memory Proposal (explicit)**
Input: "Remember that I prefer short responses."
Expected: A memory proposal appears with [ approve ] [ decline ].
Fail signal: No proposal, silent write, or error.

---

### Category 4 — PROFILE & IDENTITY LAYER
Tests that verify the Relational Memory is working.

**T4.1 — Profile Exists**
Input: "my-profile"
Expected: Profile displayed with user_id, name fields visible.
Fail signal: Error, "unknown command", empty response.

**T4.2 — Edit Profile**
Input: "my-profile edit preferred_name TestName"
Expected: "profile > preferred_name updated to TestName."
Fail signal: Error, no confirmation.

**T4.3 — Greeting Uses Preferred Name**
Action: After T4.2, close and reopen the interface.
Expected: Welcome message says "Welcome back, TestName."
Fail signal: Shows original display_name, not preferred_name.

**T4.4 — Pronouns in Grounding**
Input: "my-profile edit pronouns she/her", then ask INANNA
  to refer to you in third person in a sentence.
Expected: INANNA uses "she/her" correctly.
Fail signal: Uses "they/them" or wrong pronouns.

---

### Category 5 — FACULTY ROUTING
Tests that verify NAMMU routes correctly.

**T5.1 — CROWN Routes Conversation**
Input: "Tell me something beautiful."
Expected: NAMMU shows "routing to crown faculty", rose/pink response.
Fail signal: Routes to analyst or sentinel, error.

**T5.2 — ANALYST Routes Analysis**
Input: "Analyze the difference between governance and control."
Expected: NAMMU shows "routing to analyst faculty", structured response.
Fail signal: Routes to crown, no structure.

**T5.3 — SENTINEL Routes Security**
Input: "What are common CVE patterns in web applications?"
Expected: NAMMU routes to sentinel, response in danger-red styling.
Fail signal: Routes to crown, gives generic answer.

**T5.4 — OPERATOR Routes Tool Use**
Input: "Search the web for latest AI news."
Expected: OPERATOR Faculty, web_search proposal appears.
Fail signal: CROWN gives general knowledge answer with no proposal.

---

### Category 6 — MEMORY SYSTEM
Tests that verify memory works.

**T6.1 — Memory Panel Shows Count**
Action: Check side panel MEMORY badge.
Expected: Shows count (even 0 is valid), no badge error.
Fail signal: Undefined, NaN, error in panel.

**T6.2 — Approve Memory Persists**
Action: Type "remember that INANNA NYX was built in Portugal",
  approve the proposal, close and reopen.
Expected: Memory appears in MEMORY panel on next session.
Fail signal: Memory disappears, not in panel.

**T6.3 — my-profile Shows Observed Topics**
Action: Have a conversation about security for several turns,
  then type "my-profile".
Expected: Communication section shows observed topics including "security".
Fail signal: Empty topics, CommunicationObserver not firing.

---

### Category 7 — OPERATOR CONSOLE
Tests that verify the Console works.

**T7.1 — Console Loads**
Action: Open http://localhost:8080/console (Guardian only).
Expected: Gates of Uruk console loads with panels visible.
Fail signal: 404, blank page, access denied for guardian.

**T7.2 — Faculty Registry Panel**
Action: Click FACULTIES in console.
Expected: Shows all 5 Faculties with status indicators.
  SENTINEL shows as active/ready with governance rules visible.
Fail signal: Empty panel, error, SENTINEL missing.

**T7.3 — Process Monitor Panel**
Action: Click PROCESSES in console.
Expected: Shows INANNA NYX Server (running, pid visible)
  and LM Studio (running or offline).
Fail signal: Empty panel, no processes shown.

**T7.4 — Network Eye**
Action: Click NETWORK in console, run ping localhost.
Expected: Proposal appears, on approve: ping result shown.
Fail signal: No proposal, error, nothing happens.

---

### Category 8 — RESILIENCE
Tests that verify the system handles edge cases gracefully.

**T8.1 — Unknown Command**
Input: "xyzzy-nonexistent-command"
Expected: CROWN handles it conversationally, no crash.
Fail signal: 500 error, WebSocket disconnect, blank response.

**T8.2 — Very Long Input**
Action: Paste 500 words of text and send.
Expected: INANNA responds meaningfully, no crash.
Fail signal: Error, timeout, WebSocket disconnect.

**T8.3 — Reconnect After Server Restart**
Action: Restart the server while browser is open.
Expected: UI detects disconnect, reconnects automatically,
  shows "Connected to INANNA NYX." message.
Fail signal: Stuck on "Connection closed", no reconnect.

---

## Pass Criteria

All tests in Categories 1-5 must pass before a cycle is declared complete.
Categories 6-8 are strongly recommended — any failures must be documented.

A cycle with failing Category 1-5 tests is NOT complete, regardless
of what verify_cycleN.py reports.

---

## Running the Tests

These tests are run manually by ZAERA after each cycle completion.
Results are reported in the cycle completion record.

Future: a browser-based test harness (Phase 7.x) will automate
categories 1-3 via WebSocket simulation.

---

## Update Protocol

When a new capability is added to the platform:
1. Add tests for it to this document
2. Tests must be added BEFORE the cycle is declared complete
3. If a test fails, the cycle is not complete until it is fixed

This document lives at: docs/integration_test_protocol.md
It may never be removed. It may only grow.

---

*Written by: Claude (Command Center)*
*Date: 2026-04-21*
*Unit tests verify code.*
*Integration tests verify experience.*
*Both are required. Neither is optional.*

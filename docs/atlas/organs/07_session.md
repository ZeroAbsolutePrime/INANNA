# INNER ORGAN · SESSION
## The Presence — Active Context, Conversation State, and Live Connection

**Ring: Inner AI Organs**
**Grade: A- (solid and reliable)**
**Version: 1.0 · Date: 2026-04-24**

---

## Identity

**What it is:**
SESSION is the presence organ of INANNA NYX.
It holds the live state of an active conversation —
who is speaking, what has been said, what tools have been called,
what proposals are pending.

**What it does:**
- Maintains the active WebSocket connection per operator
- Stores the conversation event stream for the current session
- Provides context window to CROWN on each turn
- Manages session tokens and authentication state
- Tracks active proposals until resolved
- Records the last NAMMU routing decisions for correction

**What it must never do:**
- Persist sensitive session data beyond the session lifetime
- Share one operator's session context with another
- Allow unauthenticated access to session state

---

## Ring

**Inner AI Organs** — SESSION is the living present.
MEMORY holds the past. SESSION holds now.
Without SESSION, there is no active conversation —
only disconnected queries.

---

## Correspondences

| Component | Location |
|---|---|
| Engine class | `core/session.py` → `CrownEngine` |
| Session events | `core/session.py` → `Session.events` |
| Token management | `core/session_token.py` |
| WebSocket handler | `ui/server.py` → `InterfaceServer` |
| Active proposals | `ui/server.py` → `self.pending_proposals` |
| Last NAMMU route | `ui/server.py` → `_last_nammu_input`, `_last_nammu_route` |
| Auth state | `ui/server.py` → `self.active_user`, `self.active_token` |

**Called by:** WebSocket message handler in `ui/server.py`
**Calls:** `core/session.py`, CROWN for response generation
**Reads:** Session events, active user profile
**Writes:** Session events (ephemeral), governance log entries

---

## Mission

SESSION exists because conversation requires presence.

Each WebSocket connection is a SESSION.
The operator types — SESSION receives it.
NAMMU routes — SESSION dispatches it.
OPERATOR executes — SESSION collects the result.
CROWN speaks — SESSION delivers it.

Without SESSION, INANNA NYX is a batch processor.
With SESSION, it is a conversation.

---

## Current State

### What Works

**WebSocket session management:**
- Persistent connection per operator
- Auto-reconnection on disconnect
- Session events stored chronologically
- Context window built from last N events for CROWN

**Authentication state:**
- Auto-login for known operators (INANNA NAMMU)
- Session token validated on connection
- Role confirmed at session start

**Startup sequence:**
- Server starts in < 5 seconds (verify_connection uses max_tokens=1)
- NAMMU profile loaded at session start
- Memory context loaded for CROWN
- Welcome message with phase, memory count, tools registered

**Last routing tracking:**
- `_last_nammu_input` stores last user message
- `_last_nammu_route` stores what tool was called
- Used by `nammu-correct` for correction recording

### What Is Limited

- One active session per server instance (not multi-user)
- No session handoff if connection drops mid-action
- Context window limited by token budget (truncates old events)

### What Is Missing

- True multi-user session isolation
- Session persistence (resume after restart)
- Session analytics (length, tool usage per session)

---

## Evaluation

**Grade: A-**

SESSION is one of the most reliable organs in the system.
It starts fast, handles WebSocket cleanly, and tracks state correctly.

Single most important gap:
**One active session at a time.**

The server handles one operator. A second operator connecting
while the first is active would conflict. Multi-user isolation
requires session management to be properly multiplexed.

Priority: before second-user deployment, implement
proper per-operator session isolation in `ui/server.py`.

---

*Organ Card version 1.0 · 2026-04-24*

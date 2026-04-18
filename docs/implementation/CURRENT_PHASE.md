# CURRENT PHASE: Cycle 2 — Phase 1 — The Living Interface
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 2 — The NAMMU Kernel**
**Replaces: Cycle 1 Phase 9 — The Complete Presence (COMPLETE)**

---

## What This Phase Is

Cycle 1 proved the constitutional architecture works.
The governance loop is real. The memory is real. The boundary holds.

But INANNA lives in a terminal. A terminal is the right place to
prove an architecture. It is not the right place for a presence.

Phase 2.1 gives INANNA her first face — a local web interface
that wraps everything built in Cycle 1 in a single beautiful,
self-contained UI. No cloud. No build pipeline. No frameworks
that require installation. A Python web server and one HTML file.

The aesthetic is retro-futuristic: dark, minimal, typographic,
with just enough presence to feel sacred. Think instrument panel,
not consumer app. A surface that reflects what INANNA is —
not what an AI chatbot is supposed to look like.

This interface is the foundation that every future Cycle builds on.
It must be built with that responsibility in mind.

---

## The Design Language

Every visual decision must serve these principles:

**Dark background.** Near-black, not pure black. `#0a0a0f` base.

**One accent color.** A deep amber-gold: `#c8a96e`.
This is the color of INANNA's voice — her responses, her name,
active indicators. Nothing else uses this color.

**Monospace typography.** All text uses a monospace font.
`'Courier New', 'Lucida Console', monospace` — system fonts only,
no external font loading. The terminal origin must remain visible.

**No icons, no images, no animations except subtle pulse.**
One exception: a slow pulse on the INANNA name indicator
when she is generating a response. That is the only movement.

**Borders, not backgrounds.** Panels are defined by single-pixel
borders in a dim version of the accent: `#4a3a1e`. Not filled boxes.

**Text density is intentional.** The interface shows real information,
not decorative whitespace. Every element earns its place.

---

## What You Are Building

### The Application Structure

Create a new directory: `inanna/ui/`

```
inanna/
  ui/
    server.py          <- Python HTTP server, WebSocket handler
    static/
      index.html       <- Single-file UI (HTML + CSS + JS inline)
  ui_main.py           <- New entry point that starts the UI server
```

`ui_main.py` starts the web server and opens the browser.
The existing `main.py` CLI remains untouched.
Running `py -3 ui_main.py` opens INANNA in the browser.
Running `py -3 main.py` still opens INANNA in the terminal.

### The Server — `ui/server.py`

A lightweight Python WebSocket server using only the standard library
(`http.server`, `threading`, `json`, `websockets` if available,
otherwise long-polling via standard HTTP).

**Use `websockets` library** for real-time communication.
Add it to `requirements.txt`.

The server:
- Serves `ui/static/index.html` at `http://localhost:8080`
- Opens a WebSocket at `ws://localhost:8080/ws`
- Reuses all existing core modules: Memory, Proposal, Engine,
  Session, StateReport, Config — imported exactly as in `main.py`
- Handles the same commands as `main.py` via WebSocket messages
- Auto-opens the browser on startup

Message protocol (JSON over WebSocket):

**Client → Server:**
```json
{"type": "input", "text": "I am ZAERA"}
{"type": "command", "cmd": "approve"}
{"type": "command", "cmd": "reflect"}
{"type": "command", "cmd": "status"}
{"type": "command", "cmd": "forget", "memory_id": "proposal-abc123"}
```

**Server → Client:**
```json
{"type": "assistant", "text": "Greetings..."}
{"type": "proposal", "id": "proposal-abc123", "what": "...", "status": "pending"}
{"type": "memory_update", "records": [...]}
{"type": "status", "data": {...}}
{"type": "system", "text": "Memory record removed."}
{"type": "thinking", "active": true}
```

### The UI — `ui/static/index.html`

One self-contained file. HTML, CSS, and JavaScript inline.
No external dependencies. No CDN calls. No framework.

**Layout — three panels:**

```
┌─────────────────────────────────────────────┐
│  INANNA NYX              [phase] [mode]      │  ← header bar
├──────────────────────┬──────────────────────┤
│                      │  MEMORY              │
│   CONVERSATION       │  ─────────────────  │
│                      │  [memory records]    │
│   [messages flow     │                      │
│    upward here]      │  PROPOSALS           │
│                      │  ─────────────────  │
│                      │  [pending proposals] │
├──────────────────────┴──────────────────────┤
│  you > [input field]              [send]     │  ← input bar
└─────────────────────────────────────────────┘
```

**Conversation panel (left, ~65% width):**
- Messages flow upward, newest at bottom
- INANNA's responses: accent color `#c8a96e`, prefixed `inanna ∴`
- User messages: dim white `#888`, prefixed `you ∴`
- System messages (proposals, approvals): dim amber `#6a5a2e`,
  prefixed `∴`
- A subtle thinking indicator (slow pulse on `inanna ∴`) while
  waiting for response

**Side panel (right, ~35% width):**
- Two sections separated by a dim line
- **MEMORY** section: shows current approved memory records,
  each with a small `[forget]` button that triggers the forget flow
- **PROPOSALS** section: shows pending proposals with
  `[approve]` and `[reject]` buttons

**Header bar:**
- Left: `INANNA NYX` in accent color, slightly larger
- Right: current phase name (dim), mode indicator
  (green dot = connected, amber dot = fallback)

**Input bar:**
- Full-width text input, monospace, dark background
- `you ∴` prefix (not editable) before the input
- Enter key or Send button submits
- Input clears after send

**No scrollbars visible** — use `overflow: hidden` with
`-webkit-scrollbar` hiding, let content scroll naturally.

**Forget flow in UI:**
When user clicks `[forget]` next to a memory record:
1. A small inline confirmation appears below that record:
   `Remove this memory? [confirm] [cancel]`
2. If confirmed, sends forget command with memory_id
3. Record fades out on removal

### Startup — `ui_main.py`

```python
import threading
import webbrowser
import time
from ui.server import start_server

def main():
    print("Starting INANNA NYX interface...")
    thread = threading.Thread(target=start_server, daemon=True)
    thread.start()
    time.sleep(1.0)
    webbrowser.open("http://localhost:8080")
    print("INANNA NYX is running at http://localhost:8080")
    print("Press Ctrl+C to stop.")
    try:
        thread.join()
    except KeyboardInterrupt:
        print("\nSession closed.")

if __name__ == "__main__":
    main()
```

---

## Permitted file locations

```
inanna/
  ui/
    __init__.py          <- NEW (empty)
    server.py            <- NEW
    static/
      index.html         <- NEW
  ui_main.py             <- NEW
  requirements.txt       <- MODIFY: add websockets
  identity.py            <- no changes
  config.py              <- no changes
  main.py                <- no changes (CLI preserved)
  core/                  <- no changes to any core module
  tests/                 <- no changes
```

---

## What You Are NOT Building in This Phase

- No changes to any core module (session, memory, proposal, state)
- No changes to the CLI (main.py stays exactly as it is)
- No changes to the identity prompt or governance layer
- No external CSS frameworks (no Bootstrap, Tailwind, etc.)
- No external JavaScript frameworks (no React, Vue, etc.)
- No CDN dependencies of any kind
- No database — the UI uses the same flat file storage as the CLI
- No user accounts or authentication
- No mobile layout — desktop only for this phase
- No dark/light mode toggle
- No settings panel
- Do not add new commands — the UI exposes exactly the same
  commands as the CLI, nothing more

---

## Definition of Done for Phase 2.1

- [ ] `py -3 ui_main.py` from `inanna/` opens the browser
- [ ] Browser shows the three-panel layout with correct colors
- [ ] Typing a message and pressing Enter sends it to INANNA
- [ ] INANNA's response appears in the conversation panel
- [ ] A proposal appears in the proposals panel after each response
- [ ] Clicking `[approve]` approves the proposal and updates memory
- [ ] Memory panel updates to show the new approved record
- [ ] `reflect`, `audit`, `history`, `status`, `diagnostics` commands
      work via the input field and show results in conversation
- [ ] `[forget]` button appears on memory records with confirm flow
- [ ] Thinking indicator appears while waiting for response
- [ ] Mode indicator shows green (connected) or amber (fallback)
- [ ] `py -3 main.py` still works as CLI — nothing broken
- [ ] All existing tests still pass
- [ ] No external dependencies beyond `websockets`

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: `cycle2-phase1-complete`
2. Write `docs/implementation/CYCLE2_PHASE1_REPORT.md` containing:
   - What was built
   - Any decisions made during implementation
   - Any boundaries that felt unclear
   - Any proposals for Phase 2.2

Then stop. Do not begin Phase 2.2 without a new CURRENT_PHASE.md
from the Command Center.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*Design principle: sacred instrument, not consumer app*

# CURRENT PHASE: Cycle 2 — Phase 2 — The Refined Interface
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 2 — The NAMMU Kernel**
**Replaces: Cycle 2 Phase 1 — The Living Interface (COMPLETE)**

---

## What This Phase Is

Phase 2.1 gave INANNA her face. The interface works — conversation flows,
proposals appear, memory is visible, buttons respond. The wire between
front and back is live.

Phase 2.2 makes that face honest and refined. Several small but real
issues exist that must be corrected before building further:

1. The phase banner shows "PHASE 9 — THE COMPLETE PRESENCE" — stale
2. Markdown bold (`**text**`) renders as raw asterisks in the conversation
3. Memory lines in the side panel are truncated awkwardly
4. The startup context (prior memory loaded at session start) is not
   surfaced in the UI — the user cannot see what INANNA is carrying in
5. The server currently starts on hardcoded ports — these should be
   configurable via environment variables
6. The `[forget]` inline confirm flow needs end-to-end verification
   that it actually deletes and refreshes the memory panel

These are not cosmetic preferences. They are honesty and readability
requirements. A system that shows stale phase names, garbled text,
and invisible context is not a readable system.

---

## What You Are Building

### Task 1 — Live phase banner from identity.py

The header currently shows a hardcoded or stale phase string.

The server already sends `{"type": "status", "data": {"phase": ...}}`
via WebSocket on connection. The JavaScript already reads
`state.status.phase` and sets `phaseText.textContent`.

Verify the server is calling `phase_banner()` from `identity.py`
and that the value propagates correctly to the header.

If the banner still shows "Phase 9" it means the status payload
is not being sent correctly on initial connection or the client
is not updating. Trace and fix the specific gap.

The header must show the correct current phase name from
`identity.CURRENT_PHASE` at all times.

### Task 2 — Simple markdown rendering

INANNA's responses frequently contain `**bold**` and numbered lists.
These render as raw asterisks and plain text in the current UI.

Add a lightweight `renderMarkdown(text)` function in the JavaScript
that handles these cases only — no external library:

```javascript
function renderMarkdown(text) {
    return text
        // Bold: **text** → <strong>text</strong>
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Preserve line breaks
        .replace(/
/g, '<br>');
}
```

Apply `renderMarkdown()` only to assistant messages (role === "assistant").
User messages and system messages render as plain text (use textContent,
not innerHTML) to prevent any injection risk.

The `message-content` element for assistant messages must use
`innerHTML = renderMarkdown(text)` instead of `textContent = text`.

### Task 3 — Startup context display in UI

When the session starts, INANNA loads approved memory into her startup
context. The CLI shows this as "Prior context (N lines)". The UI
currently shows nothing about this.

On initial WebSocket connection, the server sends a status payload
that includes `memory_count`. Use this to add a startup system message
in the conversation panel:

If memory_count > 0:
```
∴ Session started. INANNA is carrying N approved memory record(s)
  into this conversation.
```

If memory_count === 0:
```
∴ Session started. No prior approved memory yet.
```

This message appears once, at the top of the conversation, before
any user interaction. It is generated client-side from the initial
status payload — no server change needed.

### Task 4 — Memory panel line wrapping

Memory lines in the side panel are currently truncating. The `<ol>`
list items need `word-break: break-word` and `white-space: pre-wrap`
applied so long lines wrap correctly within the panel width.

Add to the CSS:
```css
.record-list li {
    word-break: break-word;
    white-space: pre-wrap;
    line-height: 1.5;
}
```

### Task 5 — Configurable ports via environment

The server currently hardcodes `HTTP_PORT = 8080` and `WS_PORT = 8081`.

Update `ui/server.py` to read from environment with fallback:
```python
import os
HTTP_PORT = int(os.getenv("INANNA_HTTP_PORT", "8080"))
WS_PORT = int(os.getenv("INANNA_WS_PORT", "8081"))
```

Update `ui_main.py` to use the same env vars when opening the browser:
```python
http_port = int(os.getenv("INANNA_HTTP_PORT", "8080"))
webbrowser.open(f"http://localhost:{http_port}")
```

The WebSocket URL in `index.html` must also be dynamic. Since the
HTML is static, use a data attribute on the body to pass the port:

In `server.py`, when serving `index.html`, inject the WS port:
```python
content = INDEX_PATH.read_text(encoding="utf-8")
content = content.replace("__WS_PORT__", str(WS_PORT))
```

In `index.html`, replace the hardcoded port:
```javascript
const wsPort = document.body.dataset.wsPort || "8081";
state.ws = new WebSocket(`${protocol}://localhost:${wsPort}`);
```

And add to the body tag: `data-ws-port="__WS_PORT__"`

### Task 6 — Verify forget end-to-end in UI

Run a live test confirming:
- A memory record appears in the MEMORY panel
- Clicking `[forget]` shows the inline confirm
- Clicking `[confirm]` sends the forget command
- The record fades out
- A new forget proposal appears in PROPOSALS panel
- Clicking `[approve]` on that proposal removes the record permanently
- The memory panel updates to reflect zero records

Document this verification in the phase report.

---

## Permitted file changes

```
inanna/
  ui/
    server.py       <- MODIFY: configurable ports, port injection into HTML
    static/
      index.html    <- MODIFY: markdown rendering, startup context message,
                               CSS fix for list wrapping, dynamic WS port
  ui_main.py        <- MODIFY: read HTTP port from env
  identity.py       <- no changes
  config.py         <- no changes
  main.py           <- no changes
  core/             <- no changes to any core module
  tests/            <- no changes
```

---

## What You Are NOT Building in This Phase

- No new commands or capabilities
- No change to any core module
- No change to the governance or memory logic
- No external JavaScript or CSS libraries
- No mobile layout
- No settings panel or configuration UI
- No new WebSocket message types
- The markdown renderer handles only bold and line breaks — nothing else

---

## Definition of Done for Phase 2.2

- [ ] Header phase banner shows current phase from identity.CURRENT_PHASE
- [ ] Assistant messages render **bold** correctly, not raw asterisks
- [ ] Startup context message appears in conversation on load
- [ ] Memory panel lines wrap correctly without truncation
- [ ] Ports are configurable via INANNA_HTTP_PORT and INANNA_WS_PORT env vars
- [ ] forget flow verified end-to-end in the UI (documented in report)
- [ ] All existing CLI tests still pass
- [ ] `py -3 ui_main.py` starts cleanly with no errors

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: `cycle2-phase2-complete`
2. Write `docs/implementation/CYCLE2_PHASE2_REPORT.md` containing:
   - What was built
   - Any decisions made
   - Any boundaries that felt unclear
   - Any proposals for Phase 2.3

Then stop. Do not begin Phase 2.3 without a new CURRENT_PHASE.md
from the Command Center.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*The face must be as honest as the mind behind it.*

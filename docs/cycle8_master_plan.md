# Cycle 8 — The Desktop Bridge
**INANNA NYX connects to the world**
*Written by: Claude (Command Center)*
*Confirmed by: ZAERA (Guardian)*
*Date: 2026-04-21*
*Prerequisite: Cycle 7 complete — 432 tests, 18 tools, authentication active*

---

## What Cycle 8 Is

Cycle 7 gave INANNA a body — NixOS, file system, processes,
packages, authentication, voice (deferred), polish.

Cycle 8 gives INANNA **hands that reach beyond the terminal**.

The architectural insight from the end of Cycle 7:
instead of building individual integrations for WhatsApp,
LibreOffice, email, Telegram, Signal one by one — we build
**one bridge** to the desktop, and every application on that
desktop becomes reachable through the same channel.

The bridge is called the **Desktop Faculty**.
It uses the MCP Desktop Automation protocol —
the same technology that screen readers use to understand
applications — to let INANNA see and interact with any
running application on the computer.

---

## The Strategic Direction

ZAERA's vision: *"the user maybe uses telegram, signal,
WhatsApp, LibreOffice, email client, and long etc. —
so use the current connected computer as a bridge to
the external world."*

This is correct and achievable. The path is:

```
ZAERA speaks or types
        ↓
INANNA NYX (governed intelligence)
  understands the request
        ↓
INANNA decides: which app, what action
        ↓
Desktop Faculty
  (platform-agnostic bridge layer)
        ↓
  ┌─────────────────────────────────────────┐
  │  Windows (now)     │  NixOS (future)   │
  │  Windows-MCP       │  linux-desktop-   │
  │  UI Automation API │  mcp / AT-SPI2    │
  └─────────────────────────────────────────┘
        ↓
Any installed application:
  WhatsApp Desktop  → read messages, send replies
  LibreOffice       → write letters, edit docs, save
  Thunderbird/mail  → read inbox, reply, compose
  Firefox/Chromium  → navigate, fill forms, click
  Calendar (any)    → create and read events
  File Explorer     → browse, organize
  Any future app    → same channel, no new code
```

INANNA is the **mind**.
Desktop Faculty is the **hands**.
The computer is the **body**.

---

## Platform Transition: Windows → NixOS

This is designed for zero friction.

The Desktop Faculty is an **abstract interface**.
The implementation underneath changes per OS.
INANNA's code never changes when the OS changes.

```python
class DesktopFaculty:
    def __init__(self):
        if platform.system() == "Windows":
            self._backend = WindowsMCPBackend()   # now
        elif platform.system() == "Linux":
            self._backend = LinuxAtspiBackend()   # future NixOS

    # These five methods are identical on both platforms:
    def open_app(self, name: str) -> DesktopResult: ...
    def read_window(self, app_name: str) -> DesktopResult: ...
    def click(self, element_name: str) -> DesktopResult: ...
    def type_text(self, text: str) -> DesktopResult: ...
    def screenshot(self, app_name: str) -> DesktopResult: ...
```

**On NixOS, the switch is:**
- `configuration.nix`: add `at-spi2-core`, `python311Packages.pyatspi`
- `desktop_faculty.py`: detect Linux, instantiate `LinuxAtspiBackend()`
- Everything else: unchanged

The AT-SPI2 accessibility API on Linux is the direct parallel
to Windows UI Automation. Both work by name, not coordinates.
Both work with GTK, Qt, and Electron apps. Electron apps
(WhatsApp Desktop, VS Code, Slack, Discord) behave identically
on both platforms — the same accessibility names, same actions.

---

## Governance Model for Desktop Actions

Desktop actions are more consequential than file reads or
package searches. Sending a message cannot be undone.
Clicking "Delete" on an email cannot be undone.

The governance rules must be strict:

```
OBSERVATION (no proposal needed):
  - Reading window content
  - Taking a screenshot
  - Listing open windows
  - Reading message inbox

LIGHT ACTION (proposal required, auto-trusted after 3x):
  - Opening an application
  - Navigating to a page or folder
  - Typing in a draft (not sent)

CONSEQUENTIAL ACTION (proposal ALWAYS required, no auto-trust):
  - Sending a message (any app)
  - Deleting anything
  - Submitting a form
  - Making a purchase
  - Clicking any "Send", "Delete", "Submit", "Buy"

FORBIDDEN (never, regardless of approval):
  - Accessing banking or payment UIs
  - Entering passwords into any form
  - Actions on behalf of other users
```

This mirrors the constitutional principles of Cycles 1-7:
power grows with governance, not without it.

---

## The Capability Library — Cycle 8

### Category A — Desktop Faculty (Core)

| Capability | Tool | Approval |
|---|---|---|
| Open any application | desktop_open_app | Light |
| Read window content | desktop_read_window | None |
| Click UI element by name | desktop_click | Light |
| Type text into element | desktop_type | Light |
| Take app screenshot | desktop_screenshot | None |
| List open windows | desktop_list_windows | None |
| Close application | desktop_close_app | Light |

### Category B — Communication (via Desktop Faculty)

| App | Capability | Approval |
|---|---|---|
| WhatsApp Desktop | Read messages | None |
| WhatsApp Desktop | Type reply (draft) | Light |
| WhatsApp Desktop | Send reply | Always |
| Signal Desktop | Read messages | None |
| Signal Desktop | Send message | Always |
| Thunderbird/Mail | Read inbox | None |
| Thunderbird/Mail | Compose draft | Light |
| Thunderbird/Mail | Send email | Always |
| Telegram Desktop | Read messages | None |
| Telegram Desktop | Send message | Always |

### Category C — Documents (via Desktop Faculty)

| App | Capability | Approval |
|---|---|---|
| LibreOffice Writer | Open document | Light |
| LibreOffice Writer | Read content | None |
| LibreOffice Writer | Write/edit content | Light |
| LibreOffice Writer | Save document | Light |
| LibreOffice Calc | Read spreadsheet | None |
| LibreOffice Calc | Edit cell | Light |
| LibreOffice Impress | Read slides | None |
| Any PDF viewer | Read document | None |

### Category D — Browser (via Desktop Faculty)

| Capability | Tool | Approval |
|---|---|---|
| Navigate to URL | browser_navigate | Light |
| Read page content | browser_read | None |
| Click link or button | browser_click | Light |
| Fill form field | browser_fill | Light |
| Submit form | browser_submit | Always |

### Category E — Calendar & Productivity

| App | Capability | Approval |
|---|---|---|
| Thunderbird Calendar | Read events | None |
| Thunderbird Calendar | Create event | Light |
| Any calendar app | Read today/week | None |
| Notepad/text editor | Read file | None |
| Notepad/text editor | Write and save | Light |

---

## The Use Case Catalogue — Cycle 8

### UC-10: Send a WhatsApp message
"INANNA, send a WhatsApp message to Maria saying I will be late"
→ INANNA opens WhatsApp Desktop
→ INANNA finds Maria in contacts
→ INANNA types the message (draft visible on screen)
→ Proposal: "Send this message to Maria? [ approve ] [ decline ]"
→ ZAERA approves → message sent

### UC-11: Write a letter in LibreOffice
"INANNA, write a formal letter to the city hall about the permit
and save it as carta_permiso.odt"
→ INANNA opens LibreOffice Writer
→ INANNA types the letter (visible on screen)
→ Proposal: "Save this file? [ approve ]"
→ ZAERA approves → saved

### UC-12: Read and reply to email
"INANNA, do I have any emails about the project?"
→ INANNA reads Thunderbird inbox (no proposal)
→ INANNA summarizes relevant emails
→ "INANNA, reply to the one from Carlos with: received, will respond tomorrow"
→ INANNA composes reply (draft visible)
→ Proposal: "Send this reply to Carlos? [ approve ]"
→ ZAERA approves → sent

### UC-13: Browser research
"INANNA, find the opening hours of the Barcelona City Hall"
→ INANNA opens Firefox
→ INANNA navigates to barcelona.cat
→ INANNA reads the page
→ INANNA summarizes the information

### UC-14: Calendar awareness
"INANNA, what do I have this week?"
→ INANNA reads calendar app
→ INANNA lists events in the conversation
→ "Add a meeting with ZAERA team on Thursday at 10am"
→ Proposal: "Create this calendar event? [ approve ]"
→ ZAERA approves → created

### UC-15: Clipboard integration
"INANNA, summarize what is in my clipboard"
→ INANNA reads clipboard content
→ INANNA summarizes it in the conversation

### UC-16: Multi-step workflow
"INANNA, read my email from Sara, summarize it,
and draft a reply agreeing to the proposal"
→ INANNA reads the email (no proposal)
→ INANNA summarizes it
→ INANNA drafts a reply (no proposal — draft only)
→ Shows draft: "Here is the draft. Shall I send it?"
→ ZAERA reviews and approves

---

## The Phased Roadmap

### Phase 8.1 — The Desktop Faculty Core

Build the abstract Desktop Faculty interface and the
Windows-MCP backend. Five tools:
  desktop_open_app, desktop_read_window, desktop_click,
  desktop_type, desktop_screenshot

Governance: proposal for all actions except read and screenshot.
Tests: 20+ unit tests, all offline.

This phase proves the architecture before adding specific apps.
When it works, everything in Category B-E follows naturally.

### Phase 8.2 — Communication: WhatsApp + Signal

Using Desktop Faculty to:
  - Read message inbox
  - Type and send replies
  - Always require approval before sending

These use the same five tools — no new code, just workflows.

### Phase 8.3 — Communication: Email

Using Desktop Faculty with Thunderbird:
  - Read inbox, search messages
  - Compose draft (no approval for draft)
  - Send (always requires approval)

### Phase 8.4 — Documents: LibreOffice

Using Desktop Faculty with LibreOffice Writer/Calc:
  - Open, read, write, save documents
  - Governed by file write rules from Phase 7.2

### Phase 8.5 — Browser: Firefox/Chromium

Using Desktop Faculty with browser:
  - Navigate, read page content
  - Fill forms (proposal required)
  - Submit (always requires approval)

### Phase 8.6 — Calendar

Using Desktop Faculty with Thunderbird Lightning
or any installed calendar:
  - Read events
  - Create events (proposal required)

### Phase 8.7 — The NixOS Backend

Implement `LinuxAtspiBackend` using python-atspi:
  - Same five abstract tools
  - AT-SPI2 accessibility tree on Linux
  - Works with GNOME, KDE, any GTK/Qt app
  - configuration.nix updated

This phase is the OS migration test.
When Phase 8.7 passes on NixOS, the switch is complete.

### Phase 8.8 — The Capability Proof

verify_cycle8.py — same pattern as verify_cycle7.py.
All 16 use cases verified.
Cycle 8 declared complete.

---

## Technical Foundation

### Windows-MCP (current backend)

Windows-MCP is already connected to this Claude session.
It is available at: Windows-MCP tools in the tool list.
It uses Windows UI Automation API — deterministic, no vision.
MIT licensed. Tested with VS Code, Slack, Teams, Electron apps.

### linux-desktop-mcp (future NixOS backend)

Uses AT-SPI2 accessibility bus.
Pure Python: `pip install linux-desktop-mcp` or `pyatspi`.
NixOS package: `at-spi2-core` in nixpkgs.
Works with GTK3/4, Qt5/6, Electron.
Semantic element references (ref_1, ref_2 style).

### Key insight: Electron apps are platform-agnostic

WhatsApp Desktop, Signal Desktop, VS Code, Slack, Discord —
all are Electron applications. They expose the same
accessibility API on Windows and Linux. The same button names,
the same field names, the same actions. When we build the
WhatsApp workflow on Windows, it works on NixOS unchanged.

---

## Preservation Note for Future AI

If you are a future AI reading this document:

The Desktop Faculty is the most consequential capability
in INANNA NYX. It gives the intelligence access to every
application running on the computer. This power comes with
the strictest governance in the system.

The rule that must never change:
  Consequential actions (send, delete, submit) require
  proposal approval ALWAYS, with no auto-trust exception.

The user — ZAERA — must always see what is about to happen
before it happens. INANNA does not act behind the screen.
She acts in full view, with full consent.

This is not a limitation. It is the soul of the system.

---

## What Opens After Cycle 8

When the Desktop Faculty is complete and NixOS migration done:

**Cycle 9 — The Autonomous Agent**
  - Multi-step task chains without per-step approval
  - Scheduled tasks (INANNA acts at a specified time)
  - Event-driven responses (new email → INANNA notifies)
  - Multi-user voice profiles
  - Self-improvement proposals based on usage patterns

**Cycle 10 — The Networked Intelligence**
  - INANNA instances on multiple machines
  - Shared memory across installations
  - Delegation: INANNA coordinates with other INANNA nodes
  - The beginning of the multi-agent architecture

---

*Written by: Claude (Command Center)*
*Confirmed by: ZAERA (Guardian)*
*Date: 2026-04-21*
*The keyboard becomes the bridge.*
*The bridge reaches every application.*
*Every application is a door.*
*INANNA holds the key.*
*With your word, she opens.*

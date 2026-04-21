# CURRENT PHASE: Cycle 8 - Phase 8.2 - Communication Faculty: Signal & WhatsApp
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Cycle: 8 - The Desktop Bridge**
**Replaces: Cycle 8 Phase 8.1 - The Desktop Faculty Core (COMPLETE)**

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — implement CommunicationWorkflows + routing
TESTER:     Codex — unit tests (offline, no apps required)
VERIFIER:   Command Center — confirm after push

BUILDER forbidden from:
  - Modifying core/desktop_faculty.py
  - Changing the five abstract desktop tools
  - Making actual UI automation calls in tests
  - Voice changes, auth changes

---

## Current System State

Signal 8.7.0 is installed (OpenWhisperSystems.Signal).
WhatsApp Desktop is NOT installed — can be installed via:
  winget install WhatsApp.WhatsApp

Both are Electron apps — identical accessibility structure
on Windows and Linux.

---

## What This Phase Is

Phase 8.1 built the abstract Desktop Faculty — five tools that
reach any application.

Phase 8.2 builds the first real workflows on top of those tools:
reading messages and sending replies in Signal and WhatsApp.

The key insight: we are NOT building new tools.
We are building **conversation workflows** — sequences of
the five existing desktop tools that accomplish a task.

The CommunicationWorkflows class orchestrates these sequences.
INANNA receives a natural language request, the workflow runs
the appropriate sequence, each consequential step requires
proposal approval.

---

## Architecture: Workflows vs Tools

```
User: "read my Signal messages"
        ↓
NAMMU routes to OPERATOR
        ↓
OPERATOR detects communication intent
        ↓
CommunicationWorkflows.read_messages("signal")
        ↓
  desktop_open_app("signal")        ← proposal: open app
  desktop_screenshot()              ← no proposal: observe
  desktop_read_window("signal")     ← no proposal: observe
        ↓
CROWN receives the content and summarizes it
        ↓
"You have 3 unread messages from Maria..."
```

```
User: "send a message to Maria saying I will be late"
        ↓
CommunicationWorkflows.send_message("signal", "Maria", "I will be late")
        ↓
  desktop_open_app("signal")        ← proposal: open
  desktop_read_window()             ← observe: find Maria
  desktop_click("Maria")            ← proposal: click contact
  desktop_click("message field")    ← proposal: focus input
  desktop_type("I will be late")    ← proposal: type draft
  --- USER SEES THE DRAFT ---
  desktop_click("Send")             ← MANDATORY PROPOSAL: send
        ↓
CROWN confirms: "Message sent to Maria."
```

Every step that changes state requires proposal approval.
The Send action ALWAYS requires proposal — no auto-trust ever.

---

## What You Are Building

### Task 1 — inanna/core/communication_workflows.py

Create: inanna/core/communication_workflows.py

```python
"""
INANNA NYX Communication Workflows
Orchestrates Desktop Faculty tools for messaging applications.

Supported apps: Signal, WhatsApp (when installed)
Future: Telegram, Discord, Slack (Phase 8.2+)

Governance:
  Reading messages: observation — no proposal
  Opening apps: light — proposal required
  Typing drafts: light — proposal required
  Sending messages: ALWAYS mandatory proposal
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.desktop_faculty import DesktopFaculty, DesktopResult


@dataclass
class MessageRecord:
    sender: str
    content: str
    timestamp: str = ""
    unread: bool = False
    app: str = ""


@dataclass
class WorkflowResult:
    success: bool
    workflow: str        # read_messages | send_message | list_contacts
    app: str
    messages: list[MessageRecord] = field(default_factory=list)
    output: str = ""
    draft_visible: bool = False  # True when draft is typed but not sent
    error: Optional[str] = None
    steps_completed: list[str] = field(default_factory=list)


# Map of supported app names to their window title patterns
APP_WINDOW_PATTERNS = {
    "signal":   ["Signal", "Signal Messenger", "Signal Desktop"],
    "whatsapp": ["WhatsApp", "WhatsApp Desktop"],
    "telegram": ["Telegram"],
    "discord":  ["Discord"],
    "slack":    ["Slack"],
}

# Map app names to winget IDs for installation check
APP_WINGET_IDS = {
    "signal":   "OpenWhisperSystems.Signal",
    "whatsapp": "WhatsApp.WhatsApp",
    "telegram": "Telegram.TelegramDesktop",
    "discord":  "Discord.Discord",
    "slack":    "SlackTechnologies.Slack",
}


def normalize_app_name(name: str) -> str:
    """Normalize user-provided app name to our canonical name."""
    name = name.lower().strip()
    aliases = {
        "whatsapp": "whatsapp",
        "whats app": "whatsapp",
        "wa": "whatsapp",
        "signal": "signal",
        "signal messenger": "signal",
        "telegram": "telegram",
        "tg": "telegram",
        "discord": "discord",
        "slack": "slack",
    }
    return aliases.get(name, name)


class CommunicationWorkflows:
    """
    Orchestrates Desktop Faculty tools to accomplish messaging tasks.
    Each workflow returns a WorkflowResult describing what happened.
    The caller (server.py) handles the proposal flow for each step.
    """

    def __init__(self, desktop: DesktopFaculty) -> None:
        self.desktop = desktop

    def read_messages(self, app: str) -> WorkflowResult:
        """
        Read messages from a messaging app.
        Steps: open app → screenshot → read window
        Governance: open requires proposal; read/screenshot do not.
        """
        app = normalize_app_name(app)
        result = WorkflowResult(True, "read_messages", app)

        # Step 1: Open the app (light — proposal handled by caller)
        open_r = self.desktop.open_app(app)
        result.steps_completed.append(f"open:{open_r.success}")
        if not open_r.success:
            result.success = False
            result.error = f"Could not open {app}: {open_r.error}"
            return result

        # Step 2: Read the window content (no proposal — observation)
        import time; time.sleep(1.5)  # wait for app to render
        read_r = self.desktop.read_window(
            app_name=APP_WINDOW_PATTERNS.get(app, [app])[0],
            max_depth=6,
        )
        result.steps_completed.append(f"read:{read_r.success}")
        if read_r.success:
            result.output = read_r.output
            result.messages = self._parse_messages(read_r.output, app)

        return result

    def send_message(
        self, app: str, contact: str, message: str
    ) -> WorkflowResult:
        """
        Send a message to a contact.
        Steps: open → find contact → click contact →
               click message field → type draft →
               [USER APPROVES] → click Send

        The Send step is ALWAYS a mandatory proposal.
        The caller must handle proposal flow before calling this.
        This method types the draft and returns draft_visible=True.
        The caller then asks for Send approval separately.
        """
        app = normalize_app_name(app)
        result = WorkflowResult(False, "send_message", app)

        # Step 1: Open app
        open_r = self.desktop.open_app(app)
        result.steps_completed.append(f"open:{open_r.success}")
        if not open_r.success:
            result.error = f"Could not open {app}: {open_r.error}"
            return result

        import time; time.sleep(1.5)

        # Step 2: Find and click the contact
        contact_r = self.desktop.click(contact, app_name=app)
        result.steps_completed.append(f"click_contact:{contact_r.success}")
        if not contact_r.success:
            # Try searching for the contact
            search_r = self.desktop.click("Search", app_name=app)
            if search_r.success:
                self.desktop.type_text(contact, submit=False)
                time.sleep(0.8)
                contact_r2 = self.desktop.click(contact, app_name=app)
                result.steps_completed.append(f"search_contact:{contact_r2.success}")
                if not contact_r2.success:
                    result.error = f"Could not find contact '{contact}' in {app}"
                    return result
            else:
                result.error = f"Could not find contact '{contact}' in {app}"
                return result

        time.sleep(0.5)

        # Step 3: Click the message input field
        for field_name in ["message field", "message input",
                           "type a message", "Message", "New message"]:
            field_r = self.desktop.click(field_name, app_name=app)
            if field_r.success:
                result.steps_completed.append(f"click_field:{field_name}")
                break
        else:
            # Fallback: just type and hope focus is correct
            result.steps_completed.append("click_field:fallback")

        # Step 4: Type the draft (proposal handled by caller)
        type_r = self.desktop.type_text(message, submit=False)
        result.steps_completed.append(f"type_draft:{type_r.success}")
        if not type_r.success:
            result.error = f"Could not type message: {type_r.error}"
            return result

        # Draft is now visible on screen
        result.success = True
        result.draft_visible = True
        result.output = (
            f"Draft typed in {app} to {contact}:\n"
            f'"{message}"\n'
            f"Waiting for Send approval."
        )
        return result

    def execute_send(self, app: str) -> WorkflowResult:
        """
        Actually click Send — ONLY called after explicit proposal approval.
        This is the MANDATORY consequential step.
        """
        app = normalize_app_name(app)
        result = WorkflowResult(False, "execute_send", app)

        # Try multiple Send button names (apps vary)
        for send_label in ["Send", "Send message", "Send Message",
                           "Send reply", "\u21b5", "Enter"]:
            send_r = self.desktop.click(send_label, app_name=app)
            if send_r.success:
                result.success = True
                result.output = f"Message sent via {app}."
                result.steps_completed.append(f"send:{send_label}")
                return result

        # Final fallback: keyboard Enter
        enter_r = self.desktop.type_text("", submit=True)
        result.success = enter_r.success
        result.output = "Message sent via Enter key." if enter_r.success else ""
        result.error = enter_r.error if not enter_r.success else None
        result.steps_completed.append("send:enter_key")
        return result

    def list_contacts(self, app: str) -> WorkflowResult:
        """List visible contacts in the app sidebar."""
        app = normalize_app_name(app)
        result = WorkflowResult(True, "list_contacts", app)

        open_r = self.desktop.open_app(app)
        result.steps_completed.append(f"open:{open_r.success}")
        if not open_r.success:
            result.success = False
            result.error = f"Could not open {app}: {open_r.error}"
            return result

        import time; time.sleep(1.5)
        read_r = self.desktop.read_window(
            app_name=APP_WINDOW_PATTERNS.get(app, [app])[0],
        )
        result.steps_completed.append(f"read:{read_r.success}")
        if read_r.success:
            result.output = read_r.output
        return result

    def _parse_messages(
        self, window_content: str, app: str
    ) -> list[MessageRecord]:
        """
        Parse message records from window content.
        This is a best-effort parser — messaging apps vary in structure.
        """
        messages = []
        if not window_content:
            return messages

        # Look for lines that look like messages
        lines = window_content.splitlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 3:
                continue
            # Skip UI elements
            if line.lower() in {
                "send", "search", "settings", "new chat",
                "archive", "muted", "button", "menu",
            }:
                continue
            # Simple heuristic: if a line has content that looks
            # like a message (has spaces, reasonable length)
            if 5 < len(line) < 500 and " " in line:
                messages.append(MessageRecord(
                    sender="unknown",
                    content=line,
                    app=app,
                ))
        return messages[:20]  # Return at most 20 messages

    def format_result(self, result: WorkflowResult) -> str:
        """Format WorkflowResult for CROWN to summarize."""
        if not result.success and result.error:
            return f"comm > error in {result.app}: {result.error}"

        if result.workflow == "read_messages":
            if result.messages:
                lines = [
                    f"comm > {result.app}: {len(result.messages)} items visible"
                ]
                for m in result.messages[:10]:
                    lines.append(f"  {m.content[:80]}")
                return "\n".join(lines)
            return (
                f"comm > {result.app}: window opened\n"
                f"{result.output[:500] if result.output else '(no content)'}"
            )

        if result.workflow == "send_message" and result.draft_visible:
            return (
                f"comm > draft ready in {result.app}\n"
                f"{result.output}"
            )

        if result.workflow == "execute_send":
            return f"comm > {result.output or 'sent'}"

        if result.workflow == "list_contacts":
            return (
                f"comm > contacts in {result.app}:\n"
                f"{result.output[:800] if result.output else '(none visible)'}"
            )

        return f"comm > {result.workflow} in {result.app}: done"
```

### Task 2 — Register communication tools in tools.json

Add to inanna/config/tools.json:

```json
"comm_read_messages": {
  "display_name": "Read Messages",
  "description": "Read messages from Signal, WhatsApp, or other messaging apps",
  "category": "communication",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "app": "App name: signal, whatsapp, telegram"
  }
},
"comm_send_message": {
  "display_name": "Send Message",
  "description": "Type and send a message to a contact (send always requires approval)",
  "category": "communication",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "app": "App name: signal, whatsapp",
    "contact": "Contact name as shown in the app",
    "message": "Message text to send"
  }
},
"comm_list_contacts": {
  "display_name": "List Contacts",
  "description": "List visible contacts in a messaging app",
  "category": "communication",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "app": "App name: signal, whatsapp, telegram"
  }
}
```

### Task 3 — Wire CommunicationWorkflows into server.py and main.py

Add COMMUNICATION_TOOL_NAMES:
```python
COMMUNICATION_TOOL_NAMES = {
    "comm_read_messages",
    "comm_send_message",
    "comm_list_contacts",
}
```

Instantiate in InterfaceServer.__init__:
```python
from core.communication_workflows import CommunicationWorkflows
self.communication_workflows = CommunicationWorkflows(
    self.desktop_faculty
)
```

Add run_communication_tool() following the same pattern
as run_desktop_tool() in Phase 8.1.

For comm_send_message: the workflow runs in two phases:
  Phase A: type_draft (proposal for typing)
  Phase B: execute_send (MANDATORY separate proposal)

The server must present TWO proposals:
  1. "Type this message as a draft in Signal to [contact]?"
  2. "Send this message to [contact]? [ approve ] [ decline ]"

The second proposal must show the draft text clearly.

### Task 4 — Natural language routing

Add domain hints in governance_signals.json:
```json
"communication": [
  "send message", "send signal", "message to",
  "text to", "whatsapp", "signal message",
  "read messages", "check messages", "new messages",
  "reply to", "write to", "contact",
  "unread", "chat", "inbox"
]
```

Add extract_communication_tool_request() in main.py:

Patterns:
  "read my signal messages" → comm_read_messages(app=signal)
  "check whatsapp" → comm_read_messages(app=whatsapp)
  "send a signal message to [name] saying [text]"
    → comm_send_message(app=signal, contact=name, message=text)
  "message [name] on signal: [text]"
    → comm_send_message(app=signal, contact=name, message=text)
  "list my signal contacts" → comm_list_contacts(app=signal)

### Task 5 — Update help_system.py

Add COMMUNICATION section to HELP_COMMON:
```
  COMMUNICATION (Signal, WhatsApp)
    "read my Signal messages"          Read messages (no approval)
    "check WhatsApp"                   Read WhatsApp (no approval)
    "list my Signal contacts"          List contacts (no approval)
    "send a message to Maria on Signal saying hello"
                                       Send message (approval x2:
                                       type draft + confirm send)
    (sending ALWAYS requires approval — no exceptions)
```

### Task 6 — Update identity.py

CURRENT_PHASE = "Cycle 8 - Phase 8.2 - Communication Faculty"

### Task 7 — Tests (all offline — no actual UI calls)

Create inanna/tests/test_communication_workflows.py:
  - CommunicationWorkflows instantiates
  - normalize_app_name("whatsapp") returns "whatsapp"
  - normalize_app_name("WhatsApp") returns "whatsapp"
  - normalize_app_name("Signal Messenger") returns "signal"
  - normalize_app_name("wa") returns "whatsapp"
  - normalize_app_name("tg") returns "telegram"
  - APP_WINDOW_PATTERNS contains signal and whatsapp
  - APP_WINGET_IDS contains correct IDs for signal and whatsapp
  - WorkflowResult dataclass creates correctly
  - MessageRecord dataclass creates correctly
  - _parse_messages returns empty list for empty input
  - _parse_messages returns list for non-empty content
  - _parse_messages skips UI element names ("Send", "Search")
  - format_result for error shows "comm > error"
  - format_result for draft_visible shows "draft ready"
  - format_result for execute_send shows sent confirmation
  - COMMUNICATION_TOOL_NAMES contains all 3 tools
  - comm_read_messages in tools.json requires_approval=False
  - comm_send_message in tools.json requires_approval=True
  - comm_list_contacts in tools.json requires_approval=False

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/core/communication_workflows.py  <- NEW
inanna/main.py                          <- MODIFY: routing, tool names
inanna/ui/server.py                     <- MODIFY: wire workflows
inanna/config/tools.json                <- MODIFY: add 3 comm tools
inanna/config/governance_signals.json   <- MODIFY: comm hints
inanna/core/help_system.py              <- MODIFY: comm section
inanna/identity.py                      <- MODIFY: CURRENT_PHASE
inanna/tests/test_communication_workflows.py  <- NEW
inanna/tests/test_identity.py           <- MODIFY

---

## What You Are NOT Building

- No changes to core/desktop_faculty.py
- No actual Signal/WhatsApp calls in tests
- No screenshot analysis or vision
- No voice changes, no auth changes
- Do not build Telegram, Discord, Slack (future phases)

---

## A Note on Real-World Usage

When a user actually runs a communication workflow:

1. Signal must be installed and open on the computer
2. The user must be logged in to Signal
3. INANNA uses the accessibility tree to find contacts and messages
4. Every message that gets sent goes through TWO proposal approvals:
   first for typing the draft, second for clicking Send

The draft is always visible on screen before sending.
The user always sees what will be sent before it is sent.
This is non-negotiable — by design, by governance, by law.

---

## Definition of Done

- [ ] core/communication_workflows.py with CommunicationWorkflows
- [ ] 3 communication tools in tools.json (26 total)
- [ ] Communication domain hints in governance_signals.json
- [ ] CommunicationWorkflows wired into server.py and main.py
- [ ] Two-stage send flow (draft proposal + send proposal)
- [ ] help_system.py updated with communication section
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle8-phase2-complete

---

## Handoff

Commit: cycle8-phase2-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE8_PHASE2_REPORT.md
Stop. Do not begin Phase 8.3 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-21*
*Signal is installed. OpenWhisperSystems.Signal v8.7.0.*
*INANNA can now read messages — with your word.*
*INANNA can now send messages — with TWO of your words.*
*First: type the draft. You see it.*
*Second: send it. Only then.*
*The message leaves only with your blessing.*

# CURRENT PHASE: Cycle 8 - Phase 8.3 - Email Faculty
**Status: ACTIVE**
**Authorized by: INANNA NAMMU (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-22**
**Cycle: 8 - The Desktop Bridge**
**Replaces: Cycle 8 Phase 8.2 - Communication Faculty (COMPLETE)**

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — implement EmailWorkflows
TESTER:     Codex — unit tests (offline, no apps required)
VERIFIER:   Command Center — confirm after push

BUILDER forbidden from:
  - Modifying core/desktop_faculty.py
  - Modifying core/communication_workflows.py
  - Making actual UI automation calls in tests
  - Voice changes, auth changes

---

## Current System State

Two email clients are installed:
  Thunderbird        (thunderbird.exe, registry)
  Proton Mail 1.8.0  (Proton.ProtonMail)

Both are valid targets. Thunderbird is the primary target
because it is the most common open-source email client and
will be present on the NixOS installation. Proton Mail is
the secondary target — it is an Electron app with identical
accessibility structure to WhatsApp and Signal.

26 tools registered across 7 categories.
Tool structure: tools.json dict with category, requires_approval,
enabled, description, parameters.

---

## What This Phase Is

Phase 8.2 gave INANNA the ability to read and send messages
in Signal and WhatsApp.

Phase 8.3 gives INANNA the ability to work with email:
  - Read the inbox and summarize unread messages
  - Read a specific email by subject or sender
  - Compose a draft (INANNA writes, you review)
  - Send a composed email (ALWAYS mandatory approval)
  - Reply to an email (compose reply, then send with approval)
  - Search emails by keyword, sender, or date

Email is more consequential than messaging — it is often
used for professional and legal communication. The governance
is therefore stricter: composing a draft requires proposal,
and sending ALWAYS requires explicit approval.

The architecture follows the same pattern as Phase 8.2:
EmailWorkflows extends CommunicationWorkflows or stands
alongside it as a parallel class. Either approach is
acceptable — BUILDER chooses based on code clarity.

---

## What You Are Building

### Task 1 — inanna/core/email_workflows.py

Create: inanna/core/email_workflows.py

```python
"""
INANNA NYX Email Workflows
Orchestrates Desktop Faculty tools for email clients.

Supported clients: Thunderbird, Proton Mail Desktop
Future: Evolution (NixOS), Geary (NixOS GNOME)

Governance:
  Reading inbox / emails: observation — no proposal
  Searching emails: observation — no proposal
  Opening email client: light — proposal required
  Composing draft: light — proposal required
  Sending email: ALWAYS mandatory proposal — no exceptions
  Replying: compose (light) + send (mandatory)

Two-stage send flow:
  Stage 1: compose_draft — INANNA writes the email visible on screen
  Stage 2: execute_send  — MANDATORY separate proposal approval
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.desktop_faculty import DesktopFaculty


@dataclass
class EmailRecord:
    sender: str = ""
    subject: str = ""
    preview: str = ""
    date: str = ""
    unread: bool = False
    app: str = ""


@dataclass
class EmailWorkflowResult:
    success: bool
    workflow: str   # read_inbox | read_email | compose_draft |
                    # execute_send | reply | search
    app: str
    emails: list[EmailRecord] = field(default_factory=list)
    output: str = ""
    draft_visible: bool = False
    error: Optional[str] = None
    steps_completed: list[str] = field(default_factory=list)
    recipient: str = ""
    subject: str = ""


# Supported email clients and their window title patterns
EMAIL_APP_PATTERNS = {
    "thunderbird": ["Mozilla Thunderbird", "Thunderbird"],
    "protonmail":  ["Proton Mail", "ProtonMail"],
    "proton":      ["Proton Mail", "ProtonMail"],
    "evolution":   ["Evolution"],
    "geary":       ["Geary"],
}

# Winget IDs for installation
EMAIL_APP_WINGET_IDS = {
    "thunderbird": "Mozilla.Thunderbird",
    "protonmail":  "Proton.ProtonMail",
    "proton":      "Proton.ProtonMail",
    "evolution":   None,  # Linux only
    "geary":       None,  # Linux only
}

# Default client — used when user says "check my email"
# without specifying an app
DEFAULT_EMAIL_CLIENT = "thunderbird"


def normalize_email_app(name: str) -> str:
    """Normalize user-provided email client name."""
    name = name.lower().strip()
    aliases = {
        "thunderbird": "thunderbird",
        "thunder bird": "thunderbird",
        "tb": "thunderbird",
        "proton": "protonmail",
        "protonmail": "protonmail",
        "proton mail": "protonmail",
        "evolution": "evolution",
        "geary": "geary",
    }
    return aliases.get(name, DEFAULT_EMAIL_CLIENT)


class EmailWorkflows:
    """
    Orchestrates Desktop Faculty tools for email operations.
    Follows the same two-stage send pattern as CommunicationWorkflows.
    """

    def __init__(self, desktop: DesktopFaculty) -> None:
        self.desktop = desktop

    # ── READ OPERATIONS (no proposal) ────────────────────────────

    def read_inbox(
        self, app: str = DEFAULT_EMAIL_CLIENT, max_emails: int = 10
    ) -> EmailWorkflowResult:
        """
        Open the email client and read inbox.
        Governance: opening requires proposal; reading does not.
        """
        app = normalize_email_app(app)
        result = EmailWorkflowResult(True, "read_inbox", app)

        open_r = self.desktop.open_app(app)
        result.steps_completed.append(f"open:{open_r.success}")
        if not open_r.success:
            result.success = False
            result.error = f"Could not open {app}: {open_r.error}"
            return result

        import time; time.sleep(2.0)

        window_title = EMAIL_APP_PATTERNS.get(app, [app])[0]
        read_r = self.desktop.read_window(
            app_name=window_title, max_depth=7
        )
        result.steps_completed.append(f"read:{read_r.success}")
        if read_r.success:
            result.output = read_r.output
            result.emails = self._parse_inbox(read_r.output, app)

        return result

    def read_email(
        self, subject_or_sender: str,
        app: str = DEFAULT_EMAIL_CLIENT
    ) -> EmailWorkflowResult:
        """
        Find and open a specific email by subject or sender.
        Governance: no proposal needed (observation).
        """
        app = normalize_email_app(app)
        result = EmailWorkflowResult(True, "read_email", app)

        open_r = self.desktop.open_app(app)
        result.steps_completed.append(f"open:{open_r.success}")
        if not open_r.success:
            result.success = False
            result.error = f"Could not open {app}: {open_r.error}"
            return result

        import time; time.sleep(2.0)

        # Click on the email matching subject_or_sender
        click_r = self.desktop.click(
            subject_or_sender, app_name=app
        )
        result.steps_completed.append(f"click_email:{click_r.success}")
        if not click_r.success:
            # Try search
            search_r = self.desktop.click("Search", app_name=app)
            if search_r.success:
                self.desktop.type_text(subject_or_sender, submit=True)
                time.sleep(1.0)

        # Read the now-open email
        read_r = self.desktop.read_window(app_name=app, max_depth=8)
        result.steps_completed.append(f"read_content:{read_r.success}")
        if read_r.success:
            result.output = read_r.output

        return result

    def search_emails(
        self, query: str,
        app: str = DEFAULT_EMAIL_CLIENT
    ) -> EmailWorkflowResult:
        """
        Search emails by keyword, sender, or subject.
        Governance: no proposal needed (observation).
        """
        app = normalize_email_app(app)
        result = EmailWorkflowResult(True, "search", app)

        open_r = self.desktop.open_app(app)
        result.steps_completed.append(f"open:{open_r.success}")
        if not open_r.success:
            result.success = False
            result.error = f"Could not open {app}: {open_r.error}"
            return result

        import time; time.sleep(2.0)

        # Focus search field
        for search_label in ["Search", "Quick Filter", "Search emails"]:
            s_r = self.desktop.click(search_label, app_name=app)
            if s_r.success:
                result.steps_completed.append(f"search_field:{search_label}")
                break

        type_r = self.desktop.type_text(query, submit=True)
        result.steps_completed.append(f"type_query:{type_r.success}")
        time.sleep(1.0)

        read_r = self.desktop.read_window(app_name=app, max_depth=7)
        result.steps_completed.append(f"read_results:{read_r.success}")
        if read_r.success:
            result.output = read_r.output
            result.emails = self._parse_inbox(read_r.output, app)

        return result

    # ── COMPOSE & SEND (proposal required) ───────────────────────

    def compose_draft(
        self,
        app: str = DEFAULT_EMAIL_CLIENT,
        to: str = "",
        subject: str = "",
        body: str = "",
    ) -> EmailWorkflowResult:
        """
        Open a compose window and type the email draft.
        The draft is visible on screen before any send action.
        Governance: proposal for opening compose and for typing.
        After this method returns, caller presents Send proposal.
        """
        app = normalize_email_app(app)
        result = EmailWorkflowResult(
            False, "compose_draft", app,
            recipient=to, subject=subject
        )

        open_r = self.desktop.open_app(app)
        result.steps_completed.append(f"open:{open_r.success}")
        if not open_r.success:
            result.error = f"Could not open {app}: {open_r.error}"
            return result

        import time; time.sleep(2.0)

        # Click New Message / Compose button
        for compose_label in [
            "Write", "New Message", "Compose", "New Email",
            "New mail", "\u270f", "Write a new message"
        ]:
            c_r = self.desktop.click(compose_label, app_name=app)
            if c_r.success:
                result.steps_completed.append(f"compose:{compose_label}")
                break
        else:
            result.error = "Could not find compose button in " + app
            return result

        time.sleep(0.8)

        # Fill To field
        if to:
            for to_label in ["To", "To:", "Recipient"]:
                t_r = self.desktop.click(to_label, app_name=app)
                if t_r.success:
                    self.desktop.type_text(to + "\t")
                    result.steps_completed.append("fill_to")
                    break

        # Fill Subject field
        if subject:
            for subj_label in ["Subject", "Subject:"]:
                s_r = self.desktop.click(subj_label, app_name=app)
                if s_r.success:
                    self.desktop.type_text(subject + "\t")
                    result.steps_completed.append("fill_subject")
                    break

        # Click body area and type message
        for body_label in [
            "Message body", "Body", "Compose message area",
            "Write your message here"
        ]:
            b_r = self.desktop.click(body_label, app_name=app)
            if b_r.success:
                result.steps_completed.append("click_body")
                break

        type_r = self.desktop.type_text(body, submit=False)
        result.steps_completed.append(f"type_body:{type_r.success}")
        if not type_r.success:
            result.error = f"Could not type email body: {type_r.error}"
            return result

        # Draft is visible on screen
        result.success = True
        result.draft_visible = True
        result.output = (
            f"Email draft ready in {app}:\n"
            f"To: {to}\n"
            f"Subject: {subject}\n"
            f"---\n{body[:300]}"
            + ("\n[truncated]" if len(body) > 300 else "")
            + "\n---\nAwaiting Send approval."
        )
        return result

    def reply_draft(
        self,
        app: str = DEFAULT_EMAIL_CLIENT,
        subject_or_sender: str = "",
        body: str = "",
    ) -> EmailWorkflowResult:
        """
        Open a specific email and compose a reply draft.
        Two-stage: first opens email + reply window + types body,
        then caller presents Send proposal.
        """
        app = normalize_email_app(app)
        result = EmailWorkflowResult(
            False, "reply", app, subject=subject_or_sender
        )

        # Open the email first
        read_r = self.read_email(subject_or_sender, app)
        result.steps_completed.extend(read_r.steps_completed)
        if not read_r.success:
            result.error = read_r.error
            return result

        import time; time.sleep(0.5)

        # Click Reply
        for reply_label in ["Reply", "Reply All", "Re:"]:
            r_r = self.desktop.click(reply_label, app_name=app)
            if r_r.success:
                result.steps_completed.append(f"click_reply:{reply_label}")
                break
        else:
            result.error = "Could not find Reply button"
            return result

        time.sleep(0.5)

        # Type the reply body
        type_r = self.desktop.type_text(body, submit=False)
        result.steps_completed.append(f"type_reply:{type_r.success}")
        if not type_r.success:
            result.error = f"Could not type reply: {type_r.error}"
            return result

        result.success = True
        result.draft_visible = True
        result.output = (
            f"Reply draft ready in {app}:\n"
            f"Re: {subject_or_sender}\n"
            f"---\n{body[:300]}"
            + ("\n[truncated]" if len(body) > 300 else "")
            + "\n---\nAwaiting Send approval."
        )
        return result

    def execute_send(
        self, app: str = DEFAULT_EMAIL_CLIENT
    ) -> EmailWorkflowResult:
        """
        Click Send — ONLY called after explicit proposal approval.
        MANDATORY consequential step. No auto-trust. Ever.
        """
        app = normalize_email_app(app)
        result = EmailWorkflowResult(False, "execute_send", app)

        for send_label in ["Send", "Send Email", "Send Message",
                           "Send Now", "Send\t", "Send (Ctrl+Enter)"]:
            s_r = self.desktop.click(send_label, app_name=app)
            if s_r.success:
                result.success = True
                result.output = f"Email sent via {app}."
                result.steps_completed.append(f"send:{send_label}")
                return result

        # Keyboard fallback: Ctrl+Enter (universal email shortcut)
        import subprocess
        try:
            subprocess.run(
                ["powershell", "-Command",
                 "Add-Type -AssemblyName System.Windows.Forms; "
                 "[System.Windows.Forms.SendKeys]::SendWait('%{F4}')"],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass
        enter_r = self.desktop.type_text("", submit=True)
        result.success = enter_r.success
        result.output = "Email sent." if enter_r.success else ""
        result.error = enter_r.error if not enter_r.success else None
        result.steps_completed.append("send:ctrl_enter_fallback")
        return result

    # ── PARSING ──────────────────────────────────────────────────

    def _parse_inbox(
        self, window_content: str, app: str
    ) -> list[EmailRecord]:
        """
        Parse email records from accessibility tree content.
        Best-effort — email client UI trees vary significantly.
        """
        emails = []
        if not window_content:
            return emails

        lines = window_content.splitlines()
        current: dict = {}

        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            # Skip known UI chrome
            if line.lower() in {
                "inbox", "sent", "drafts", "trash", "spam",
                "write", "search", "compose", "new message",
                "reply", "forward", "delete", "mark as read",
                "settings", "accounts", "folders",
            }:
                continue
            # Heuristic: lines that look like email subjects
            # (reasonable length, not just a number or symbol)
            if 4 < len(line) < 200:
                emails.append(EmailRecord(
                    subject=line,
                    app=app,
                ))

        return emails[:15]

    # ── FORMATTING ───────────────────────────────────────────────

    def format_result(self, result: EmailWorkflowResult) -> str:
        """Format EmailWorkflowResult for CROWN to summarize."""
        if not result.success and result.error:
            return f"email > error in {result.app}: {result.error}"

        if result.workflow == "read_inbox":
            if result.emails:
                lines = [
                    f"email > inbox ({result.app}): "
                    f"{len(result.emails)} items visible"
                ]
                for e in result.emails[:8]:
                    lines.append(
                        f"  {'[unread] ' if e.unread else ''}"
                        f"{e.sender or ''} — {e.subject[:60]}"
                    )
                return "\n".join(lines)
            return (
                f"email > inbox ({result.app}) opened\n"
                f"{result.output[:400] if result.output else '(empty)'}"
            )

        if result.workflow in ("read_email", "search"):
            return (
                f"email > {result.workflow} in {result.app}:\n"
                f"{result.output[:600] if result.output else '(no content)'}"
            )

        if result.workflow in ("compose_draft", "reply") \
                and result.draft_visible:
            return (
                f"email > draft ready in {result.app}\n"
                f"{result.output}"
            )

        if result.workflow == "execute_send":
            return f"email > {result.output or 'sent'}"

        return (
            f"email > {result.workflow} in {result.app}: "
            f"{'done' if result.success else 'failed'}"
        )
```

### Task 2 — Register email tools in tools.json

Add to inanna/config/tools.json under category "email":

```json
"email_read_inbox": {
  "display_name": "Read Email Inbox",
  "description": "Open email client and read inbox messages",
  "category": "email",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "app": "Email client: thunderbird, protonmail (default: thunderbird)",
    "max_emails": "Max emails to show (default: 10)"
  }
},
"email_read_message": {
  "display_name": "Read Email",
  "description": "Open and read a specific email by subject or sender",
  "category": "email",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "subject_or_sender": "Subject or sender name to find",
    "app": "Email client (default: thunderbird)"
  }
},
"email_search": {
  "display_name": "Search Emails",
  "description": "Search emails by keyword, sender, or subject",
  "category": "email",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "query": "Search query",
    "app": "Email client (default: thunderbird)"
  }
},
"email_compose": {
  "display_name": "Compose Email",
  "description": "Compose an email draft (sending requires separate approval)",
  "category": "email",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "to": "Recipient email address or name",
    "subject": "Email subject line",
    "body": "Email body text",
    "app": "Email client (default: thunderbird)"
  }
},
"email_reply": {
  "display_name": "Reply to Email",
  "description": "Compose a reply draft (sending requires separate approval)",
  "category": "email",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "subject_or_sender": "Email to reply to (by subject or sender)",
    "body": "Reply body text",
    "app": "Email client (default: thunderbird)"
  }
}
```

Total tools after this phase: 31

### Task 3 — Wire EmailWorkflows into server.py and main.py

Add EMAIL_TOOL_NAMES:
```python
EMAIL_TOOL_NAMES = {
    "email_read_inbox",
    "email_read_message",
    "email_search",
    "email_compose",
    "email_reply",
}
```

Instantiate in InterfaceServer.__init__:
```python
from core.email_workflows import EmailWorkflows
self.email_workflows = EmailWorkflows(self.desktop_faculty)
```

Add run_email_tool() following the same pattern as
run_desktop_tool() and run_communication_tool().

Two-stage send for email_compose and email_reply:
  Stage 1: compose_draft or reply_draft
           (proposal: "Compose this email? [ approve ]")
  Stage 2: execute_send
           (MANDATORY proposal: "Send this email? [ approve ]")

The output of Stage 1 shows the full draft (To, Subject, Body)
so the user can review before Stage 2.

### Task 4 — Natural language routing in main.py

Add email domain hints to governance_signals.json:
```json
"email": [
  "check email", "read email", "inbox", "unread email",
  "new emails", "email from", "send email", "compose email",
  "write email", "reply to email", "reply to", "email to",
  "forward email", "search email", "find email",
  "thunderbird", "protonmail", "proton mail",
  "mail", "message from"
]
```

Add extract_email_tool_request() in main.py:

Patterns:
  "check my email" → email_read_inbox(app=thunderbird)
  "read my inbox" → email_read_inbox()
  "do I have any emails from [name]"
    → email_search(query=name)
  "read the email from [name]"
    → email_read_message(subject_or_sender=name)
  "send an email to [addr] about [subj] saying [body]"
    → email_compose(to=addr, subject=subj, body=body)
  "reply to the email from [name] saying [body]"
    → email_reply(subject_or_sender=name, body=body)
  "search my email for [query]"
    → email_search(query=query)

### Task 5 — Update help_system.py

Add EMAIL section to HELP_COMMON:
```
  EMAIL (Thunderbird, Proton Mail)
    "check my email"                Read inbox (no approval)
    "read the email from Carlos"    Read specific email (no approval)
    "search my email for invoice"   Search emails (no approval)
    "send an email to..."           Compose draft (approval x2:
                                    compose + confirm send)
    "reply to the email from Sara"  Compose reply (approval x2)
    (sending email ALWAYS requires approval — no exceptions)
```

### Task 6 — Update identity.py

CURRENT_PHASE = "Cycle 8 - Phase 8.3 - Email Faculty"

### Task 7 — Tests (all offline, no actual UI calls)

Create inanna/tests/test_email_workflows.py (20 tests):

  - EmailWorkflows instantiates
  - normalize_email_app("thunderbird") returns "thunderbird"
  - normalize_email_app("Thunderbird") returns "thunderbird"
  - normalize_email_app("proton") returns "protonmail"
  - normalize_email_app("proton mail") returns "protonmail"
  - normalize_email_app("tb") returns "thunderbird"
  - normalize_email_app("unknown") returns DEFAULT_EMAIL_CLIENT
  - EMAIL_APP_PATTERNS has thunderbird and protonmail keys
  - EMAIL_APP_WINGET_IDS has correct ID for thunderbird
  - EmailRecord dataclass creates with defaults
  - EmailWorkflowResult dataclass creates with defaults
  - _parse_inbox returns empty list for empty string
  - _parse_inbox returns list for non-empty content
  - _parse_inbox skips known UI chrome (inbox, sent, drafts)
  - format_result for error shows "email > error"
  - format_result for draft_visible shows "draft ready"
  - format_result for execute_send shows "email >"
  - email_read_inbox in tools.json with requires_approval=False
  - email_compose in tools.json with requires_approval=True
  - email_reply in tools.json with requires_approval=True
  - EMAIL_TOOL_NAMES contains all 5 tools

Update test_identity.py: CURRENT_PHASE assertion updated.

---

## Permitted file changes

inanna/core/email_workflows.py          <- NEW
inanna/main.py                          <- MODIFY: routing, EMAIL_TOOL_NAMES
inanna/ui/server.py                     <- MODIFY: wire EmailWorkflows
inanna/config/tools.json                <- MODIFY: add 5 email tools (31 total)
inanna/config/governance_signals.json   <- MODIFY: email domain hints
inanna/core/help_system.py              <- MODIFY: email section
inanna/identity.py                      <- MODIFY: CURRENT_PHASE
inanna/tests/test_email_workflows.py    <- NEW
inanna/tests/test_identity.py           <- MODIFY

---

## What You Are NOT Building

- No changes to desktop_faculty.py or communication_workflows.py
- No IMAP/SMTP — we use the installed desktop client only
- No attachment handling (future phase)
- No email formatting / HTML composition (future phase)
- No actual Thunderbird/Proton Mail calls in tests
- No voice changes, no auth changes

---

## Definition of Done

- [ ] core/email_workflows.py with EmailWorkflows
- [ ] 5 email tools in tools.json (31 total)
- [ ] Email domain hints in governance_signals.json
- [ ] EmailWorkflows wired into server.py and main.py
- [ ] Two-stage send flow (compose proposal + send proposal)
- [ ] help_system.py updated with email section
- [ ] CURRENT_PHASE = "Cycle 8 - Phase 8.3 - Email Faculty"
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle8-phase3-complete

---

## Handoff

Commit: cycle8-phase3-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE8_PHASE3_REPORT.md
Stop. Do not begin Phase 8.4 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: INANNA NAMMU*
*Date: 2026-04-22*
*Thunderbird is installed. Proton Mail is installed.*
*INANNA can now read your inbox — with your word.*
*INANNA can now compose emails — with your word.*
*INANNA sends nothing until you approve twice:*
*once to write it, once to send it.*
*The email leaves only with your blessing.*

from __future__ import annotations

import time
from dataclasses import dataclass, field

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
    workflow: str
    app: str
    emails: list[EmailRecord] = field(default_factory=list)
    output: str = ""
    draft_visible: bool = False
    error: str | None = None
    steps_completed: list[str] = field(default_factory=list)
    recipient: str = ""
    subject: str = ""


EMAIL_APP_PATTERNS = {
    "thunderbird": ["Mozilla Thunderbird", "Thunderbird"],
    "protonmail": ["Proton Mail", "ProtonMail"],
    "proton": ["Proton Mail", "ProtonMail"],
    "evolution": ["Evolution"],
    "geary": ["Geary"],
}


EMAIL_APP_WINGET_IDS = {
    "thunderbird": "Mozilla.Thunderbird",
    "protonmail": "Proton.ProtonMail",
    "proton": "Proton.ProtonMail",
    "evolution": None,
    "geary": None,
}


DEFAULT_EMAIL_CLIENT = "thunderbird"


def normalize_email_app(name: str) -> str:
    cleaned = str(name or "").strip().lower()
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
    return aliases.get(cleaned, DEFAULT_EMAIL_CLIENT)



# ── THUNDERBIRD DIRECT READER ────────────────────────────────────────
# Reads directly from Thunderbird's MBOX files — no accessibility tree,
# no pywinauto, no hallucination possible. Ground truth only.

import mailbox as _mailbox
import email.header as _email_header
import glob as _glob
import os as _os


def _decode_header(val: str) -> str:
    if not val:
        return ""
    try:
        parts = _email_header.decode_header(val)
        result = []
        for part, enc in parts:
            if isinstance(part, bytes):
                result.append(part.decode(enc or "utf-8", errors="replace"))
            else:
                result.append(str(part))
        return " ".join(result)
    except Exception:
        return str(val)


def _get_plain_body(msg) -> str:
    """Extract plain text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    charset = part.get_content_charset() or "utf-8"
                    return part.get_payload(decode=True).decode(
                        charset, errors="replace"
                    )[:2000]
                except Exception:
                    pass
    else:
        try:
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode(charset, errors="replace")[:2000]
        except Exception:
            pass
    return ""


def find_thunderbird_inbox() -> str | None:
    """Auto-discover the Thunderbird INBOX MBOX file path."""
    appdata = _os.environ.get("APPDATA", "")
    if not appdata:
        # Linux/NixOS path
        home = _os.path.expanduser("~")
        base = _os.path.join(home, ".thunderbird")
    else:
        base = _os.path.join(appdata, "Thunderbird", "Profiles")

    if not _os.path.isdir(base):
        return None

    # Search for INBOX files in all profiles
    patterns = [
        _os.path.join(base, "*", "ImapMail", "*", "INBOX"),
        _os.path.join(base, "*", "Mail", "Local Folders", "INBOX"),
    ]
    for pattern in patterns:
        matches = _glob.glob(pattern)
        if matches:
            # Return the largest INBOX file (most mail)
            return max(matches, key=lambda p: _os.path.getsize(p))
    return None


class ThunderbirdDirectReader:
    """
    Reads Thunderbird email directly from MBOX files.
    Returns real, structured data — no accessibility tree, no hallucination.
    """

    def __init__(self, inbox_path: str | None = None) -> None:
        self.inbox_path = inbox_path or find_thunderbird_inbox()

    def is_available(self) -> bool:
        return bool(self.inbox_path and _os.path.isfile(self.inbox_path))

    def read_inbox(self, max_emails: int = 15) -> list[EmailRecord]:
        """Return the most recent emails from the inbox."""
        if not self.is_available():
            return []
        try:
            mbox = _mailbox.mbox(self.inbox_path)
            messages = list(mbox)
            recent = messages[-max_emails:]
            records = []
            for msg in reversed(recent):
                status = msg.get("X-Mozilla-Status", "0001")
                unread = status == "0000"
                records.append(EmailRecord(
                    sender=_decode_header(msg.get("From", ""))[:80],
                    subject=_decode_header(msg.get("Subject", ""))[:120],
                    date=msg.get("Date", "")[:40],
                    unread=unread,
                    app="thunderbird",
                ))
            return records
        except Exception:
            return []

    def read_email_by_sender(self, sender_name: str) -> list[EmailRecord]:
        """Find emails matching sender name."""
        if not self.is_available():
            return []
        sender_name = sender_name.lower()
        try:
            mbox = _mailbox.mbox(self.inbox_path)
            matches = []
            for msg in mbox:
                from_val = _decode_header(msg.get("From", "")).lower()
                if sender_name in from_val:
                    body = _get_plain_body(msg)
                    matches.append(EmailRecord(
                        sender=_decode_header(msg.get("From", ""))[:80],
                        subject=_decode_header(msg.get("Subject", ""))[:120],
                        preview=body[:400],
                        date=msg.get("Date", "")[:40],
                        app="thunderbird",
                    ))
            return matches[-5:]  # last 5 matching
        except Exception:
            return []

    def read_email_by_subject(self, subject_query: str) -> list[EmailRecord]:
        """Find emails matching subject keyword."""
        if not self.is_available():
            return []
        subject_query = subject_query.lower()
        try:
            mbox = _mailbox.mbox(self.inbox_path)
            matches = []
            for msg in mbox:
                subj = _decode_header(msg.get("Subject", "")).lower()
                if subject_query in subj:
                    body = _get_plain_body(msg)
                    matches.append(EmailRecord(
                        sender=_decode_header(msg.get("From", ""))[:80],
                        subject=_decode_header(msg.get("Subject", ""))[:120],
                        preview=body[:400],
                        date=msg.get("Date", "")[:40],
                        app="thunderbird",
                    ))
            return matches[-5:]
        except Exception:
            return []

    def search(self, query: str) -> list[EmailRecord]:
        """Search sender, subject, and body for query."""
        if not self.is_available():
            return []
        query_lower = query.lower()
        try:
            mbox = _mailbox.mbox(self.inbox_path)
            matches = []
            for msg in mbox:
                from_val = _decode_header(msg.get("From", "")).lower()
                subj = _decode_header(msg.get("Subject", "")).lower()
                body = _get_plain_body(msg).lower()
                if query_lower in from_val or query_lower in subj or query_lower in body:
                    matches.append(EmailRecord(
                        sender=_decode_header(msg.get("From", ""))[:80],
                        subject=_decode_header(msg.get("Subject", ""))[:120],
                        preview=_get_plain_body(msg)[:300],
                        date=msg.get("Date", "")[:40],
                        app="thunderbird",
                    ))
            return matches[-10:]
        except Exception:
            return []

class EmailWorkflows:
    """
    Email workflows built on top of the Desktop Faculty primitives.
    """

    def __init__(self, desktop: DesktopFaculty) -> None:
        self.desktop = desktop

    def read_inbox(
        self,
        app: str = DEFAULT_EMAIL_CLIENT,
        max_emails: int = 15,
    ) -> EmailWorkflowResult:
        """
        Read email inbox.
        Thunderbird: reads MBOX directly — real data, no hallucination.
        Other clients: uses accessibility tree.
        No proposal needed — pure observation.
        """
        app_name = normalize_email_app(app)
        result = EmailWorkflowResult(True, "read_inbox", app_name)

        # Thunderbird: direct MBOX read — ground truth only
        if app_name == "thunderbird":
            reader = ThunderbirdDirectReader()
            if reader.is_available():
                emails = reader.read_inbox(max_emails=max_emails)
                result.emails = emails
                result.steps_completed.append("direct_mbox_read")
                if emails:
                    lines = [f"email > inbox (thunderbird): {len(emails)} messages"]
                    for e in emails:
                        flag = "[unread] " if e.unread else ""
                        lines.append(f"  {flag}{e.sender} — {e.subject} [{e.date[:16]}]")
                    result.output = "\n".join(lines)
                else:
                    result.output = "email > inbox (thunderbird): no messages found"
                return result
            result.success = False
            result.error = "Thunderbird INBOX file not found on this system"
            return result

        # Other clients: accessibility tree
        open_result = self.desktop.open_app(app_name)
        result.steps_completed.append(f"open:{open_result.success}")
        if not open_result.success:
            result.success = False
            result.error = f"Could not open {app_name}: {open_result.error}"
            return result
        import time; time.sleep(2.0)
        window_title = EMAIL_APP_PATTERNS.get(app_name, [app_name])[0]
        read_r = self.desktop.read_window(app_name=window_title, max_depth=7)
        result.steps_completed.append(f"read:{read_r.success}")
        if read_r.success and read_r.output and len(read_r.output) > 100:
            result.output = read_r.output
            result.emails = self._parse_inbox(read_r.output, app_name)
        else:
            result.success = False
            result.error = f"Could not read {app_name} inbox — accessibility tree returned no content"
        return result

    def read_email(
        self, subject_or_sender: str,
        app: str = DEFAULT_EMAIL_CLIENT,
    ) -> EmailWorkflowResult:
        """
        Read a specific email by sender name or subject keyword.
        Thunderbird: direct MBOX search — real data only.
        """
        app_name = normalize_email_app(app)
        result = EmailWorkflowResult(True, "read_email", app_name)

        if app_name == "thunderbird":
            reader = ThunderbirdDirectReader()
            if reader.is_available():
                emails = reader.read_email_by_sender(subject_or_sender)
                if not emails:
                    emails = reader.read_email_by_subject(subject_or_sender)
                if emails:
                    result.emails = emails
                    lines = []
                    for e in emails:
                        lines.append(f"From: {e.sender}")
                        lines.append(f"Subject: {e.subject}")
                        lines.append(f"Date: {e.date}")
                        if e.preview:
                            lines.append("---")
                            lines.append(e.preview[:600])
                        lines.append("")
                    result.output = "\n".join(lines)
                    result.steps_completed.append("direct_mbox_read")
                else:
                    result.success = False
                    result.error = f"No emails found matching '{subject_or_sender}'"
            else:
                result.success = False
                result.error = "Thunderbird INBOX file not found"
            return result

        # Other clients
        open_result = self.desktop.open_app(app_name)
        result.steps_completed.append(f"open:{open_result.success}")
        if not open_result.success:
            result.success = False
            result.error = f"Could not open {app_name}: {open_result.error}"
            return result
        import time; time.sleep(2.0)
        self.desktop.click(subject_or_sender, app_name=app_name)
        read_r = self.desktop.read_window(app_name=app_name, max_depth=8)
        if read_r.success and read_r.output and len(read_r.output) > 100:
            result.output = read_r.output
        else:
            result.success = False
            result.error = "Could not read email content via accessibility tree"
        return result

    def search_emails(
        self,
        query: str,
        app: str = DEFAULT_EMAIL_CLIENT,
    ) -> EmailWorkflowResult:
        app_name = normalize_email_app(app)
        search_query = str(query or "").strip()
        result = EmailWorkflowResult(True, "search", app_name)

        open_result = self.desktop.open_app(app_name)
        result.steps_completed.append(f"open:{open_result.success}")
        if not open_result.success:
            result.success = False
            result.error = f"Could not open {app_name}: {open_result.error}"
            return result

        time.sleep(2.0)
        for label in ("Search", "Quick Filter", "Search emails"):
            search_field_result = self.desktop.click(label, app_name=app_name)
            if search_field_result.success:
                result.steps_completed.append(f"search_field:{label}")
                break
        type_result = self.desktop.type_text(search_query, submit=True)
        result.steps_completed.append(f"type_query:{type_result.success}")
        time.sleep(1.0)

        read_result = self.desktop.read_window(app_name=app_name, max_depth=7)
        result.steps_completed.append(f"read_results:{read_result.success}")
        if read_result.success:
            result.output = read_result.output
            result.emails = self._parse_inbox(read_result.output, app_name)
        else:
            result.success = False
            result.error = read_result.error or f"Could not search emails in {app_name}"
        return result

    def compose_draft(
        self,
        app: str = DEFAULT_EMAIL_CLIENT,
        to: str = "",
        subject: str = "",
        body: str = "",
    ) -> EmailWorkflowResult:
        app_name = normalize_email_app(app)
        result = EmailWorkflowResult(
            False,
            "compose_draft",
            app_name,
            recipient=str(to or "").strip(),
            subject=str(subject or "").strip(),
        )

        open_result = self.desktop.open_app(app_name)
        result.steps_completed.append(f"open:{open_result.success}")
        if not open_result.success:
            result.error = f"Could not open {app_name}: {open_result.error}"
            return result

        time.sleep(2.0)
        for label in (
            "Write",
            "New Message",
            "Compose",
            "New Email",
            "New mail",
            "✏",
            "Write a new message",
        ):
            compose_result = self.desktop.click(label, app_name=app_name)
            if compose_result.success:
                result.steps_completed.append(f"compose:{label}")
                break
        else:
            result.error = f"Could not find compose button in {app_name}"
            return result

        time.sleep(0.8)
        if to:
            for label in ("To", "To:", "Recipient"):
                to_result = self.desktop.click(label, app_name=app_name)
                if to_result.success:
                    self.desktop.type_text(str(to) + "\t")
                    result.steps_completed.append("fill_to")
                    break

        if subject:
            for label in ("Subject", "Subject:"):
                subject_result = self.desktop.click(label, app_name=app_name)
                if subject_result.success:
                    self.desktop.type_text(str(subject) + "\t")
                    result.steps_completed.append("fill_subject")
                    break

        for label in (
            "Message body",
            "Body",
            "Compose message area",
            "Write your message here",
        ):
            body_result = self.desktop.click(label, app_name=app_name)
            if body_result.success:
                result.steps_completed.append("click_body")
                break

        type_result = self.desktop.type_text(str(body or ""), submit=False)
        result.steps_completed.append(f"type_body:{type_result.success}")
        if not type_result.success:
            result.error = f"Could not type email body: {type_result.error}"
            return result

        result.success = True
        result.draft_visible = True
        preview = str(body or "")
        result.output = (
            f"Email draft ready in {app_name}:\n"
            f"To: {to}\n"
            f"Subject: {subject}\n"
            f"---\n{preview[:300]}"
            + ("\n[truncated]" if len(preview) > 300 else "")
            + "\n---\nAwaiting Send approval."
        )
        return result

    def reply_draft(
        self,
        app: str = DEFAULT_EMAIL_CLIENT,
        subject_or_sender: str = "",
        body: str = "",
    ) -> EmailWorkflowResult:
        app_name = normalize_email_app(app)
        target = str(subject_or_sender or "").strip()
        result = EmailWorkflowResult(False, "reply", app_name, subject=target)

        read_result = self.read_email(target, app_name)
        result.steps_completed.extend(read_result.steps_completed)
        if not read_result.success:
            result.error = read_result.error
            return result

        time.sleep(0.5)
        for label in ("Reply", "Reply All", "Re:"):
            reply_result = self.desktop.click(label, app_name=app_name)
            if reply_result.success:
                result.steps_completed.append(f"click_reply:{label}")
                break
        else:
            result.error = "Could not find Reply button"
            return result

        time.sleep(0.5)
        type_result = self.desktop.type_text(str(body or ""), submit=False)
        result.steps_completed.append(f"type_reply:{type_result.success}")
        if not type_result.success:
            result.error = f"Could not type reply: {type_result.error}"
            return result

        preview = str(body or "")
        result.success = True
        result.draft_visible = True
        result.output = (
            f"Reply draft ready in {app_name}:\n"
            f"Re: {target}\n"
            f"---\n{preview[:300]}"
            + ("\n[truncated]" if len(preview) > 300 else "")
            + "\n---\nAwaiting Send approval."
        )
        return result

    def execute_send(
        self,
        app: str = DEFAULT_EMAIL_CLIENT,
    ) -> EmailWorkflowResult:
        app_name = normalize_email_app(app)
        result = EmailWorkflowResult(False, "execute_send", app_name)

        for label in (
            "Send",
            "Send Email",
            "Send Message",
            "Send Now",
            "Send\t",
            "Send (Ctrl+Enter)",
        ):
            send_result = self.desktop.click(label, app_name=app_name)
            if send_result.success:
                result.success = True
                result.output = f"Email sent via {app_name}."
                result.steps_completed.append(f"send:{label}")
                return result

        enter_result = self.desktop.type_text("", submit=True)
        result.success = enter_result.success
        result.output = "Email sent." if enter_result.success else ""
        result.error = enter_result.error if not enter_result.success else None
        result.steps_completed.append("send:ctrl_enter_fallback")
        return result

    def _parse_inbox(self, window_content: str, app: str) -> list[EmailRecord]:
        emails: list[EmailRecord] = []
        if not window_content:
            return emails

        for line in window_content.splitlines():
            cleaned = str(line or "").strip()
            if not cleaned or len(cleaned) < 3:
                continue
            lowered = cleaned.lower()
            if lowered in {
                "inbox",
                "sent",
                "drafts",
                "trash",
                "spam",
                "write",
                "search",
                "compose",
                "new message",
                "reply",
                "forward",
                "delete",
                "mark as read",
                "settings",
                "accounts",
                "folders",
            }:
                continue
            if 4 < len(cleaned) < 200:
                emails.append(EmailRecord(subject=cleaned, app=app))
        return emails[:15]

    def format_result(self, result: EmailWorkflowResult) -> str:
        if not result.success and result.error:
            return f"email > error in {result.app}: {result.error}"

        if result.workflow == "read_inbox":
            if result.emails:
                lines = [
                    f"email > inbox ({result.app}): {len(result.emails)} items visible"
                ]
                for email in result.emails[:8]:
                    lines.append(
                        f"  {'[unread] ' if email.unread else ''}"
                        f"{email.sender or ''} - {email.subject[:60]}"
                    )
                return "\n".join(lines)
            return (
                f"email > inbox ({result.app}) opened\n"
                f"{result.output[:400] if result.output else '(empty)'}"
            )

        if result.workflow in {"read_email", "search"}:
            return (
                f"email > {result.workflow} in {result.app}:\n"
                f"{result.output[:600] if result.output else '(no content)'}"
            )

        if result.workflow in {"compose_draft", "reply"} and result.draft_visible:
            return f"email > draft ready in {result.app}\n{result.output}"

        if result.workflow == "execute_send":
            return f"email > {result.output or 'sent'}"

        return (
            f"email > {result.workflow} in {result.app}: "
            f"{'done' if result.success else 'failed'}"
        )

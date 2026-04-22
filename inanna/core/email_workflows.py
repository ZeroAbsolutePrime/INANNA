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


class EmailWorkflows:
    """
    Email workflows built on top of the Desktop Faculty primitives.
    """

    def __init__(self, desktop: DesktopFaculty) -> None:
        self.desktop = desktop

    def read_inbox(
        self,
        app: str = DEFAULT_EMAIL_CLIENT,
        max_emails: int = 10,
    ) -> EmailWorkflowResult:
        app_name = normalize_email_app(app)
        result = EmailWorkflowResult(True, "read_inbox", app_name)

        open_result = self.desktop.open_app(app_name)
        result.steps_completed.append(f"open:{open_result.success}")
        if not open_result.success:
            result.success = False
            result.error = f"Could not open {app_name}: {open_result.error}"
            return result

        time.sleep(2.0)
        window_title = EMAIL_APP_PATTERNS.get(app_name, [app_name])[0]
        read_result = self.desktop.read_window(app_name=window_title, max_depth=7)
        result.steps_completed.append(f"read:{read_result.success}")
        if read_result.success:
            result.output = read_result.output
            result.emails = self._parse_inbox(read_result.output, app_name)[: max(1, max_emails)]
        else:
            result.success = False
            result.error = read_result.error or f"Could not read inbox in {app_name}"
        return result

    def read_email(
        self,
        subject_or_sender: str,
        app: str = DEFAULT_EMAIL_CLIENT,
    ) -> EmailWorkflowResult:
        app_name = normalize_email_app(app)
        lookup = str(subject_or_sender or "").strip()
        result = EmailWorkflowResult(True, "read_email", app_name)

        open_result = self.desktop.open_app(app_name)
        result.steps_completed.append(f"open:{open_result.success}")
        if not open_result.success:
            result.success = False
            result.error = f"Could not open {app_name}: {open_result.error}"
            return result

        time.sleep(2.0)
        click_result = self.desktop.click(lookup, app_name=app_name)
        result.steps_completed.append(f"click_email:{click_result.success}")
        if not click_result.success:
            search_result = self.desktop.click("Search", app_name=app_name)
            result.steps_completed.append(f"search:{search_result.success}")
            if search_result.success:
                self.desktop.type_text(lookup, submit=True)
                time.sleep(1.0)

        read_result = self.desktop.read_window(app_name=app_name, max_depth=8)
        result.steps_completed.append(f"read_content:{read_result.success}")
        if read_result.success:
            result.output = read_result.output
        else:
            result.success = False
            result.error = read_result.error or f"Could not read email in {app_name}"
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

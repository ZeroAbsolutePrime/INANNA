from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from core.desktop_faculty import DesktopFaculty


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
    workflow: str
    app: str
    messages: list[MessageRecord] = field(default_factory=list)
    output: str = ""
    draft_visible: bool = False
    error: str | None = None
    steps_completed: list[str] = field(default_factory=list)


APP_WINDOW_PATTERNS = {
    "signal": ["Signal", "Signal Messenger", "Signal Desktop"],
    "whatsapp": ["WhatsApp", "WhatsApp Desktop"],
    "telegram": ["Telegram"],
    "discord": ["Discord"],
    "slack": ["Slack"],
}


APP_WINGET_IDS = {
    "signal": "OpenWhisperSystems.Signal",
    "whatsapp": "WhatsApp.WhatsApp",
    "telegram": "Telegram.TelegramDesktop",
    "discord": "Discord.Discord",
    "slack": "SlackTechnologies.Slack",
}


def normalize_app_name(name: str) -> str:
    cleaned = str(name or "").strip().lower()
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
    return aliases.get(cleaned, cleaned)


class CommunicationWorkflows:
    """
    Messaging workflows built on top of the Desktop Faculty primitives.
    """

    def __init__(self, desktop: DesktopFaculty) -> None:
        self.desktop = desktop

    def read_messages(self, app: str) -> WorkflowResult:
        app_name = normalize_app_name(app)
        result = WorkflowResult(True, "read_messages", app_name)
        if not app_name:
            result.success = False
            result.error = "Communication app is required."
            return result

        open_result = self.desktop.open_app(app_name)
        result.steps_completed.append(f"open:{open_result.success}")
        if not open_result.success:
            result.success = False
            result.error = f"Could not open {app_name}: {open_result.error}"
            return result

        screenshot_result = self.desktop.screenshot(app_name)
        result.steps_completed.append(f"screenshot:{screenshot_result.success}")

        time.sleep(1.5)
        read_result = self.desktop.read_window(
            app_name=APP_WINDOW_PATTERNS.get(app_name, [app_name])[0],
            max_depth=6,
        )
        result.steps_completed.append(f"read:{read_result.success}")
        if read_result.success:
            result.output = read_result.output
            result.messages = self._parse_messages(read_result.output, app_name)
        else:
            result.success = False
            result.error = read_result.error or f"Could not read {app_name} window."
        return result

    def send_message(self, app: str, contact: str, message: str) -> WorkflowResult:
        app_name = normalize_app_name(app)
        contact_name = str(contact or "").strip()
        message_text = str(message or "")
        result = WorkflowResult(False, "send_message", app_name)

        if not app_name:
            result.error = "Communication app is required."
            return result
        if not contact_name:
            result.error = "Contact name is required."
            return result
        if not message_text.strip():
            result.error = "Message text is required."
            return result

        open_result = self.desktop.open_app(app_name)
        result.steps_completed.append(f"open:{open_result.success}")
        if not open_result.success:
            result.error = f"Could not open {app_name}: {open_result.error}"
            return result

        time.sleep(1.5)

        contact_result = self.desktop.click(contact_name, app_name=app_name)
        result.steps_completed.append(f"click_contact:{contact_result.success}")
        if not contact_result.success:
            search_result = self.desktop.click("Search", app_name=app_name)
            result.steps_completed.append(f"search_button:{search_result.success}")
            if search_result.success:
                search_type_result = self.desktop.type_text(contact_name, submit=False)
                result.steps_completed.append(f"type_search:{search_type_result.success}")
                time.sleep(0.8)
                contact_retry_result = self.desktop.click(contact_name, app_name=app_name)
                result.steps_completed.append(f"search_contact:{contact_retry_result.success}")
                if not contact_retry_result.success:
                    result.error = f"Could not find contact '{contact_name}' in {app_name}"
                    return result
            else:
                result.error = f"Could not find contact '{contact_name}' in {app_name}"
                return result

        time.sleep(0.5)
        for field_name in (
            "message field",
            "message input",
            "type a message",
            "Message",
            "New message",
        ):
            field_result = self.desktop.click(field_name, app_name=app_name)
            if field_result.success:
                result.steps_completed.append(f"click_field:{field_name}")
                break
        else:
            result.steps_completed.append("click_field:fallback")

        type_result = self.desktop.type_text(message_text, submit=False)
        result.steps_completed.append(f"type_draft:{type_result.success}")
        if not type_result.success:
            result.error = f"Could not type message: {type_result.error}"
            return result

        result.success = True
        result.draft_visible = True
        result.output = (
            f"Draft typed in {app_name} to {contact_name}:\n"
            f'"{message_text}"\n'
            "Waiting for Send approval."
        )
        return result

    def execute_send(self, app: str) -> WorkflowResult:
        app_name = normalize_app_name(app)
        result = WorkflowResult(False, "execute_send", app_name)
        if not app_name:
            result.error = "Communication app is required."
            return result

        for send_label in (
            "Send",
            "Send message",
            "Send Message",
            "Send reply",
            "↵",
            "Enter",
        ):
            send_result = self.desktop.click(send_label, app_name=app_name)
            if send_result.success:
                result.success = True
                result.output = f"Message sent via {app_name}."
                result.steps_completed.append(f"send:{send_label}")
                return result

        enter_result = self.desktop.type_text("", submit=True)
        result.success = enter_result.success
        result.output = "Message sent via Enter key." if enter_result.success else ""
        result.error = enter_result.error if not enter_result.success else None
        result.steps_completed.append("send:enter_key")
        return result

    def list_contacts(self, app: str) -> WorkflowResult:
        app_name = normalize_app_name(app)
        result = WorkflowResult(True, "list_contacts", app_name)
        if not app_name:
            result.success = False
            result.error = "Communication app is required."
            return result

        open_result = self.desktop.open_app(app_name)
        result.steps_completed.append(f"open:{open_result.success}")
        if not open_result.success:
            result.success = False
            result.error = f"Could not open {app_name}: {open_result.error}"
            return result

        time.sleep(1.5)
        read_result = self.desktop.read_window(
            app_name=APP_WINDOW_PATTERNS.get(app_name, [app_name])[0],
            max_depth=6,
        )
        result.steps_completed.append(f"read:{read_result.success}")
        if read_result.success:
            result.output = read_result.output
        else:
            result.success = False
            result.error = read_result.error or f"Could not read contacts from {app_name}"
        return result

    def _parse_messages(self, window_content: str, app: str) -> list[MessageRecord]:
        messages: list[MessageRecord] = []
        if not window_content:
            return messages

        for line in window_content.splitlines():
            cleaned_line = str(line or "").strip()
            if not cleaned_line or len(cleaned_line) < 3:
                continue
            visible_text = re.sub(r"^\[[^\]]+\]\s*", "", cleaned_line).strip()
            if not visible_text:
                continue
            if visible_text.lower() in {
                "send",
                "search",
                "settings",
                "new chat",
                "archive",
                "muted",
                "button",
                "menu",
            }:
                continue
            if 5 < len(visible_text) < 500 and " " in visible_text:
                messages.append(
                    MessageRecord(
                        sender="unknown",
                        content=visible_text,
                        app=app,
                    )
                )
        return messages[:20]

    def format_result(self, result: WorkflowResult) -> str:
        if not result.success and result.error:
            return f"comm > error in {result.app}: {result.error}"

        if result.workflow == "read_messages":
            if result.messages:
                lines = [f"comm > {result.app}: {len(result.messages)} items visible"]
                for message in result.messages[:10]:
                    lines.append(f"  {message.content[:80]}")
                return "\n".join(lines)
            return (
                f"comm > {result.app}: window opened\n"
                f"{result.output[:500] if result.output else '(no content)'}"
            )

        if result.workflow == "send_message" and result.draft_visible:
            return f"comm > draft ready in {result.app}\n{result.output}"

        if result.workflow == "execute_send":
            return f"comm > {result.output or 'sent'}"

        if result.workflow == "list_contacts":
            return (
                f"comm > contacts in {result.app}:\n"
                f"{result.output[:800] if result.output else '(none visible)'}"
            )

        return f"comm > {result.workflow} in {result.app}: done"

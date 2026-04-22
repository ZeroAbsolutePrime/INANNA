from __future__ import annotations

import os
import platform
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


CONSEQUENTIAL_LABELS = {
    "send",
    "send message",
    "send reply",
    "send email",
    "delete",
    "remove",
    "trash",
    "submit",
    "confirm",
    "ok",
    "buy",
    "purchase",
    "pay",
    "post",
    "publish",
}

LINUX_APP_NAME_MAP = {
    "thunderbird": "thunderbird",
    "firefox": "firefox",
    "signal": "signal-desktop",
    "libreoffice": "libreoffice",
    "writer": "libreoffice --writer",
    "calc": "libreoffice --calc",
    "impress": "libreoffice --impress",
    "terminal": "gnome-terminal",
    "files": "nautilus",
}


def is_consequential_label(label: str) -> bool:
    normalized = " ".join(str(label or "").strip().lower().split())
    for suffix in (" button", " link", " tab", " key", " icon"):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
            break
    return normalized in CONSEQUENTIAL_LABELS


@dataclass
class DesktopResult:
    success: bool
    tool: str
    query: str
    output: str = ""
    screenshot_path: str = ""
    error: str | None = None
    window_title: str = ""
    element_found: bool = False
    consequential: bool = False


class DesktopFaculty:
    """
    Platform-agnostic desktop bridge for INANNA NYX.
    """

    def __init__(self) -> None:
        self._os = platform.system() or "Unknown"
        self._backend = self._select_backend()

    def _select_backend(self):
        if self._os == "Windows":
            return WindowsMCPBackend()
        if self._os == "Linux":
            return LinuxAtspiBackend()
        return FallbackBackend(self._os)

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def open_app(self, app: str) -> DesktopResult:
        return self._backend.open_app(app)

    def read_window(self, app_name: str = "", max_depth: int = 5) -> DesktopResult:
        return self._backend.read_window(app_name, max(1, min(int(max_depth or 5), 10)))

    def click(self, label: str, app_name: str = "") -> DesktopResult:
        result = self._backend.click(label, app_name)
        result.consequential = is_consequential_label(label)
        return result

    def type_text(self, text: str, submit: bool = False) -> DesktopResult:
        result = self._backend.type_text(text, submit)
        result.consequential = bool(submit)
        return result

    def screenshot(self, app_name: str = "") -> DesktopResult:
        return self._backend.screenshot(app_name)

    def format_result(self, result: DesktopResult) -> str:
        if not result.success:
            return f"desktop > error: {result.error or 'Unknown desktop error.'}"

        if result.tool == "open_app":
            message = f"desktop > opened: {result.query}"
            if result.window_title:
                message += f" [{result.window_title}]"
            return message

        if result.tool == "read_window":
            lines = [f"desktop > window content: {result.query or 'active window'}", ""]
            lines.append(result.output[:2000] if result.output else "(empty or no accessible content)")
            return "\n".join(lines)

        if result.tool == "click":
            message = f"desktop > clicked: '{result.query}'"
            if result.consequential:
                message += " [consequential action]"
            return message

        if result.tool == "type":
            preview = result.query[:40] + ("..." if len(result.query) > 40 else "")
            message = f"desktop > typed: '{preview}'"
            if result.consequential:
                message += " [submitted]"
            return message

        if result.tool == "screenshot":
            message = f"desktop > screenshot captured: {result.query or 'desktop'}"
            if result.screenshot_path:
                message += f" [{result.screenshot_path}]"
            return message

        return f"desktop > {result.tool}: {result.query}"


class WindowsMCPBackend:
    """
    Windows desktop backend using pywinauto with PowerShell fallbacks.
    """

    name = "windows-mcp"

    def _has_pywinauto(self) -> bool:
        try:
            import pywinauto  # noqa: F401

            return True
        except ImportError:
            return False

    def open_app(self, app: str) -> DesktopResult:
        target = str(app or "").strip()
        if not target:
            return DesktopResult(False, "open_app", target, error="Application name is required.")
        try:
            escaped = target.replace("'", "''")
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"Start-Process -FilePath '{escaped}'"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return DesktopResult(True, "open_app", target, output=f"Started {target}")
            fallback = subprocess.run(
                ["cmd", "/c", "start", "", target],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return DesktopResult(
                fallback.returncode == 0,
                "open_app",
                target,
                output=f"Started {target}" if fallback.returncode == 0 else "",
                error=str(fallback.stderr or result.stderr or "").strip()[:200] or None,
            )
        except subprocess.TimeoutExpired:
            return DesktopResult(False, "open_app", target, error=f"Timeout launching {target}")
        except Exception as error:
            return DesktopResult(False, "open_app", target, error=str(error))

    def read_window(self, app_name: str = "", max_depth: int = 5) -> DesktopResult:
        query = str(app_name or "").strip()
        if not self._has_pywinauto():
            return self._fallback_read_window(query)
        try:
            import pywinauto
            from pywinauto import Desktop

            if query:
                app = pywinauto.Application(backend="uia").connect(
                    title_re=f".*{re.escape(query)}.*",
                    timeout=5,
                )
                window = app.top_window()
            else:
                windows = Desktop(backend="uia").windows()
                if not windows:
                    return DesktopResult(False, "read_window", query, error="No windows found.")
                window = windows[0]

            lines: list[str] = []
            self._extract_tree(window.wrapper_object(), lines, 0, max_depth)
            return DesktopResult(
                True,
                "read_window",
                query or window.window_text(),
                output="\n".join(lines),
                window_title=window.window_text(),
            )
        except Exception as error:
            return DesktopResult(False, "read_window", query, error=str(error))

    def _extract_tree(self, element, lines: list[str], depth: int, max_depth: int) -> None:
        if depth > max_depth:
            return
        try:
            name = str(element.window_text() or "").strip()
            ctrl_type = str(getattr(element.element_info, "control_type", "") or "").strip()
            if name or ctrl_type:
                indent = "  " * depth
                lines.append(f"{indent}[{ctrl_type or 'control'}] {name}".rstrip())
        except Exception:
            pass
        try:
            for child in element.children():
                self._extract_tree(child, lines, depth + 1, max_depth)
        except Exception:
            pass

    def _fallback_read_window(self, app_name: str) -> DesktopResult:
        script = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$children = $root.FindAll(
    [System.Windows.Automation.TreeScope]::Children,
    [System.Windows.Automation.Condition]::TrueCondition
)
foreach ($child in $children) {
    $label = "[" + $child.Current.ControlType.ProgrammaticName + "] " + $child.Current.Name
    Write-Output $label
}
"""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = str(result.stdout or "").strip()
            if app_name:
                filtered = [
                    line for line in output.splitlines() if app_name.lower() in line.lower()
                ]
                output = "\n".join(filtered)
            return DesktopResult(True, "read_window", app_name, output=output[:2000])
        except Exception as error:
            return DesktopResult(False, "read_window", app_name, error=str(error))

    def click(self, label: str, app_name: str = "") -> DesktopResult:
        target = str(label or "").strip()
        query = str(app_name or "").strip()
        if not target:
            return DesktopResult(False, "click", target, error="Element label is required.")
        if not self._has_pywinauto():
            return DesktopResult(False, "click", target, error="pywinauto is not installed.")
        try:
            from pywinauto import Application, Desktop

            if query:
                window = Application(backend="uia").connect(
                    title_re=f".*{re.escape(query)}.*",
                    timeout=5,
                ).top_window()
            else:
                windows = Desktop(backend="uia").windows()
                if not windows:
                    return DesktopResult(False, "click", target, error="No windows found.")
                window = windows[0]
            element = window.child_window(title=target, found_index=0)
            element.click_input()
            return DesktopResult(True, "click", target, output=f"Clicked '{target}'", element_found=True)
        except Exception as error:
            return DesktopResult(False, "click", target, error=str(error))

    def type_text(self, text: str, submit: bool = False) -> DesktopResult:
        content = str(text or "")
        if not content:
            return DesktopResult(False, "type", content, error="Text is required.")
        try:
            from pywinauto.keyboard import send_keys

            escaped = content.replace("{", "{{").replace("}", "}}")
            send_keys(escaped, with_spaces=True, pause=0.02)
            if submit:
                send_keys("{ENTER}")
            return DesktopResult(True, "type", content, output=f"Typed {len(content)} characters")
        except ImportError:
            try:
                escaped = content.replace("'", "''")
                script = (
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    f"[System.Windows.Forms.SendKeys]::SendWait('{escaped}')"
                )
                if submit:
                    script += "; [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')"
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", script],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                return DesktopResult(True, "type", content, output=f"Typed {len(content)} characters")
            except Exception as error:
                return DesktopResult(False, "type", content, error=str(error))
        except Exception as error:
            return DesktopResult(False, "type", content, error=str(error))

    def screenshot(self, app_name: str = "") -> DesktopResult:
        target = str(app_name or "").strip() or "desktop"
        out_path = Path(tempfile.NamedTemporaryFile(prefix="inanna_desktop_", suffix=".png", delete=False).name)
        try:
            escaped = str(out_path).replace("'", "''")
            script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "Add-Type -AssemblyName System.Drawing; "
                "$screen = [System.Windows.Forms.Screen]::PrimaryScreen; "
                "$bounds = $screen.Bounds; "
                "$bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height); "
                "$graphics = [System.Drawing.Graphics]::FromImage($bitmap); "
                "$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size); "
                f"$bitmap.Save('{escaped}'); "
                "$graphics.Dispose(); "
                "$bitmap.Dispose();"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if out_path.exists():
                return DesktopResult(
                    True,
                    "screenshot",
                    target,
                    screenshot_path=str(out_path),
                    output=f"Screenshot saved: {out_path.name}",
                )
            return DesktopResult(False, "screenshot", target, error="Screenshot file not created.")
        except Exception as error:
            return DesktopResult(False, "screenshot", target, error=str(error))


class LinuxAtspiBackend:
    """
    Linux desktop backend using AT-SPI2 with command-line fallbacks.
    """

    name = "linux-atspi2"

    def _detect_display_server(self) -> str:
        """Detect X11 or Wayland. Returns 'wayland' or 'x11'."""
        wayland_display = os.environ.get("WAYLAND_DISPLAY", "")
        xdg_session = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if wayland_display or xdg_session == "wayland":
            return "wayland"
        return "x11"

    def _normalize_app_name(self, app: str) -> str:
        normalized = str(app or "").strip().lower()
        return LINUX_APP_NAME_MAP.get(normalized, str(app or "").strip())

    def open_app(self, app: str) -> DesktopResult:
        target = str(app or "").strip()
        if not target:
            return DesktopResult(False, "open_app", target, error="Application name is required.")
        command_text = self._normalize_app_name(target)
        try:
            process = subprocess.Popen(command_text.split())
            return DesktopResult(
                process.poll() is None or process.returncode == 0,
                "open_app",
                target,
            )
        except Exception:
            try:
                process = subprocess.Popen(["xdg-open", command_text])
                return DesktopResult(
                    process.poll() is None or process.returncode == 0,
                    "open_app",
                    target,
                )
            except Exception as error:
                return DesktopResult(False, "open_app", target, error=str(error))

    def read_window(self, app_name: str = "", max_depth: int = 5) -> DesktopResult:
        query = str(app_name or "").strip()
        try:
            import pyatspi

            desktop = pyatspi.Registry.getDesktop(0)
            lines: list[str] = []
            for app in desktop:
                app_label = str(getattr(app, "name", "") or "")
                if query and query.lower() not in app_label.lower():
                    continue
                self._extract_tree(app, lines, 0, max_depth)
            return DesktopResult(True, "read_window", query, output="\n".join(lines))
        except ImportError:
            return DesktopResult(False, "read_window", query, error="pyatspi is not installed.")
        except Exception as error:
            return DesktopResult(False, "read_window", query, error=str(error))

    def _extract_tree(self, element, lines: list[str], depth: int, max_depth: int) -> None:
        if depth > max_depth:
            return
        try:
            role = str(element.getRoleName() or "").strip()
            name = str(element.name or "").strip()
            if role or name:
                indent = "  " * depth
                lines.append(f"{indent}[{role or 'element'}] {name}".rstrip())
        except Exception:
            pass
        try:
            for index in range(int(element.childCount)):
                self._extract_tree(element.getChildAtIndex(index), lines, depth + 1, max_depth)
        except Exception:
            pass

    def click(self, label: str, app_name: str = "") -> DesktopResult:
        target = str(label or "").strip()
        query = str(app_name or "").strip()
        if not target:
            return DesktopResult(False, "click", target, error="Element label is required.")
        try:
            import pyatspi

            desktop = pyatspi.Registry.getDesktop(0)
            for app in desktop:
                app_label = str(getattr(app, "name", "") or "")
                if query and query.lower() not in app_label.lower():
                    continue
                element = self._find_by_name(app, target)
                if element is not None:
                    element.queryAction().doAction(0)
                    return DesktopResult(True, "click", target, element_found=True, output=f"Clicked '{target}'")
            return DesktopResult(False, "click", target, error=f"Element '{target}' not found.")
        except ImportError:
            return DesktopResult(False, "click", target, error="pyatspi is not installed.")
        except Exception as error:
            return DesktopResult(False, "click", target, error=str(error))

    def _find_by_name(self, element, name: str):
        try:
            element_name = str(element.name or "").strip()
            if element_name.lower() == name.lower():
                return element
        except Exception:
            pass
        try:
            for index in range(int(element.childCount)):
                found = self._find_by_name(element.getChildAtIndex(index), name)
                if found is not None:
                    return found
        except Exception:
            pass
        return None

    def type_text(self, text: str, submit: bool = False) -> DesktopResult:
        content = str(text or "")
        if not content:
            return DesktopResult(False, "type", content, error="Text is required.")
        display_server = self._detect_display_server()
        try:
            if display_server == "wayland":
                result = subprocess.run(
                    ["ydotool", "type", content],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if submit:
                    subprocess.run(
                        ["ydotool", "key", "28:1", "28:0"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
            else:
                result = subprocess.run(
                    ["xdotool", "type", "--clearmodifiers", content],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if submit:
                    subprocess.run(
                        ["xdotool", "key", "Return"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
            return DesktopResult(result.returncode == 0, "type", content, output=f"Typed {len(content)} characters")
        except FileNotFoundError:
            try:
                fallback_command = (
                    ["xdotool", "type", "--clearmodifiers", content]
                    if display_server == "wayland"
                    else ["ydotool", "type", content]
                )
                result = subprocess.run(fallback_command, capture_output=True, text=True, timeout=10)
                return DesktopResult(
                    result.returncode == 0,
                    "type",
                    content,
                    output=f"Typed {len(content)} characters",
                    error=str(result.stderr or "").strip() or None,
                )
            except Exception as error:
                return DesktopResult(False, "type", content, error=str(error))
        except Exception as error:
            return DesktopResult(False, "type", content, error=str(error))

    def screenshot(self, app_name: str = "") -> DesktopResult:
        target = str(app_name or "").strip() or "desktop"
        out_path = Path(tempfile.NamedTemporaryFile(prefix="inanna_desktop_", suffix=".png", delete=False).name)
        try:
            result = subprocess.run(
                ["scrot", str(out_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and out_path.exists():
                return DesktopResult(True, "screenshot", target, screenshot_path=str(out_path))
            fallback = subprocess.run(
                ["gnome-screenshot", "-f", str(out_path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if fallback.returncode == 0 and out_path.exists():
                return DesktopResult(True, "screenshot", target, screenshot_path=str(out_path))
            return DesktopResult(False, "screenshot", target, error="Screenshot failed.")
        except Exception as error:
            return DesktopResult(False, "screenshot", target, error=str(error))


class FallbackBackend:
    def __init__(self, os_name: str) -> None:
        self._os = str(os_name or "Unknown")
        self.name = f"fallback-{self._os.lower()}"

    def _unsupported(self, tool: str, query: str) -> DesktopResult:
        return DesktopResult(False, tool, query, error=f"Desktop Faculty is not supported on {self._os}.")

    def open_app(self, app: str) -> DesktopResult:
        return self._unsupported("open_app", str(app or "").strip())

    def read_window(self, app_name: str = "", max_depth: int = 5) -> DesktopResult:
        del max_depth
        return self._unsupported("read_window", str(app_name or "").strip())

    def click(self, label: str, app_name: str = "") -> DesktopResult:
        del app_name
        return self._unsupported("click", str(label or "").strip())

    def type_text(self, text: str, submit: bool = False) -> DesktopResult:
        del submit
        return self._unsupported("type", str(text or ""))

    def screenshot(self, app_name: str = "") -> DesktopResult:
        return self._unsupported("screenshot", str(app_name or "").strip())

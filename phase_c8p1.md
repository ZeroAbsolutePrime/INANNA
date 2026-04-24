# CURRENT PHASE: Cycle 8 - Phase 8.1 - The Desktop Faculty Core
**Status: ACTIVE**
**Authorized by: INANNA NAMMU (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Cycle: 8 - The Desktop Bridge**
**Master plan: docs/cycle8_master_plan.md**
**Prerequisite: Cycle 7 complete — 432 tests, 18 tools, authentication**

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — implement Desktop Faculty and Windows backend
TESTER:     Codex — unit tests (offline, no apps required)
VERIFIER:   Command Center — confirm after push

BUILDER forbidden from:
  - Touching voice/ directory
  - Modifying auth system
  - Building app-specific workflows (Phase 8.2+)
  - Making actual UI automation calls in tests

---

## What This Phase Is

This phase builds the architecture that all of Cycle 8 rests on.

The Desktop Faculty is the bridge between INANNA and every
application running on the computer. Instead of building
one integration per app, we build five abstract tools that
work with any app. Then Phases 8.2-8.6 use these same five
tools to reach WhatsApp, LibreOffice, email, browser, calendar.

The Windows backend uses Windows-MCP — already connected to
the system and verified working.

The Linux backend is stubbed and ready for Phase 8.7 when
the system moves to NixOS.

---

## Technical Foundation: Windows-MCP

Windows-MCP is already installed and running on this machine.
It is available at: Windows-MCP tools (Snapshot, Click, Type,
Screenshot, App, PowerShell).

Key tools we will use:
  Snapshot — reads the UI accessibility tree of any window.
             Returns elements with their names, roles, states.
             No screenshots needed. Deterministic by name.

  App      — opens any application by name.

  Click    — clicks a UI element by its accessibility label.

  Type     — types text into the focused element.

  Screenshot — captures the current screen state as an image.

Windows-MCP uses the Windows UI Automation API — the same API
screen readers use. It finds "Send" button by name, not pixel.
Works with classic Windows apps, Windows 11, Electron, and
Chromium-based browsers. Deterministic regardless of DPI,
theme, resolution, or window position.

---

## The Five Abstract Tools

All five tools work identically on Windows (via Windows-MCP)
and on Linux (via AT-SPI2, Phase 8.7).

### desktop_open_app
Open any installed application by name.
```
input:  {"app": "whatsapp"}
output: success/failure, window_title
```
Governance: requires proposal (Light)

### desktop_read_window
Read the accessibility tree content of a window.
Returns structured text of all visible UI elements.
```
input:  {"app_name": "whatsapp", "max_depth": 5}
output: structured element tree as text
```
Governance: no proposal required (observation only)

### desktop_click
Click a UI element by its accessibility name.
```
input:  {"label": "Send", "app_name": "whatsapp"}
output: success/failure, element_found
```
Governance: requires proposal for consequential elements
(Send, Delete, Submit, Buy, Confirm)

### desktop_type
Type text into the currently focused element.
```
input:  {"text": "Hello, how are you?", "submit": false}
output: success/failure, chars_typed
```
Governance: requires proposal (typing is visible action)
submit=True sends Enter after typing (consequential)

### desktop_screenshot
Capture the current state of a window as an image.
```
input:  {"app_name": "whatsapp"}
output: screenshot path, dimensions
```
Governance: no proposal required (observation only)

---

## What You Are Building

### Task 1 — inanna/core/desktop_faculty.py

Create: inanna/core/desktop_faculty.py

```python
"""
INANNA NYX Desktop Faculty
Platform-agnostic bridge to the desktop UI.

Windows backend: Windows-MCP (UI Automation API)
Linux backend: AT-SPI2 via python-atspi (Phase 8.7)

The five abstract tools:
  desktop_open_app      — open any application
  desktop_read_window   — read UI content
  desktop_click         — click by accessibility name
  desktop_type          — type text
  desktop_screenshot    — capture screen state

Governance:
  Observation (read, screenshot): no proposal needed
  Light action (open, navigate): proposal required, auto-trust after 3x
  Consequential (send, delete, submit): proposal ALWAYS required
"""
from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Consequential element names — clicking these always requires proposal
# regardless of trust level
CONSEQUENTIAL_LABELS = {
    "send", "send message", "send reply", "send email",
    "delete", "remove", "trash",
    "submit", "confirm", "ok",
    "buy", "purchase", "pay",
    "post", "publish",
}


def is_consequential_label(label: str) -> bool:
    """Returns True if clicking this label requires mandatory proposal."""
    return label.lower().strip() in CONSEQUENTIAL_LABELS


@dataclass
class DesktopResult:
    success: bool
    tool: str           # open_app | read_window | click | type | screenshot
    query: str          # the app name or element name
    output: str = ""    # text output (window content, confirmation)
    screenshot_path: str = ""
    error: Optional[str] = None
    window_title: str = ""
    element_found: bool = False
    consequential: bool = False  # True if this was a send/delete/submit


class DesktopFaculty:
    """
    Platform-agnostic desktop automation.
    Automatically selects the right backend based on the OS.
    """

    def __init__(self) -> None:
        self._os = platform.system()
        self._backend = self._select_backend()

    def _select_backend(self):
        if self._os == "Windows":
            return WindowsMCPBackend()
        elif self._os == "Linux":
            return LinuxAtspiBackend()
        else:
            return FallbackBackend(self._os)

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def open_app(self, app: str) -> DesktopResult:
        """
        Open an application by name.
        Requires proposal approval (Light governance).
        """
        return self._backend.open_app(app)

    def read_window(
        self, app_name: str = "", max_depth: int = 5
    ) -> DesktopResult:
        """
        Read the accessibility tree of a window.
        No proposal required — observation only.
        """
        return self._backend.read_window(app_name, max_depth)

    def click(
        self, label: str, app_name: str = ""
    ) -> DesktopResult:
        """
        Click a UI element by its accessibility name.
        Consequential elements (Send, Delete) always require proposal.
        """
        result = self._backend.click(label, app_name)
        result.consequential = is_consequential_label(label)
        return result

    def type_text(
        self, text: str, submit: bool = False
    ) -> DesktopResult:
        """
        Type text into the focused element.
        submit=True sends Enter after (consequential).
        """
        result = self._backend.type_text(text, submit)
        result.consequential = submit
        return result

    def screenshot(self, app_name: str = "") -> DesktopResult:
        """
        Capture the screen or a specific app window.
        No proposal required — observation only.
        """
        return self._backend.screenshot(app_name)

    def format_result(self, result: DesktopResult) -> str:
        """Format a DesktopResult for display in the conversation."""
        if not result.success:
            return f"desktop > error: {result.error}"

        if result.tool == "open_app":
            return (
                f"desktop > opened: {result.query}"
                + (f" [{result.window_title}]" if result.window_title else "")
            )

        if result.tool == "read_window":
            lines = [f"desktop > window content: {result.query}", ""]
            if result.output:
                lines.append(result.output[:2000])
            else:
                lines.append("(empty or no accessible content)")
            return "\n".join(lines)

        if result.tool == "click":
            return (
                f"desktop > clicked: '{result.query}'"
                + (" [consequential action]" if result.consequential else "")
            )

        if result.tool == "type":
            preview = result.query[:40] + ("..." if len(result.query) > 40 else "")
            return (
                f"desktop > typed: '{preview}'"
                + (" [submitted]" if result.consequential else "")
            )

        if result.tool == "screenshot":
            return (
                f"desktop > screenshot captured: {result.query}"
                + (f" [{result.screenshot_path}]" if result.screenshot_path else "")
            )

        return f"desktop > {result.tool}: {result.query}"


# ── WINDOWS BACKEND ──────────────────────────────────────────────────

class WindowsMCPBackend:
    """
    Desktop Faculty backend using Windows-MCP subprocess calls.

    Windows-MCP is available as a running MCP server connected to
    the current session. For INANNA's use, we call it via PowerShell
    subprocess using pywinauto and the Windows UI Automation API.

    This backend wraps pywinauto — the Python library that powers
    Windows-MCP under the hood — for direct programmatic access.
    """

    name = "windows-mcp"

    def _has_pywinauto(self) -> bool:
        try:
            import pywinauto  # noqa: F401
            return True
        except ImportError:
            return False

    def open_app(self, app: str) -> DesktopResult:
        try:
            # Use PowerShell Start-Process for reliable app launch
            result = subprocess.run(
                ["powershell", "-Command",
                 f'Start-Process "{app}"'],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return DesktopResult(
                    True, "open_app", app,
                    output=f"Started {app}",
                )
            # Fallback: try the run command
            result2 = subprocess.run(
                ["cmd", "/c", "start", "", app],
                capture_output=True, text=True, timeout=10,
                shell=True,
            )
            return DesktopResult(
                result2.returncode == 0,
                "open_app", app,
                output=f"Started {app}" if result2.returncode == 0 else "",
                error=result2.stderr[:200] if result2.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return DesktopResult(
                False, "open_app", app,
                error=f"Timeout launching {app}",
            )
        except Exception as e:
            return DesktopResult(False, "open_app", app, error=str(e))

    def read_window(
        self, app_name: str = "", max_depth: int = 5
    ) -> DesktopResult:
        if not self._has_pywinauto():
            return self._fallback_read_window(app_name)
        try:
            import pywinauto
            if app_name:
                app = pywinauto.Application(backend="uia").connect(
                    title_re=f".*{app_name}.*",
                    timeout=5,
                )
                window = app.top_window()
            else:
                from pywinauto import Desktop
                desktop = Desktop(backend="uia")
                windows = desktop.windows()
                if not windows:
                    return DesktopResult(
                        False, "read_window", app_name,
                        error="No windows found",
                    )
                window = windows[0]

            # Extract accessibility tree as text
            lines = []
            self._extract_tree(window.wrapper_object(), lines, 0, max_depth)
            return DesktopResult(
                True, "read_window", app_name,
                output="\n".join(lines),
                window_title=window.window_text(),
            )
        except Exception as e:
            return DesktopResult(
                False, "read_window", app_name, error=str(e)
            )

    def _extract_tree(self, element, lines, depth, max_depth):
        """Recursively extract accessibility tree as text."""
        if depth > max_depth:
            return
        try:
            name = element.window_text() or ""
            ctrl_type = element.element_info.control_type or ""
            if name or ctrl_type:
                indent = "  " * depth
                line = f"{indent}[{ctrl_type}] {name}".strip()
                if line:
                    lines.append(line)
        except Exception:
            pass
        try:
            for child in element.children():
                self._extract_tree(child, lines, depth + 1, max_depth)
        except Exception:
            pass

    def _fallback_read_window(self, app_name: str) -> DesktopResult:
        """Fallback using PowerShell accessibility when pywinauto absent."""
        script = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$ae = [System.Windows.Automation.AutomationElement]::RootElement
$children = $ae.FindAll(
    [System.Windows.Automation.TreeScope]::Children,
    [System.Windows.Automation.Condition]::TrueCondition
)
foreach ($c in $children) {
    Write-Output ("[" + $c.Current.ControlType.ProgrammaticName + "] " + $c.Current.Name)
}
"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True, text=True, timeout=10,
            )
            return DesktopResult(
                True, "read_window", app_name,
                output=result.stdout[:2000],
            )
        except Exception as e:
            return DesktopResult(
                False, "read_window", app_name, error=str(e)
            )

    def click(self, label: str, app_name: str = "") -> DesktopResult:
        if not self._has_pywinauto():
            return DesktopResult(
                False, "click", label,
                error="pywinauto not installed. Run: pip install pywinauto",
            )
        try:
            import pywinauto
            if app_name:
                app = pywinauto.Application(backend="uia").connect(
                    title_re=f".*{app_name}.*", timeout=5
                )
                window = app.top_window()
            else:
                from pywinauto import Desktop
                window = Desktop(backend="uia").windows()[0]

            element = window.child_window(title=label, found_index=0)
            element.click_input()
            return DesktopResult(
                True, "click", label,
                output=f"Clicked '{label}'",
                element_found=True,
            )
        except Exception as e:
            return DesktopResult(False, "click", label, error=str(e))

    def type_text(self, text: str, submit: bool = False) -> DesktopResult:
        try:
            import pywinauto
            from pywinauto.keyboard import send_keys
            # Type using keyboard send_keys
            # Escape special characters for pywinauto
            escaped = text.replace("{", "{{").replace("}", "}}")
            send_keys(escaped, with_spaces=True, pause=0.02)
            if submit:
                send_keys("{ENTER}")
            return DesktopResult(
                True, "type", text,
                output=f"Typed {len(text)} characters"
                + (" and submitted" if submit else ""),
            )
        except ImportError:
            # Fallback: PowerShell SendKeys
            try:
                script = (
                    "Add-Type -AssemblyName System.Windows.Forms; "
                    f"[System.Windows.Forms.SendKeys]::SendWait('{text}')"
                )
                if submit:
                    script += "; [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')"
                subprocess.run(
                    ["powershell", "-Command", script],
                    timeout=10, capture_output=True,
                )
                return DesktopResult(
                    True, "type", text,
                    output=f"Typed {len(text)} characters",
                )
            except Exception as e:
                return DesktopResult(False, "type", text, error=str(e))
        except Exception as e:
            return DesktopResult(False, "type", text, error=str(e))

    def screenshot(self, app_name: str = "") -> DesktopResult:
        try:
            import tempfile
            out = Path(tempfile.mktemp(suffix=".png"))
            script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "Add-Type -AssemblyName System.Drawing; "
                "$screen = [System.Windows.Forms.Screen]::PrimaryScreen; "
                "$bounds = $screen.Bounds; "
                "$bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height); "
                "$graphics = [System.Drawing.Graphics]::FromImage($bitmap); "
                "$graphics.CopyFromScreen($bounds.Location, "
                "[System.Drawing.Point]::Empty, $bounds.Size); "
                f"$bitmap.Save('{str(out)}'); "
                "$graphics.Dispose(); $bitmap.Dispose()"
            )
            subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True, timeout=10,
            )
            if out.exists():
                return DesktopResult(
                    True, "screenshot", app_name or "desktop",
                    screenshot_path=str(out),
                    output=f"Screenshot saved: {out.name}",
                )
            return DesktopResult(
                False, "screenshot", app_name,
                error="Screenshot file not created",
            )
        except Exception as e:
            return DesktopResult(False, "screenshot", app_name, error=str(e))


# ── LINUX BACKEND (Phase 8.7 — NixOS AT-SPI2) ────────────────────────

class LinuxAtspiBackend:
    """
    Desktop Faculty backend using AT-SPI2 on Linux/NixOS.

    Requires: at-spi2-core, python3-pyatspi
    NixOS: services.gnome.at-spi2-core.enable = true;
           environment.systemPackages = [ pkgs.at-spi2-core ];

    This backend is stubbed for Phase 8.7.
    It will be implemented when the system migrates to NixOS.
    The interface is identical to WindowsMCPBackend.
    """

    name = "linux-atspi2"

    def open_app(self, app: str) -> DesktopResult:
        try:
            subprocess.Popen(["xdg-open", app])
            return DesktopResult(True, "open_app", app)
        except Exception as e:
            # Try direct process launch
            try:
                subprocess.Popen([app])
                return DesktopResult(True, "open_app", app)
            except Exception as e2:
                return DesktopResult(
                    False, "open_app", app, error=str(e2)
                )

    def read_window(
        self, app_name: str = "", max_depth: int = 5
    ) -> DesktopResult:
        try:
            import pyatspi
            desktop = pyatspi.Registry.getDesktop(0)
            lines = []
            for app in desktop:
                if app_name and app_name.lower() not in app.name.lower():
                    continue
                self._extract_tree(app, lines, 0, max_depth)
            return DesktopResult(
                True, "read_window", app_name,
                output="\n".join(lines),
            )
        except ImportError:
            return DesktopResult(
                False, "read_window", app_name,
                error="pyatspi not installed. Run: pip install pyatspi2",
            )
        except Exception as e:
            return DesktopResult(
                False, "read_window", app_name, error=str(e)
            )

    def _extract_tree(self, element, lines, depth, max_depth):
        if depth > max_depth:
            return
        try:
            role = element.getRoleName()
            name = element.name or ""
            indent = "  " * depth
            if name or role:
                lines.append(f"{indent}[{role}] {name}".strip())
        except Exception:
            pass
        try:
            for i in range(element.childCount):
                self._extract_tree(
                    element.getChildAtIndex(i), lines, depth + 1, max_depth
                )
        except Exception:
            pass

    def click(self, label: str, app_name: str = "") -> DesktopResult:
        try:
            import pyatspi
            desktop = pyatspi.Registry.getDesktop(0)
            for app in desktop:
                if app_name and app_name.lower() not in app.name.lower():
                    continue
                element = self._find_by_name(app, label)
                if element:
                    element.queryAction().doAction(0)
                    return DesktopResult(
                        True, "click", label, element_found=True,
                        output=f"Clicked '{label}'",
                    )
            return DesktopResult(
                False, "click", label,
                error=f"Element '{label}' not found",
            )
        except ImportError:
            return DesktopResult(
                False, "click", label,
                error="pyatspi not installed",
            )
        except Exception as e:
            return DesktopResult(False, "click", label, error=str(e))

    def _find_by_name(self, element, name: str):
        """Recursively find element by accessibility name."""
        try:
            if element.name.lower() == name.lower():
                return element
        except Exception:
            pass
        try:
            for i in range(element.childCount):
                child = element.getChildAtIndex(i)
                found = self._find_by_name(child, name)
                if found:
                    return found
        except Exception:
            pass
        return None

    def type_text(self, text: str, submit: bool = False) -> DesktopResult:
        try:
            subprocess.run(
                ["xdotool", "type", "--clearmodifiers", text],
                capture_output=True, timeout=10,
            )
            if submit:
                subprocess.run(
                    ["xdotool", "key", "Return"],
                    capture_output=True, timeout=5,
                )
            return DesktopResult(True, "type", text)
        except FileNotFoundError:
            # Try ydotool (Wayland)
            try:
                subprocess.run(
                    ["ydotool", "type", text],
                    capture_output=True, timeout=10,
                )
                return DesktopResult(True, "type", text)
            except Exception as e:
                return DesktopResult(
                    False, "type", text,
                    error="xdotool/ydotool not available: " + str(e),
                )
        except Exception as e:
            return DesktopResult(False, "type", text, error=str(e))

    def screenshot(self, app_name: str = "") -> DesktopResult:
        import tempfile
        out = Path(tempfile.mktemp(suffix=".png"))
        try:
            subprocess.run(
                ["scrot", str(out)],
                capture_output=True, timeout=10,
            )
            if out.exists():
                return DesktopResult(
                    True, "screenshot", app_name or "desktop",
                    screenshot_path=str(out),
                )
            # Fallback: gnome-screenshot
            subprocess.run(
                ["gnome-screenshot", "-f", str(out)],
                capture_output=True, timeout=10,
            )
            return DesktopResult(
                out.exists(), "screenshot", app_name,
                screenshot_path=str(out) if out.exists() else "",
                error=None if out.exists() else "Screenshot failed",
            )
        except Exception as e:
            return DesktopResult(False, "screenshot", app_name, error=str(e))


# ── FALLBACK BACKEND ─────────────────────────────────────────────────

class FallbackBackend:
    """Fallback for unsupported platforms."""

    def __init__(self, os_name: str) -> None:
        self.name = f"fallback-{os_name.lower()}"
        self._os = os_name

    def _unsupported(self, tool: str, query: str) -> DesktopResult:
        return DesktopResult(
            False, tool, query,
            error=f"Desktop Faculty not supported on {self._os}",
        )

    def open_app(self, app: str) -> DesktopResult:
        return self._unsupported("open_app", app)

    def read_window(self, app_name: str = "", max_depth: int = 5) -> DesktopResult:
        return self._unsupported("read_window", app_name)

    def click(self, label: str, app_name: str = "") -> DesktopResult:
        return self._unsupported("click", label)

    def type_text(self, text: str, submit: bool = False) -> DesktopResult:
        return self._unsupported("type", text)

    def screenshot(self, app_name: str = "") -> DesktopResult:
        return self._unsupported("screenshot", app_name)
```

### Task 2 — Register Desktop tools in tools.json

Add to inanna/config/tools.json:

```json
"desktop_open_app": {
  "display_name": "Open Application",
  "description": "Open any installed application by name",
  "category": "desktop",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "app": "Application name (e.g. whatsapp, firefox, libreoffice)"
  }
},
"desktop_read_window": {
  "display_name": "Read Window Content",
  "description": "Read accessible content from any application window",
  "category": "desktop",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "app_name": "Application name filter (optional)",
    "max_depth": "UI tree depth (default 5)"
  }
},
"desktop_click": {
  "display_name": "Click UI Element",
  "description": "Click a UI element by its accessibility name",
  "category": "desktop",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "label": "Accessibility name of the element to click",
    "app_name": "Application to target (optional)"
  }
},
"desktop_type": {
  "display_name": "Type Text",
  "description": "Type text into the focused UI element",
  "category": "desktop",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "text": "Text to type",
    "submit": "Send Enter after typing (default: false)"
  }
},
"desktop_screenshot": {
  "display_name": "Take Screenshot",
  "description": "Capture the current screen state",
  "category": "desktop",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "app_name": "Application to capture (optional, defaults to full screen)"
  }
}
```

### Task 3 — Wire DesktopFaculty into server.py and main.py

Add DESKTOP_TOOL_NAMES set:
```python
DESKTOP_TOOL_NAMES = {
    "desktop_open_app",
    "desktop_read_window",
    "desktop_click",
    "desktop_type",
    "desktop_screenshot",
}
```

Add to execute_tool_request():
```python
if tool_name in DESKTOP_TOOL_NAMES:
    return run_desktop_tool(
        desktop_faculty or DesktopFaculty(),
        tool_name,
        params,
    )
```

Add run_desktop_tool() function:
```python
def run_desktop_tool(
    desktop_faculty: DesktopFaculty,
    tool_name: str,
    params: dict,
) -> ToolResult:
    if tool_name == "desktop_open_app":
        r = desktop_faculty.open_app(str(params.get("app", "")))
    elif tool_name == "desktop_read_window":
        r = desktop_faculty.read_window(
            str(params.get("app_name", "")),
            int(params.get("max_depth", 5)),
        )
    elif tool_name == "desktop_click":
        r = desktop_faculty.click(
            str(params.get("label", "")),
            str(params.get("app_name", "")),
        )
    elif tool_name == "desktop_type":
        r = desktop_faculty.type_text(
            str(params.get("text", "")),
            bool(params.get("submit", False)),
        )
    elif tool_name == "desktop_screenshot":
        r = desktop_faculty.screenshot(str(params.get("app_name", "")))
    else:
        r = DesktopResult(False, tool_name, "", error="Unknown desktop tool")

    return ToolResult(
        tool=tool_name,
        query=r.query,
        success=r.success,
        data={
            "output": r.output,
            "window_title": r.window_title,
            "screenshot_path": r.screenshot_path,
            "consequential": r.consequential,
        },
        error=r.error,
        formatted=desktop_faculty.format_result(r),
    )
```

Instantiate in InterfaceServer.__init__:
```python
from core.desktop_faculty import DesktopFaculty
self.desktop_faculty = DesktopFaculty()
```

### Task 4 — Natural language routing

Add domain hints for desktop tools in governance_signals.json:
```json
"desktop": [
  "open app", "launch app", "start app", "open application",
  "read window", "what is in", "what does", "show me the screen",
  "click", "press button", "tap", "select",
  "type", "write", "enter text", "fill in",
  "screenshot", "take a photo of screen", "capture screen",
  "switch to", "focus on"
]
```

Add extract_desktop_tool_request() in main.py:
Pattern matching for:
  "open [app]" → desktop_open_app
  "read [app] window" → desktop_read_window
  "click [label]" → desktop_click
  "type [text]" → desktop_type
  "take a screenshot" → desktop_screenshot

### Task 5 — Add pywinauto to requirements.txt

Add:
```
# Desktop Faculty (Windows backend)
pywinauto>=0.6.8
```

Note: pywinauto is optional — DesktopFaculty gracefully falls back
to PowerShell-based automation when pywinauto is not installed.

### Task 6 — Update help_system.py

Add DESKTOP section to HELP_COMMON:
```
  DESKTOP (speak naturally or use commands)
    "open firefox"                Open any application
    "read the whatsapp window"    Read window content
    "click the Send button"       Click any UI element (approval)
    "type hello world"            Type text (approval)
    "take a screenshot"           Capture screen
    (consequential: send/delete always require approval)
```

### Task 7 — Update identity.py

CURRENT_PHASE = "Cycle 8 - Phase 8.1 - The Desktop Faculty Core"

### Task 8 — Tests

Create inanna/tests/test_desktop_faculty.py:
  - DesktopFaculty instantiates without error
  - backend_name is non-empty string
  - is_consequential_label("send") returns True
  - is_consequential_label("delete") returns True
  - is_consequential_label("read") returns False
  - is_consequential_label("Send Message") returns True (case-insensitive)
  - WindowsMCPBackend instantiates
  - LinuxAtspiBackend instantiates
  - FallbackBackend instantiates with custom OS name
  - FallbackBackend.open_app returns success=False
  - DesktopResult dataclass creates correctly
  - format_result for open_app (success) has app name
  - format_result for error shows "desktop > error:"
  - format_result for read_window includes "window content"
  - format_result for click (consequential) includes "consequential"
  - DESKTOP_TOOL_NAMES contains all 5 tools
  - desktop_open_app in tools.json with requires_approval=True
  - desktop_read_window in tools.json with requires_approval=False
  - desktop_screenshot in tools.json with requires_approval=False

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/core/desktop_faculty.py           <- NEW
inanna/main.py                           <- MODIFY: DESKTOP_TOOL_NAMES, routing
inanna/ui/server.py                      <- MODIFY: DesktopFaculty instantiation
inanna/config/tools.json                 <- MODIFY: add 5 desktop tools
inanna/config/governance_signals.json    <- MODIFY: desktop domain hints
inanna/requirements.txt                  <- MODIFY: add pywinauto
inanna/core/help_system.py               <- MODIFY: desktop section
inanna/identity.py                       <- MODIFY: CURRENT_PHASE
inanna/tests/test_desktop_faculty.py     <- NEW
inanna/tests/test_identity.py            <- MODIFY

---

## What You Are NOT Building

- No app-specific workflows (WhatsApp, LibreOffice, etc.) — Phase 8.2+
- No actual UI automation calls in tests (all offline)
- No vision/screenshot analysis — text accessibility only
- No voice changes
- No auth changes
- Do NOT call pywinauto in tests — only test class structure

---

## Definition of Done

- [ ] core/desktop_faculty.py with DesktopFaculty + 3 backends
- [ ] 5 desktop tools in tools.json (23 total)
- [ ] Desktop domain hints in governance_signals.json
- [ ] DesktopFaculty wired into server.py and main.py
- [ ] pywinauto in requirements.txt
- [ ] help_system.py updated with desktop section
- [ ] CURRENT_PHASE updated to Cycle 8 Phase 8.1
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle8-phase1-complete

---

## Handoff

Commit: cycle8-phase1-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE8_PHASE1_REPORT.md
Stop. Do not begin Phase 8.2 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: INANNA NAMMU*
*Date: 2026-04-21*
*Cycle 8 begins.*
*INANNA gains hands that reach beyond the terminal.*
*Five abstract tools. Three platform backends.*
*Every application on the computer becomes reachable.*
*WhatsApp. LibreOffice. Email. Browser. Calendar.*
*All through the same channel.*
*With your word, she reaches.*
*Without your word, she observes and waits.*

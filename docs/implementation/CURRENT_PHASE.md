# CURRENT PHASE: Cycle 8 - Phase 8.5 - Browser Faculty
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-22**
**Cycle: 8 - The Desktop Bridge**
**Replaces: Cycle 8 Phase 8.4 - Document Faculty (COMPLETE)**

---

## MANDATORY READING — in this exact order

1. docs/platform_architecture.md
2. docs/cycle8_master_plan.md
3. docs/cycle9_master_plan.md
4. docs/implementation/CURRENT_PHASE.md (this file)
5. CODEX_DOCTRINE.md
6. ABSOLUTE_PROTOCOL.md

All documentation in this phase must be complete and permanent.

---

## Current System State

Browsers installed:
  Firefox    (firefox.exe)
  Chrome     (chrome.exe)
  Edge       (Microsoft.Edge v147.0.3912.72)

Python libraries available:
  playwright: INSTALLED  ← primary browser automation
  httpx:      INSTALLED  ← fast HTTP client for direct fetching
  urllib:     stdlib     ← fallback, always available
  selenium:   not installed
  beautifulsoup4: not installed  ← must install

Tools registered: 35 across 9 categories
Tests passing: 543
Phase: Cycle 8 - Phase 8.4 - Document Faculty

---

## What This Phase Is

The Browser Faculty gives INANNA the ability to:
  - Fetch web pages and extract readable content
  - Navigate to URLs
  - Search the web for current information
  - Fill forms and click buttons (governed)
  - Read page content without opening a visual browser

This is different from web_search (which queries a search API).
The Browser Faculty works with any URL — local, intranet, public.

---

## Architecture: Two Levels

### Level 1 — Headless HTTP (primary, no browser needed)

For reading web pages, INANNA does NOT need to open Firefox.
It fetches the URL directly with httpx and parses the HTML.
This is fast, reliable, and works without any visible browser.

```
"read the page at https://example.com"
  → BrowserDirectFetcher.fetch(url)
  → httpx.get(url) → HTML
  → extract readable text (strip tags)
  → return PageRecord(title, content, url)
  → CROWN summarizes
```

This covers 90% of use cases.
No UI automation. No browser process. No screenshots.
Works on any hardware. Works on NixOS headlessly.

### Level 2 — Playwright (for JS-heavy pages and form interaction)

Some pages require JavaScript to render content.
For these, Playwright opens a headless browser process,
navigates, waits for JS, and reads the DOM.

```
"fill the contact form at https://example.com/contact"
  → PlaywrightBrowser.navigate(url)
  → page.fill('#name', 'ZAERA')   [proposal required]
  → page.click('submit')          [mandatory proposal]
  → return result
```

Playwright is used only when Level 1 is insufficient.
Playwright is HEADLESS by default — no visible browser window.
Using it with a visible browser requires explicit request.

### Level 3 — Desktop Faculty (visible browser control)

When the user explicitly wants to control the visible Firefox
window (e.g. "open this in Firefox"), the Desktop Faculty
handles it via AT-SPI2/Windows UI Automation.

---

## Governance Model

```
OBSERVATION (no proposal needed):
  - Fetching any public URL and reading content
  - Reading current page title/URL
  - Searching for information

LIGHT ACTION (proposal required):
  - Navigating to a URL in a visible browser
  - Opening a new browser tab
  - Typing into a search field

CONSEQUENTIAL ACTION (always mandatory proposal):
  - Submitting any form
  - Clicking "Submit", "Buy", "Confirm", "Delete"
  - Filling in personal data fields
  - Any action that sends data to a server

FORBIDDEN (never, regardless of approval):
  - Entering passwords into web forms
  - Accessing banking or payment pages
  - Actions involving financial transactions
  - Bypassing CAPTCHAs
```

---

## What You Are Building

### Task 1 — Install missing libraries

```bash
pip install beautifulsoup4 lxml --break-system-packages
```

Playwright browsers (headless Chromium):
```bash
py -3 -m playwright install chromium
```

Note: if playwright install fails (requires network),
implement a graceful fallback to httpx-only mode.

### Task 2 — inanna/core/browser_workflows.py

Create: inanna/core/browser_workflows.py

```python
"""
INANNA NYX Browser Faculty
Fetches web pages, reads content, and interacts with web UIs.

Two-level architecture:
  Level 1: BrowserDirectFetcher — httpx + BeautifulSoup
           No browser process needed. Fast. Works headlessly.
           Primary approach for reading public web pages.

  Level 2: PlaywrightBrowser — headless Chromium via Playwright
           For JS-heavy pages and form interaction.
           Used only when Level 1 is insufficient.

Governance:
  Fetching/reading URLs: no proposal (observation)
  Navigating visible browser: proposal required
  Submitting forms: ALWAYS mandatory proposal
  Entering passwords: FORBIDDEN

See docs/platform_architecture.md for platform context.
See docs/cycle8_master_plan.md for Cycle 8 architecture.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

from core.desktop_faculty import DesktopFaculty


@dataclass
class PageRecord:
    """Structured content extracted from a web page."""
    url: str = ""
    title: str = ""
    content: str = ""      # readable text, stripped of HTML
    links: list[str] = field(default_factory=list)
    word_count: int = 0
    status_code: int = 0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.content)

    def summary_line(self) -> str:
        parts = [f"browser > {self.url[:60]}"]
        if self.title:
            parts.append(self.title[:50])
        if self.word_count:
            parts.append(f"{self.word_count} words")
        return " | ".join(parts)


@dataclass
class BrowserActionResult:
    """Result of a browser interaction (click, fill, navigate)."""
    success: bool
    action: str = ""       # navigate | fill | click | search
    url: str = ""
    output: str = ""
    consequential: bool = False
    error: Optional[str] = None


# URL safety check — prevents accessing sensitive local resources
FORBIDDEN_URL_PATTERNS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "file://",
    "192.168.",
    "10.",
    "172.16.",
]


def is_safe_url(url: str) -> bool:
    """
    Returns True if the URL is safe to fetch.
    Blocks localhost, internal networks, and file:// URLs
    to prevent SSRF and local file disclosure.
    Exception: allow localhost only for explicitly configured
    internal services (future: whitelist via config).
    """
    url_lower = url.lower()
    return not any(pattern in url_lower for pattern in FORBIDDEN_URL_PATTERNS)


def clean_html_to_text(html: str) -> str:
    """
    Extract readable text from HTML.
    Uses BeautifulSoup if available, falls back to regex.
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        # Remove script, style, nav, footer
        for tag in soup(["script", "style", "nav", "footer",
                         "header", "aside", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive blank lines
        import re
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except ImportError:
        # Fallback: simple regex tag stripper
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()


def extract_title(html: str) -> str:
    """Extract page title from HTML."""
    import re
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


# ── LEVEL 1: DIRECT HTTP FETCHER ─────────────────────────────────────

class BrowserDirectFetcher:
    """
    Fetches web pages directly using httpx.
    No browser process. Fast. Headless.
    Primary approach for reading public web content.
    """

    DEFAULT_TIMEOUT = 15  # seconds
    MAX_CONTENT_BYTES = 2 * 1024 * 1024  # 2MB

    def fetch(self, url: str) -> PageRecord:
        """
        Fetch a URL and return readable content.
        No proposal needed — observation only.
        """
        if not is_safe_url(url):
            return PageRecord(
                url=url,
                error=f"URL blocked: internal/local addresses not accessible"
            )

        # Ensure URL has scheme
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            import httpx
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; INANNA-NYX/1.0; "
                    "+https://github.com/ZeroAbsolutePrime/INANNA)"
                ),
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Language": "en,es;q=0.9,ca;q=0.8",
            }
            with httpx.Client(
                timeout=self.DEFAULT_TIMEOUT,
                follow_redirects=True,
                headers=headers,
            ) as client:
                response = client.get(url)

            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                # Non-HTML content — return raw or note
                if "application/pdf" in content_type:
                    return PageRecord(
                        url=str(response.url),
                        title="PDF document",
                        content=f"[PDF at {url}] — use doc_read to read PDF files.",
                        status_code=response.status_code,
                    )
                return PageRecord(
                    url=str(response.url),
                    title=f"Non-HTML content ({content_type})",
                    content=f"Content type: {content_type}",
                    status_code=response.status_code,
                )

            html = response.text[:self.MAX_CONTENT_BYTES]
            title = extract_title(html)
            text = clean_html_to_text(html)

            return PageRecord(
                url=str(response.url),
                title=title,
                content=text[:8000],   # cap at 8000 chars for CROWN
                word_count=len(text.split()),
                status_code=response.status_code,
            )

        except ImportError:
            return self._fetch_urllib(url)
        except Exception as e:
            return PageRecord(url=url, error=str(e))

    def _fetch_urllib(self, url: str) -> PageRecord:
        """Stdlib fallback when httpx not available."""
        import urllib.request
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "INANNA-NYX/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                html = r.read(self.MAX_CONTENT_BYTES).decode("utf-8", errors="replace")
            title = extract_title(html)
            text = clean_html_to_text(html)
            return PageRecord(
                url=url, title=title,
                content=text[:8000],
                word_count=len(text.split()),
                status_code=200,
            )
        except Exception as e:
            return PageRecord(url=url, error=str(e))

    def search(self, query: str, engine: str = "duckduckgo") -> PageRecord:
        """
        Perform a web search and return results page content.
        Uses DuckDuckGo HTML search (no API key required).
        No proposal needed.
        """
        import urllib.parse
        if engine == "duckduckgo":
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        else:
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        record = self.fetch(url)
        record.url = f"search:{query}"
        return record


# ── LEVEL 2: PLAYWRIGHT BROWSER ──────────────────────────────────────

class PlaywrightBrowser:
    """
    Headless browser automation via Playwright.
    Used for JS-heavy pages and form interaction.
    Requires: playwright + chromium install.

    All form submission requires mandatory proposal approval.
    Passwords and financial data: FORBIDDEN.
    """

    def __init__(self) -> None:
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is None:
            try:
                import playwright
                self._available = True
            except ImportError:
                self._available = False
        return self._available

    def fetch_js(self, url: str) -> PageRecord:
        """
        Fetch a JS-rendered page using headless Chromium.
        Returns readable text after JS execution.
        No proposal needed — observation.
        """
        if not is_safe_url(url):
            return PageRecord(url=url, error="URL blocked: internal address")

        if not self.is_available():
            return PageRecord(
                url=url,
                error="Playwright not available. Run: py -3 -m playwright install chromium"
            )

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                title = page.title()
                content = page.inner_text("body")
                browser.close()
            return PageRecord(
                url=url,
                title=title,
                content=content[:8000],
                word_count=len(content.split()),
                status_code=200,
            )
        except Exception as e:
            return PageRecord(url=url, error=str(e))

    def navigate_and_fill(
        self,
        url: str,
        fields: dict[str, str],
    ) -> BrowserActionResult:
        """
        Navigate to URL and fill form fields.
        REQUIRES proposal approval for each field.
        Submitting the form requires MANDATORY separate proposal.
        """
        if not self.is_available():
            return BrowserActionResult(
                success=False, action="fill",
                error="Playwright not available"
            )
        # Implementation deferred to Phase 8.5 extended
        # (requires multi-step proposal flow)
        return BrowserActionResult(
            success=False, action="fill",
            error="Form filling not yet implemented in this phase"
        )


# ── BROWSER WORKFLOWS ────────────────────────────────────────────────

class BrowserWorkflows:
    """
    Orchestrates browser operations.
    Uses BrowserDirectFetcher (Level 1) as primary.
    Uses PlaywrightBrowser (Level 2) for JS-heavy pages.
    Uses Desktop Faculty (Level 3) for visible browser control.
    """

    def __init__(self, desktop: DesktopFaculty) -> None:
        self.desktop = desktop
        self.fetcher = BrowserDirectFetcher()
        self.playwright = PlaywrightBrowser()

    def read_page(self, url: str, js: bool = False) -> PageRecord:
        """
        Read a web page and return structured content.
        js=True forces Playwright for JS-heavy pages.
        No proposal needed — observation only.
        """
        if js and self.playwright.is_available():
            return self.playwright.fetch_js(url)
        return self.fetcher.fetch(url)

    def search_web(self, query: str) -> PageRecord:
        """
        Search the web and return results.
        No proposal needed — observation only.
        """
        return self.fetcher.search(query)

    def open_in_browser(
        self, url: str, browser: str = "firefox"
    ) -> BrowserActionResult:
        """
        Open URL in a visible browser window.
        Requires proposal approval — light action.
        """
        result = self.desktop.open_app(f"{browser} {url}")
        return BrowserActionResult(
            success=result.success,
            action="navigate",
            url=url,
            output=f"Opened {url} in {browser}",
            error=result.error,
        )

    def format_page_result(self, record: PageRecord) -> str:
        """Format PageRecord for CROWN."""
        if not record.success:
            return f"browser > error: {record.error}"
        lines = [
            f"browser > {record.url}",
            f"Title: {record.title}" if record.title else "",
            f"Words: {record.word_count}",
            "",
            "CONTENT:",
            record.content[:3000],
        ]
        return "\n".join(l for l in lines if l is not None)

    def format_search_result(self, record: PageRecord, query: str) -> str:
        """Format search result for CROWN."""
        if not record.success:
            return f"browser > search error: {record.error}"
        return (
            f"browser > search results for: {query}\n"
            f"{record.content[:3000]}"
        )
```

### Task 3 — Register browser tools in tools.json

Add to inanna/config/tools.json under category "browser":

```json
"browser_read": {
  "display_name": "Read Web Page",
  "description": "Fetch and read any web page URL",
  "category": "browser",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "url": "URL to fetch (https:// added if missing)",
    "js": "Use JS rendering for dynamic pages (default: false)"
  }
},
"browser_search": {
  "display_name": "Web Search",
  "description": "Search the web via DuckDuckGo and return results",
  "category": "browser",
  "requires_approval": false,
  "enabled": true,
  "parameters": {
    "query": "Search query"
  }
},
"browser_open": {
  "display_name": "Open in Browser",
  "description": "Open a URL in Firefox, Chrome, or Edge",
  "category": "browser",
  "requires_approval": true,
  "enabled": true,
  "parameters": {
    "url": "URL to open",
    "browser": "Browser to use: firefox, chrome, edge (default: firefox)"
  }
}
```

Total tools after this phase: 38

### Task 4 — Wire BrowserWorkflows into server.py and main.py

Add BROWSER_TOOL_NAMES:
```python
BROWSER_TOOL_NAMES = {
    "browser_read",
    "browser_search",
    "browser_open",
}
```

Instantiate in InterfaceServer.__init__:
```python
from core.browser_workflows import BrowserWorkflows
self.browser_workflows = BrowserWorkflows(self.desktop_faculty)
```

Add run_browser_tool() following the established pattern.

For browser_read and browser_search: no proposal.
For browser_open: proposal required.

Note on web_search vs browser_search:
  web_search (existing): calls the search API via the engine
  browser_search (new): fetches DuckDuckGo HTML results directly
  Both coexist — web_search is preferred when API is available

### Task 5 — Natural language routing in main.py

Add browser domain hints to governance_signals.json:
```json
"browser": [
  "open url", "go to", "navigate to", "visit",
  "read the page", "what does the page say",
  "fetch", "browse to", "open website", "open site",
  "search the web", "look up online", "find online",
  "what is on", "read the website",
  "open firefox", "open chrome", "open edge",
  "open in browser", "show me the website"
]
```

Add extract_browser_tool_request() in main.py:

Patterns:
  "go to [url]" → browser_open(url=url)
  "open [url] in firefox" → browser_open(url, browser=firefox)
  "read the page at [url]" → browser_read(url=url)
  "fetch [url]" → browser_read(url=url)
  "search the web for [query]" → browser_search(query=query)
  "look up [query] online" → browser_search(query=query)
  "what is [topic]?" → browser_search(query=topic)
    (only when web_search is not triggered first)

### Task 6 — Update help_system.py

Add BROWSER section to HELP_COMMON:
```
  BROWSER (Firefox, Chrome, Edge)
    "read the page at https://example.com"
                                       Fetch and read URL (no approval)
    "search the web for NixOS install" Web search (no approval)
    "go to https://example.com"        Open in Firefox (approval)
    "open https://example.com in chrome"
                                       Open in Chrome (approval)

  Note: passwords and financial forms are never accessible
  Internal/local addresses (localhost, 192.168.x.x) are blocked
```

### Task 7 — Update identity.py

CURRENT_PHASE = "Cycle 8 - Phase 8.5 - Browser Faculty"

### Task 8 — Tests (all offline — no actual network calls)

Create inanna/tests/test_browser_workflows.py (20 tests):

  - BrowserWorkflows instantiates
  - BrowserDirectFetcher instantiates
  - PlaywrightBrowser instantiates
  - is_safe_url("https://example.com") returns True
  - is_safe_url("http://localhost:8080") returns False
  - is_safe_url("http://192.168.1.1") returns False
  - is_safe_url("file:///etc/passwd") returns False
  - clean_html_to_text removes script and style tags
  - clean_html_to_text preserves text content
  - extract_title finds title in HTML
  - extract_title returns empty string when no title
  - PageRecord defaults are correct
  - PageRecord.success True when content present
  - PageRecord.success False when error set
  - PageRecord.summary_line includes URL
  - BrowserDirectFetcher._fetch_urllib handles connection error gracefully
    (mock urllib to raise URLError)
  - BrowserDirectFetcher.fetch blocks internal URLs
  - BROWSER_TOOL_NAMES contains all 3 tools
  - browser_read in tools.json with requires_approval=False
  - browser_open in tools.json with requires_approval=True

### Task 9 — docs/nixos_browser_faculty.md (mandatory)

Create: docs/nixos_browser_faculty.md

Document:
  - NixOS packages for browser libraries:
      python311Packages.httpx
      python311Packages.beautifulsoup4
      python311Packages.lxml
      python311Packages.playwright (note: browser binaries separate)
  - Firefox NixOS package: programs.firefox.enable = true
  - Playwright on NixOS: special considerations for browser binaries
  - Environment variables for browser paths
  - How BrowserDirectFetcher works without a visible browser
  - Level 1 vs Level 2 on NixOS

Update test_identity.py, test_operator.py, test_commands.py.

---

## Permitted file changes

inanna/core/browser_workflows.py       <- NEW
inanna/main.py                         <- MODIFY
inanna/ui/server.py                    <- MODIFY
inanna/config/tools.json               <- MODIFY: add 3 browser tools
inanna/config/governance_signals.json  <- MODIFY: browser hints
inanna/requirements.txt                <- MODIFY: beautifulsoup4, lxml
inanna/core/help_system.py             <- MODIFY: browser section
inanna/identity.py                     <- MODIFY
inanna/tests/test_browser_workflows.py <- NEW
inanna/tests/test_identity.py          <- MODIFY
inanna/tests/test_operator.py          <- MODIFY
inanna/tests/test_commands.py          <- MODIFY
docs/nixos_browser_faculty.md          <- NEW (mandatory)

---

## What You Are NOT Building

- No form filling in this phase (future extension)
- No cookie/session management
- No login to web services via browser
- No screenshot analysis (Level 1 is text-only)
- No calendar (Phase 8.6)
- No voice changes, no auth changes
- Do NOT make actual network calls in tests

---

## Definition of Done

- [ ] core/browser_workflows.py complete
- [ ] beautifulsoup4 + lxml installed
- [ ] playwright chromium installed (graceful fallback if fails)
- [ ] 3 browser tools in tools.json (38 total)
- [ ] is_safe_url blocks localhost and internal IPs
- [ ] BrowserWorkflows wired into server.py and main.py
- [ ] Natural language routing for browser commands
- [ ] help_system.py updated
- [ ] docs/nixos_browser_faculty.md written
- [ ] CURRENT_PHASE = "Cycle 8 - Phase 8.5 - Browser Faculty"
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle8-phase5-complete

---

## Handoff

Commit: cycle8-phase5-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE8_PHASE5_REPORT.md

The report MUST include:
  - Whether Playwright chromium installed successfully
  - Which fallback is active if not
  - Test of browser_read against a real URL (if network available)
  - NixOS equivalents for all new dependencies

Stop. Do not begin Phase 8.6 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-22*
*The browser is the window to the world.*
*INANNA reads through it.*
*INANNA never touches passwords.*
*INANNA never submits without your word.*
*The web is observation.*
*Action requires blessing.*

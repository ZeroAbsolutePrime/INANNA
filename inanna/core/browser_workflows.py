"""
INANNA NYX Browser Faculty
Fetches web pages, reads content, and interacts with web UIs.

Two-level architecture:
  Level 1: BrowserDirectFetcher - httpx + BeautifulSoup
           No browser process needed. Fast. Works headlessly.
           Primary approach for reading public web pages.

  Level 2: PlaywrightBrowser - headless Chromium via Playwright
           For JS-heavy pages and form interaction.
           Used only when Level 1 is insufficient.

Governance:
  Fetching/reading URLs: no proposal (observation)
  Navigating visible browser: proposal required
  Submitting forms: ALWAYS mandatory proposal
  Entering passwords: FORBIDDEN
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import quote, urlparse

from core.desktop_faculty import DesktopFaculty


@dataclass
class PageRecord:
    """Structured content extracted from a web page."""

    url: str = ""
    title: str = ""
    content: str = ""
    links: list[str] = field(default_factory=list)
    word_count: int = 0
    status_code: int = 0
    error: str | None = None

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
    """Result of a browser interaction."""

    success: bool
    action: str = ""
    url: str = ""
    output: str = ""
    consequential: bool = False
    error: str | None = None


@dataclass
class BrowserComprehension:
    """Structured summary of a fetched web page or search result."""

    url: str = ""
    title: str = ""
    word_count: int = 0
    is_search: bool = False
    query: str = ""
    excerpt: str = ""
    key_topics: list[str] = field(default_factory=list)
    is_pdf: bool = False
    status_code: int = 0
    error: str | None = None

    def to_crown_context(self) -> str:
        if self.error:
            return f"browser > error: {self.error}"
        if self.is_search:
            lines = [
                f"WEB SEARCH: {self.query!r}",
                f"Results from: {self.url}",
                "",
                f"CONTENT ({self.word_count} words):",
                self.excerpt,
            ]
            return "\n".join(line for line in lines if line is not None)

        lines = [
            f"WEB PAGE: {self.title or self.url}",
            f"URL: {self.url}",
            f"Size: {self.word_count} words",
        ]
        if self.key_topics:
            lines.append(f"Topics: {', '.join(self.key_topics[:5])}")
        lines.extend(["", "CONTENT:", self.excerpt])
        return "\n".join(line for line in lines if line is not None)


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
    """Block local, file, and private-network URLs."""

    url_lower = str(url or "").strip().lower()
    return bool(url_lower) and not any(pattern in url_lower for pattern in FORBIDDEN_URL_PATTERNS)


def clean_html_to_text(html: str) -> str:
    """Extract readable text from HTML."""

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return re.sub(r"\n{3,}", "\n\n", text).strip()
    except Exception:
        text = re.sub(r"<script.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s{2,}", " ", text).strip()


def extract_title(html: str) -> str:
    """Extract page title from HTML."""

    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def _extract_links_from_html(html: str) -> list[str]:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", "")).strip()
            if href and href not in links:
                links.append(href)
            if len(links) >= 25:
                break
        return links
    except Exception:
        return []


def build_browser_comprehension(
    record: PageRecord,
    query: str = "",
    is_search: bool = False,
) -> BrowserComprehension:
    """Build deterministic browser comprehension from a page record."""

    if not record.success:
        return BrowserComprehension(error=record.error or "Unknown error")

    content = str(record.content or "")
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    excerpt_lines: list[str] = []
    total_chars = 0
    for line in lines:
        if total_chars >= 400:
            break
        remaining = max(0, 400 - total_chars)
        excerpt_lines.append(line[:remaining])
        total_chars += len(excerpt_lines[-1])
    excerpt = "\n".join(excerpt_lines).strip()[:400]

    topic_candidates = re.findall(r"\b[A-Z][a-z]{2,}\b", content[:2000])
    counts = Counter(topic_candidates)
    key_topics = [
        word
        for word, _ in counts.most_common(8)
        if word.lower()
        not in {"the", "this", "that", "with", "from", "your", "have", "will", "are", "for"}
    ][:6]

    lowered_title = str(record.title or "").lower()
    lowered_content = content.lower()
    is_pdf = "pdf" in lowered_title or content.startswith("[PDF at") or "application/pdf" in lowered_content

    return BrowserComprehension(
        url=record.url,
        title=record.title,
        word_count=record.word_count,
        is_search=is_search,
        query=query,
        excerpt=excerpt,
        key_topics=key_topics,
        is_pdf=is_pdf,
        status_code=record.status_code,
    )


class BrowserDirectFetcher:
    """
    Fetches web pages directly using httpx.
    No browser process. Fast. Headless.
    """

    DEFAULT_TIMEOUT = 15
    MAX_CONTENT_BYTES = 2 * 1024 * 1024

    def fetch(self, url: str) -> PageRecord:
        normalized_url = str(url or "").strip()
        if not normalized_url:
            return PageRecord(url="", error="Empty URL.")
        if not normalized_url.startswith(("http://", "https://")):
            normalized_url = "https://" + normalized_url
        if not is_safe_url(normalized_url):
            return PageRecord(
                url=normalized_url,
                error="URL blocked: internal/local addresses not accessible",
            )

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
                response = client.get(normalized_url)
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                if "application/pdf" in content_type:
                    return PageRecord(
                        url=str(response.url),
                        title="PDF document",
                        content=f"[PDF at {normalized_url}] - use doc_read to read PDF files.",
                        word_count=11,
                        status_code=response.status_code,
                    )
                return PageRecord(
                    url=str(response.url),
                    title=f"Non-HTML content ({content_type})",
                    content=f"Content type: {content_type}",
                    word_count=3,
                    status_code=response.status_code,
                )
            html = response.text[: self.MAX_CONTENT_BYTES]
            return PageRecord(
                url=str(response.url),
                title=extract_title(html),
                content=clean_html_to_text(html)[:8000],
                links=_extract_links_from_html(html),
                word_count=len(clean_html_to_text(html).split()),
                status_code=response.status_code,
            )
        except ImportError:
            return self._fetch_urllib(normalized_url)
        except Exception as exc:
            return PageRecord(url=normalized_url, error=str(exc))

    def _fetch_urllib(self, url: str) -> PageRecord:
        import urllib.request

        try:
            request = urllib.request.Request(url, headers={"User-Agent": "INANNA-NYX/1.0"})
            with urllib.request.urlopen(request, timeout=10) as response:
                html = response.read(self.MAX_CONTENT_BYTES).decode("utf-8", errors="replace")
            text = clean_html_to_text(html)
            return PageRecord(
                url=url,
                title=extract_title(html),
                content=text[:8000],
                links=_extract_links_from_html(html),
                word_count=len(text.split()),
                status_code=200,
            )
        except Exception as exc:
            return PageRecord(url=url, error=str(exc))

    def search(self, query: str, engine: str = "duckduckgo") -> PageRecord:
        cleaned_query = str(query or "").strip()
        if not cleaned_query:
            return PageRecord(url="search:", error="Empty search query.")
        if engine == "duckduckgo":
            url = f"https://html.duckduckgo.com/html/?q={quote(cleaned_query)}"
        else:
            url = f"https://www.google.com/search?q={quote(cleaned_query)}"
        record = self.fetch(url)
        record.url = f"search:{cleaned_query}"
        return record


class PlaywrightBrowser:
    """
    Headless browser automation via Playwright.
    Used for JS-heavy pages and form interaction.
    """

    def __init__(self) -> None:
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is None:
            try:
                from playwright.sync_api import sync_playwright  # noqa: F401

                self._available = True
            except Exception:
                self._available = False
        return self._available

    def fetch_js(self, url: str) -> PageRecord:
        normalized_url = str(url or "").strip()
        if not normalized_url:
            return PageRecord(url="", error="Empty URL.")
        if not normalized_url.startswith(("http://", "https://")):
            normalized_url = "https://" + normalized_url
        if not is_safe_url(normalized_url):
            return PageRecord(url=normalized_url, error="URL blocked: internal/local addresses not accessible")
        if not self.is_available():
            return PageRecord(
                url=normalized_url,
                error="Playwright not available. Run: py -3 -m playwright install chromium",
            )

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(normalized_url, timeout=20000, wait_until="domcontentloaded")
                title = page.title()
                content = page.inner_text("body")
                browser.close()
            return PageRecord(
                url=normalized_url,
                title=title,
                content=content[:8000],
                word_count=len(content.split()),
                status_code=200,
            )
        except Exception as exc:
            return PageRecord(url=normalized_url, error=str(exc))

    def navigate_and_fill(
        self,
        url: str,
        fields: dict[str, str],
    ) -> BrowserActionResult:
        del fields
        if not self.is_available():
            return BrowserActionResult(success=False, action="fill", url=url, error="Playwright not available")
        return BrowserActionResult(
            success=False,
            action="fill",
            url=url,
            consequential=True,
            error="Form filling not yet implemented in this phase",
        )


class BrowserWorkflows:
    """
    Orchestrates browser operations.
    """

    def __init__(self, desktop: DesktopFaculty) -> None:
        self.desktop = desktop
        self.fetcher = BrowserDirectFetcher()
        self.playwright = PlaywrightBrowser()

    def read_page(self, url: str, js: bool = False) -> tuple[PageRecord, BrowserComprehension]:
        if js and self.playwright.is_available():
            record = self.playwright.fetch_js(url)
        else:
            record = self.fetcher.fetch(url)
        return record, build_browser_comprehension(record)

    def search_web(self, query: str) -> tuple[PageRecord, BrowserComprehension]:
        record = self.fetcher.search(query)
        return record, build_browser_comprehension(record, query=query, is_search=True)

    def open_in_browser(self, url: str, browser: str = "firefox") -> BrowserActionResult:
        normalized_url = str(url or "").strip()
        if not normalized_url.startswith(("http://", "https://")):
            normalized_url = "https://" + normalized_url
        if not is_safe_url(normalized_url):
            return BrowserActionResult(
                success=False,
                action="navigate",
                url=normalized_url,
                consequential=True,
                error="URL blocked: internal/local addresses not accessible",
            )
        result = self.desktop.open_app(f"{browser} {normalized_url}")
        return BrowserActionResult(
            success=result.success,
            action="navigate",
            url=normalized_url,
            output=f"Opened {normalized_url} in {browser}",
            consequential=True,
            error=result.error,
        )

    def format_page_result(self, record: PageRecord) -> str:
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
        return "\n".join(line for line in lines if line)

    def format_search_result(self, record: PageRecord, query: str) -> str:
        if not record.success:
            return f"browser > search error: {record.error}"
        return (
            f"browser > search results for: {query}\n"
            f"{record.content[:3000]}"
        )

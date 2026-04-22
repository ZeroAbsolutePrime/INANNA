from __future__ import annotations

import json
import urllib.error
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from core.browser_workflows import (
    BrowserComprehension,
    BrowserDirectFetcher,
    BrowserWorkflows,
    PageRecord,
    PlaywrightBrowser,
    clean_html_to_text,
    extract_title,
    is_safe_url,
)
from main import BROWSER_TOOL_NAMES


class BrowserWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.desktop = Mock()
        self.desktop.open_app.return_value = Mock(success=True, error=None)
        self.workflows = BrowserWorkflows(self.desktop)

    def test_browser_workflows_instantiates(self) -> None:
        self.assertIsInstance(self.workflows, BrowserWorkflows)

    def test_browser_direct_fetcher_instantiates(self) -> None:
        self.assertIsInstance(BrowserDirectFetcher(), BrowserDirectFetcher)

    def test_playwright_browser_instantiates(self) -> None:
        self.assertIsInstance(PlaywrightBrowser(), PlaywrightBrowser)

    def test_is_safe_url_allows_public_https(self) -> None:
        self.assertTrue(is_safe_url("https://example.com"))

    def test_is_safe_url_blocks_localhost(self) -> None:
        self.assertFalse(is_safe_url("http://localhost:8080"))

    def test_is_safe_url_blocks_private_lan(self) -> None:
        self.assertFalse(is_safe_url("http://192.168.1.1"))

    def test_is_safe_url_blocks_file_scheme(self) -> None:
        self.assertFalse(is_safe_url("file:///etc/passwd"))

    def test_clean_html_to_text_removes_script_and_style_tags(self) -> None:
        html = "<html><head><style>bad</style><script>bad</script></head><body><p>Hello</p></body></html>"

        text = clean_html_to_text(html)

        self.assertNotIn("bad", text)

    def test_clean_html_to_text_preserves_text_content(self) -> None:
        html = "<html><body><h1>Title</h1><p>Body copy</p></body></html>"

        text = clean_html_to_text(html)

        self.assertIn("Title", text)
        self.assertIn("Body copy", text)

    def test_extract_title_finds_title(self) -> None:
        self.assertEqual(extract_title("<title>Alpha</title>"), "Alpha")

    def test_extract_title_returns_empty_when_missing(self) -> None:
        self.assertEqual(extract_title("<html><body>no title</body></html>"), "")

    def test_page_record_defaults_are_correct(self) -> None:
        record = PageRecord()

        self.assertEqual(record.url, "")
        self.assertEqual(record.links, [])
        self.assertEqual(record.word_count, 0)

    def test_page_record_success_true_when_content_present(self) -> None:
        self.assertTrue(PageRecord(url="https://example.com", content="hello").success)

    def test_page_record_success_false_when_error_set(self) -> None:
        self.assertFalse(PageRecord(url="https://example.com", content="hello", error="boom").success)

    def test_page_record_summary_line_includes_url(self) -> None:
        record = PageRecord(url="https://example.com", title="Example", content="hello world", word_count=2)

        self.assertIn("https://example.com", record.summary_line())

    def test_fetch_urllib_handles_connection_error_gracefully(self) -> None:
        fetcher = BrowserDirectFetcher()
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            record = fetcher._fetch_urllib("https://example.com")

        self.assertFalse(record.success)
        self.assertIn("offline", record.error or "")

    def test_fetch_blocks_internal_urls(self) -> None:
        record = BrowserDirectFetcher().fetch("http://localhost:8080")

        self.assertFalse(record.success)
        self.assertIn("blocked", record.error or "")

    def test_browser_tool_names_contains_all_three_tools(self) -> None:
        self.assertEqual(BROWSER_TOOL_NAMES, {"browser_read", "browser_search", "browser_open"})

    def test_browser_read_tool_definition_requires_no_approval(self) -> None:
        tools_path = Path(__file__).resolve().parent.parent / "config" / "tools.json"
        payload = json.loads(tools_path.read_text(encoding="utf-8"))
        tool = payload["tools"]["browser_read"]

        self.assertFalse(tool["requires_approval"])
        self.assertEqual(tool["category"], "browser")

    def test_browser_open_tool_definition_requires_approval(self) -> None:
        tools_path = Path(__file__).resolve().parent.parent / "config" / "tools.json"
        payload = json.loads(tools_path.read_text(encoding="utf-8"))
        tool = payload["tools"]["browser_open"]

        self.assertTrue(tool["requires_approval"])
        self.assertEqual(tool["category"], "browser")

    def test_open_in_browser_uses_desktop_faculty(self) -> None:
        result = self.workflows.open_in_browser("example.com", browser="chrome")

        self.assertTrue(result.success)
        self.desktop.open_app.assert_called_once()

    def test_search_web_uses_fetcher(self) -> None:
        expected = PageRecord(url="search:test", title="Search", content="body", word_count=1)
        with patch.object(self.workflows.fetcher, "search", return_value=expected) as search_mock:
            result, comprehension = self.workflows.search_web("test")

        self.assertEqual(result, expected)
        self.assertIsInstance(comprehension, BrowserComprehension)
        self.assertTrue(comprehension.is_search)
        search_mock.assert_called_once_with("test")


if __name__ == "__main__":
    unittest.main()

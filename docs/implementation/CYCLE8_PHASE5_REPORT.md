# Cycle 8 Phase 8.5 Report - Browser Faculty

## Summary

Phase 8.5 adds the Browser Faculty to INANNA NYX.
The system can now:

- fetch and read public web pages directly
- search DuckDuckGo HTML results directly
- open a URL in Firefox, Chrome, or Edge through governed desktop launch

The Browser Faculty follows the same principle as the Document Faculty:
use a direct machine-readable path first, then use the visible application
path only when the user explicitly asks for it.

## Dependency and runtime result

Python install command:

```powershell
py -3 -m pip install beautifulsoup4 lxml --break-system-packages
```

Results:

- `beautifulsoup4 4.14.3` installed successfully
- `lxml 6.1.0` was already installed and available

Playwright browser runtime command:

```powershell
py -3 -m playwright install chromium
```

Result:

- Playwright Chromium installed successfully
- no fallback-only mode was required

## Fallback behavior

Even though Chromium installed cleanly, the Browser Faculty still retains
graceful fallback behavior:

- direct read/search uses `httpx` first
- if `httpx` is unavailable, stdlib `urllib` is used
- if Playwright is unavailable, JS-read requests return a clear error instead
  of hanging or crashing

## Real URL smoke check

Network was available during implementation.
The Browser Faculty smoke path was verified against a real public URL:

- target: `https://example.com`
- result: readable content and title extraction worked through the direct fetch path

This smoke check was not part of the unit test suite.
All automated tests remain offline and make no real network calls.

## Tool surface

Three tools were added:

- `browser_read`
- `browser_search`
- `browser_open`

Total registered tools after this phase: `38`

## Governance

- `browser_read`: no approval required
- `browser_search`: no approval required
- `browser_open`: approval required

Blocked by design:

- localhost URLs
- private network URLs
- `file://` URLs
- password and financial form actions

## NixOS equivalents

New dependencies map to these NixOS packages:

- `httpx` -> `python311Packages.httpx`
- `beautifulsoup4` -> `python311Packages.beautifulsoup4`
- `lxml` -> `python311Packages.lxml`
- `playwright` -> `python311Packages.playwright`

See `docs/nixos_browser_faculty.md` for the NixOS deployment note.

## Verification

Verification for this phase includes:

- focused browser workflow tests
- updated operator registry tests
- updated identity tests
- updated help and command tests
- full tracked unittest discovery run

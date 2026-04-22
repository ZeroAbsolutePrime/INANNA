# NixOS Browser Faculty Dependencies

Cycle 8 Phase 8.5 adds the Browser Faculty to INANNA NYX.
It uses a two-level model:

- Level 1: direct HTTP fetch and HTML parsing
- Level 2: headless Chromium through Playwright for JS-heavy pages

## Python dependencies

The following Python libraries are used by the Browser Faculty:

- `httpx`
- `beautifulsoup4`
- `lxml`
- `playwright`

Installed during this phase:

- `beautifulsoup4 4.14.3`
- `lxml 6.1.0` was already present
- Playwright Chromium install succeeded via:

```powershell
py -3 -m playwright install chromium
```

## NixOS equivalents

- `python311Packages.httpx`
- `python311Packages.beautifulsoup4`
- `python311Packages.lxml`
- `python311Packages.playwright`

Browser packages:

- `programs.firefox.enable = true`
- or `pkgs.google-chrome` / `pkgs.chromium` when a visible browser is desired

## Playwright on NixOS

Playwright on NixOS often needs explicit browser-runtime handling because
the browser binaries are not always resolved like they are on Windows.

Recommended options:

- use `python311Packages.playwright`
- install `chromium` or `google-chrome`
- set browser executable paths explicitly when needed

Typical environment variables:

- `PLAYWRIGHT_BROWSERS_PATH`
- `CHROME_BIN`
- `CHROMIUM_BIN`

## How the Browser Faculty works without a visible browser

Level 1 never opens Firefox or Chromium. It fetches a URL directly with
`httpx`, parses the returned HTML, strips non-readable elements, and
returns structured text for CROWN.

This means Browser Faculty reading works:

- headlessly
- without a GUI session
- without a visible browser window
- with lower latency than desktop automation

## Level 1 vs Level 2 on NixOS

Level 1:

- best for public pages and static content
- does not require a browser process
- is the default path

Level 2:

- used for JS-rendered pages
- depends on Playwright plus a Chromium runtime
- still headless by default

Visible browser control remains a separate path through the Desktop Faculty.

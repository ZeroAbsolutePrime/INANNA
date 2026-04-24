# CURRENT PHASE: Cycle 8 - Phase 8.7 - NixOS Backend
**Status: ACTIVE**
**Authorized by: INANNA NAMMU (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-22**
**Cycle: 8 - The Desktop Bridge**
**Replaces: Cycle 8 Phase 8.6 - Calendar Faculty (COMPLETE)**

---

## MANDATORY READING — in this exact order

1. docs/platform_architecture.md   ← ESSENTIAL for this phase
2. docs/cycle8_master_plan.md
3. docs/implementation/CURRENT_PHASE.md (this file)
4. CODEX_DOCTRINE.md
5. ABSOLUTE_PROTOCOL.md

---

## Current System State (discovered before writing this phase)

LinuxAtspiBackend: FULLY IMPLEMENTED in core/desktop_faculty.py
  - open_app()    via xdg-open / subprocess
  - read_window() via pyatspi.Registry.getDesktop()
  - click()       via pyatspi queryAction().doAction()
  - type_text()   via xdotool / ydotool fallback
  - screenshot()  via scrot / gnome-screenshot fallback
  All 5 operations complete. No stub — real code.

NixOS directory: nixos/
  configuration.nix  (1462 bytes — current, missing Cycle 8 deps)
  inanna-nyx.service (460 bytes)
  install.sh         (989 bytes)
  README.md          (1203 bytes)

Current NixOS config gaps (configuration.nix was written in Cycle 7):
  MISSING: at-spi2-core, pyatspi
  MISSING: thunderbird (email), signal-desktop
  MISSING: libreoffice, firefox (document + browser)
  MISSING: python libs: python-docx, pymupdf, openpyxl, odfpy
  MISSING: python libs: icalendar, caldav, httpx, beautifulsoup4
  MISSING: python libs: playwright (browser automation)
  MISSING: xdotool, ydotool, scrot (desktop automation tools)
  MISSING: INANNA_SERVER_URL env var (client → server connection)
  MISSING: Network security hardening

Tools registered: 41 across 11 categories
Tests passing: 591
Phase: Cycle 8 - Phase 8.6 - Calendar Faculty

---

## What This Phase Is

Phase 8.7 brings the NixOS configuration to feature parity
with everything built in Cycles 7 and 8.

This phase has TWO parts:

### Part A — NixOS Client Configuration

Update nixos/configuration.nix to include ALL dependencies
for the NixOS client laptop (INANNA NAMMU's machine when she moves
from Windows to NixOS).

This is the machine that:
  - Connects to the DGX Spark server (browser → :8080/:8081)
  - Runs the Desktop Faculty (AT-SPI2 accessibility)
  - Has local apps INANNA can reach: Thunderbird, Signal,
    LibreOffice, Firefox

The config must be complete, bootable, and correct.

### Part B — NixOS Server Configuration

Update nixos/configuration.nix (or create a separate
nixos/server.nix) for the DGX Spark server deployment.

This is the machine that:
  - Runs INANNA NYX Core (HTTP :8080, WebSocket :8081)
  - Loads the LLM models (CROWN, NAMMU, SENTINEL, ANALYST)
  - Serves multiple clients

---

## What You Are Building

### Task 1 — nixos/client.nix (NEW — NixOS client config)

Create: nixos/client.nix

This is the complete NixOS configuration for INANNA NAMMU's client
laptop. It replaces configuration.nix for client machines.

The file must include:

```nix
{ config, pkgs, lib, ... }:

{
  # ── SYSTEM ────────────────────────────────────────────────────
  system.stateVersion = "25.11";
  networking.hostName = "inanna-client";
  time.timeZone = "Europe/Madrid";   # ZAERA's timezone

  # ── BOOT ──────────────────────────────────────────────────────
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # ── USER ──────────────────────────────────────────────────────
  users.users.inanna_nammu = {
    isNormalUser = true;
    description = "INANNA NAMMU - Guardian";
    extraGroups = [ "networkmanager" "wheel" "audio" "video" "input" ];
    home = "/home/inanna_nammu";
    shell = pkgs.bash;
  };

  # ── DESKTOP (Wayland + GNOME) ─────────────────────────────────
  services.xserver.enable = true;
  services.xserver.displayManager.gdm.enable = true;
  services.xserver.desktopManager.gnome.enable = true;
  services.xserver.displayManager.gdm.wayland = true;

  # ── AT-SPI2 — Desktop Faculty requirement ─────────────────────
  # Enables INANNA's LinuxAtspiBackend to read application windows
  # via the accessibility tree. Required for all Desktop Faculty ops.
  services.gnome.at-spi2-core.enable = true;

  # ── SYSTEM PACKAGES ───────────────────────────────────────────
  environment.systemPackages = with pkgs; [
    # Core system tools
    git curl wget

    # Python runtime
    python311
    python311Packages.pip

    # ── INANNA client Python dependencies ────────────────────────
    # WebSocket + HTTP
    python311Packages.websockets
    python311Packages.aiohttp
    python311Packages.httpx

    # Email Faculty (Thunderbird MBOX reader)
    # (mailbox module is stdlib — no extra package)

    # Document Faculty
    python311Packages.python-docx
    python311Packages.pymupdf          # PDF reading
    python311Packages.openpyxl         # XLSX reading
    # odfpy: may need overlay if not in nixpkgs
    # python311Packages.odfpy

    # Browser Faculty
    python311Packages.beautifulsoup4
    python311Packages.lxml

    # Calendar Faculty
    python311Packages.icalendar
    # python311Packages.caldav          # optional

    # ── AT-SPI2 Python bindings ───────────────────────────────────
    at-spi2-core                        # system library
    python311Packages.pyatspi           # Python bindings for AT-SPI2

    # ── Desktop interaction tools (LinuxAtspiBackend) ─────────────
    xdotool        # X11 input simulation (fallback for type_text)
    ydotool        # Wayland input simulation (primary for type_text)
    wl-clipboard   # Wayland clipboard (wl-copy / wl-paste)
    scrot          # X11 screenshot (fallback)
    # gnome-screenshot is part of gnome desktop

    # ── Applications accessible to INANNA Desktop Faculty ─────────
    thunderbird    # Email + Calendar (Lightning built-in)
    signal-desktop # Secure messaging
    libreoffice    # Document suite (Writer, Calc, Impress)
    firefox        # Browser

    # ── Utilities ─────────────────────────────────────────────────
    ripgrep
    tree
    htop
  ];

  # ── ENVIRONMENT VARIABLES ─────────────────────────────────────
  # Configure INANNA client to connect to the DGX server
  # Update INANNA_SERVER_URL when DGX IP is known
  environment.sessionVariables = {
    INANNA_SERVER_URL = "http://192.168.1.100:8080";   # DGX IP
    INANNA_WS_URL     = "ws://192.168.1.100:8081";     # DGX WS
    # Override locally for development:
    # INANNA_SERVER_URL = "http://localhost:8080";
  };

  # ── ACCESSIBILITY ──────────────────────────────────────────────
  # Required for pyatspi to work with Wayland apps
  environment.variables = {
    AT_SPI_BUS_ADDRESS = "unix:path=/run/user/1000/at-spi/bus";
  };

  # ── FIREWALL ──────────────────────────────────────────────────
  networking.firewall.enable = true;
  networking.firewall.allowedTCPPorts = [];  # client: no inbound ports
  networking.networkmanager.enable = true;
}
```

### Task 2 — nixos/server.nix (NEW — NixOS server config)

Create: nixos/server.nix

Complete NixOS configuration for the DGX Spark server.

The file must include:

```nix
{ config, pkgs, lib, ... }:

{
  # ── SYSTEM ────────────────────────────────────────────────────
  system.stateVersion = "25.11";
  networking.hostName = "inanna-server";
  time.timeZone = "Europe/Madrid";

  # ── BOOT ──────────────────────────────────────────────────────
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # ── USER ──────────────────────────────────────────────────────
  users.users.inanna = {
    isNormalUser = true;
    description = "INANNA NYX Service User";
    home = "/home/inanna";
    shell = pkgs.bash;
  };

  # ── HEADLESS (no desktop on server) ───────────────────────────
  # Server runs headless — no display manager needed
  # Models run via LM Studio or ollama
  services.xserver.enable = false;

  # ── SYSTEM PACKAGES ───────────────────────────────────────────
  environment.systemPackages = with pkgs; [
    # Core
    git curl wget htop tmux

    # Python runtime
    python311
    python311Packages.pip

    # INANNA NYX Python dependencies (server-side)
    python311Packages.websockets
    python311Packages.aiohttp
    python311Packages.httpx
    python311Packages.python-docx
    python311Packages.pymupdf
    python311Packages.openpyxl
    python311Packages.beautifulsoup4
    python311Packages.lxml
    python311Packages.icalendar
    python311Packages.cryptography      # auth / PBKDF2

    # LLM serving (choose one)
    # ollama               # alternative to LM Studio
  ];

  # ── INANNA NYX SYSTEMD SERVICE ────────────────────────────────
  systemd.services.inanna-nyx = {
    description = "INANNA NYX - Sovereign Intelligence Platform";
    after = [ "network.target" ];
    wantedBy = [ "multi-user.target" ];

    serviceConfig = {
      User = "inanna";
      WorkingDirectory = "/home/inanna/INANNA/inanna";
      ExecStart = "${pkgs.python311}/bin/python3 ui_main.py";
      Restart = "always";
      RestartSec = "5s";

      # Resource limits
      MemoryMax = "8G";          # OS memory (models use GPU RAM)
      CPUQuota  = "400%";        # 4 cores max for Python process

      # Logging
      StandardOutput = "journal";
      StandardError  = "journal";
    };

    environment = {
      # Model: update when DGX is provisioned with actual model
      INANNA_MODEL_URL  = "http://localhost:1234/v1";
      INANNA_MODEL_NAME = "qwen2.5-72b-instruct";   # DGX Spark model

      # Realm
      INANNA_REALM      = "default";

      # Security
      INANNA_SECRET_KEY = "";   # Set via secrets management
    };
  };

  # ── FIREWALL ──────────────────────────────────────────────────
  networking.firewall.enable = true;
  # Open INANNA ports (restrict to LAN in production)
  networking.firewall.allowedTCPPorts = [
    8080   # INANNA HTTP
    8081   # INANNA WebSocket
    1234   # LM Studio / model server
  ];
  networking.networkmanager.enable = true;

  # ── SSH (server management) ───────────────────────────────────
  services.openssh = {
    enable = true;
    settings.PasswordAuthentication = false;  # keys only
    settings.PermitRootLogin = "no";
  };
}
```

### Task 3 — nixos/configuration.nix (UPDATE)

Update the existing nixos/configuration.nix to reflect the
two-machine architecture. Add a comment block at the top:

```nix
# INANNA NYX - NixOS Configuration
# ─────────────────────────────────
# This file: legacy single-machine config (Cycle 7)
# Updated:   Cycle 8 Phase 8.7
#
# For new deployments, use:
#   nixos/client.nix  — INANNA NAMMU's laptop (NixOS client)
#   nixos/server.nix  — DGX Spark (INANNA NYX server)
#
# This file is kept for single-machine testing (server + client
# on the same machine, e.g. during development).
```

Also add all missing Cycle 8 packages to this file:
  at-spi2-core, python311Packages.pyatspi
  thunderbird, signal-desktop, libreoffice, firefox
  xdotool, ydotool, wl-clipboard, scrot
  python311Packages.python-docx, python311Packages.pymupdf
  python311Packages.openpyxl
  python311Packages.beautifulsoup4, python311Packages.lxml
  python311Packages.icalendar, python311Packages.httpx

### Task 4 — nixos/README.md (UPDATE)

Update nixos/README.md to document the two-machine architecture
and explain when to use client.nix vs server.nix vs
configuration.nix. Include:
  - Prerequisites (NixOS 25.11+)
  - client.nix: for INANNA NAMMU's laptop
  - server.nix: for DGX Spark
  - configuration.nix: single-machine development
  - How to apply: nixos-rebuild switch --flake .
  - How to update DGX IP in client.nix
  - AT-SPI2 verification command:
      python3 -c "import pyatspi; print('AT-SPI2 OK')"

### Task 5 — core/desktop_faculty.py (ENHANCE LinuxAtspiBackend)

The LinuxAtspiBackend is complete but needs two improvements:

**Improvement 1: Wayland detection**
Add a helper that detects X11 vs Wayland and selects
the correct input tool automatically:

```python
def _detect_display_server(self) -> str:
    """Detect X11 or Wayland. Returns 'wayland' or 'x11'."""
    wayland_display = os.environ.get('WAYLAND_DISPLAY', '')
    xdg_session = os.environ.get('XDG_SESSION_TYPE', '').lower()
    if wayland_display or xdg_session == 'wayland':
        return 'wayland'
    return 'x11'
```

Use this in type_text() to prefer ydotool on Wayland
and xdotool on X11, rather than always trying xdotool first.

**Improvement 2: app name normalization for Linux**
Add a Linux app name map equivalent to the Windows one:
```python
LINUX_APP_NAME_MAP = {
    'thunderbird': 'thunderbird',
    'firefox': 'firefox',
    'signal': 'signal-desktop',
    'libreoffice': 'libreoffice',
    'writer': 'libreoffice --writer',
    'calc': 'libreoffice --calc',
    'impress': 'libreoffice --impress',
    'terminal': 'gnome-terminal',
    'files': 'nautilus',
}
```

### Task 6 — identity.py

CURRENT_PHASE = "Cycle 8 - Phase 8.7 - NixOS Backend"

### Task 7 — Tests (all offline — no actual NixOS needed)

Create inanna/tests/test_nixos_backend.py (20 tests):

  - LinuxAtspiBackend instantiates
  - LinuxAtspiBackend.name == "linux-atspi2"
  - LinuxAtspiBackend.open_app returns DesktopResult on missing binary
    (mock subprocess.Popen to raise FileNotFoundError)
  - LinuxAtspiBackend.type_text returns DesktopResult on missing xdotool
    (mock subprocess.run to raise FileNotFoundError)
  - LinuxAtspiBackend.screenshot returns DesktopResult on missing scrot
    (mock subprocess.run to raise FileNotFoundError)
  - LinuxAtspiBackend.read_window returns error when pyatspi missing
    (mock import to raise ImportError)
  - LinuxAtspiBackend.click returns error when pyatspi missing
    (mock import to raise ImportError)
  - LinuxAtspiBackend._detect_display_server returns 'wayland'
    when WAYLAND_DISPLAY is set (monkeypatch os.environ)
  - LinuxAtspiBackend._detect_display_server returns 'x11'
    when WAYLAND_DISPLAY not set
  - LINUX_APP_NAME_MAP contains 'thunderbird'
  - LINUX_APP_NAME_MAP contains 'firefox'
  - LINUX_APP_NAME_MAP maps 'signal' to 'signal-desktop'
  - DesktopFaculty selects LinuxAtspiBackend on Linux
    (mock sys.platform to 'linux')
  - DesktopFaculty selects WindowsMCPBackend on Windows
    (mock sys.platform to 'win32')
  - DesktopFaculty selects FallbackBackend on unknown platform
    (mock sys.platform to 'unknown')
  - nixos/client.nix exists and contains 'at-spi2-core'
  - nixos/client.nix contains 'pyatspi'
  - nixos/client.nix contains 'thunderbird'
  - nixos/server.nix exists and contains 'inanna-nyx'
  - nixos/README.md contains 'client.nix'

Update test_identity.py: CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/core/desktop_faculty.py         <- MODIFY: Wayland detection,
                                           LINUX_APP_NAME_MAP
inanna/identity.py                     <- MODIFY: CURRENT_PHASE
inanna/tests/test_nixos_backend.py     <- NEW
inanna/tests/test_identity.py          <- MODIFY
nixos/client.nix                       <- NEW (mandatory)
nixos/server.nix                       <- NEW (mandatory)
nixos/configuration.nix                <- MODIFY: add comment + packages
nixos/README.md                        <- MODIFY: two-machine architecture

---

## What You Are NOT Building

- No actual NixOS flake.nix (future)
- No secrets management (future)
- No network discovery between client and server (future)
- No changes to Python tool code (faculties are complete)
- No new Python tools registered
- No changes to server.py, main.py, or tools.json
- Do NOT attempt to import pyatspi in tests without mocking

---

## Important: Platform Detection in DesktopFaculty

The DesktopFaculty already selects the backend based on platform.
Verify (do NOT change) that selection logic works correctly:
  - sys.platform == 'win32'  → WindowsMCPBackend
  - sys.platform == 'linux'  → LinuxAtspiBackend
  - otherwise                → FallbackBackend

If the selection logic uses a different pattern, document it
accurately in the test — do not change the logic to match
the test. The test must match the actual code.

---

## Definition of Done

- [ ] nixos/client.nix created with all Cycle 8 dependencies
- [ ] nixos/server.nix created with systemd service + DGX config
- [ ] nixos/configuration.nix updated with comment + missing packages
- [ ] nixos/README.md updated with two-machine architecture
- [ ] LinuxAtspiBackend has _detect_display_server()
- [ ] LINUX_APP_NAME_MAP defined
- [ ] CURRENT_PHASE = "Cycle 8 - Phase 8.7 - NixOS Backend"
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle8-phase7-complete

---

## Handoff

Commit: cycle8-phase7-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE8_PHASE7_REPORT.md

The report MUST include:
  - Confirmation of client.nix and server.nix created
  - AT-SPI2 package names used (may differ across nixpkgs versions)
  - Wayland vs X11 detection approach
  - Platform selection logic confirmed correct
  - Note on pyatspi nixpkgs availability

Stop. Do not begin Phase 8.8 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: INANNA NAMMU*
*Date: 2026-04-22*
*The NixOS configuration is the DNA of the platform.*
*Every package declared is a capability confirmed.*
*client.nix: the hands*
*server.nix: the brain*
*When they connect, INANNA lives.*
*This phase writes the blueprint*
*for the day the DGX arrives.*

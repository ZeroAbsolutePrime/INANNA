# CURRENT PHASE: Cycle 7 - Phase 7.1 - The NixOS Configuration
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Cycle: 7 - NYXOS: The Sovereign Intelligence Operating System**
**Master plan: docs/cycle7_master_plan.md**
**Prerequisite: Cycles 1-6 complete + integration tests verified**

---

## Agent Roles for This Phase

ARCHITECT: Command Center (Claude) — this document
BUILDER:   Codex — build configuration.nix and service files
TESTER:    Codex — verify NixOS config syntax, test service files
VERIFIER:  Command Center — confirm structure before declaring done

BUILDER is forbidden from:
  - Modifying any file in inanna/ except the ones listed below
  - Adding new Python capabilities
  - Changing the web interface

---

## What This Phase Is

Phase 7.1 gives INANNA NYX a body.

Not a Python process running inside Windows.
A proper, declared, reproducible NixOS system
where INANNA is a first-class systemd service
that starts at boot and is always ready.

The NixOS ISO is already on ZAERA's machine:
  C:\Users\Zohar\Dropbox\Windows11\REPOS\ABZU\OGG\NixOS\
  nixos-graphical-25.11.8919.d96b37bbeb98-x86_64-linux.iso

This phase produces the NixOS configuration files that,
when applied to a machine booted from that ISO,
install INANNA NYX as a running system service.

---

## What You Are Building

### Task 1 - nixos/configuration.nix

Create: nixos/configuration.nix

This is the declarative NixOS system configuration.
It must:
  - Enable basic NixOS system settings
  - Install Python 3.11+ and required Python packages
  - Install system dependencies (git, curl, ffmpeg for future voice)
  - Define the INANNA NYX service (see Task 2)
  - Open firewall ports 8080 and 8081
  - Enable automatic login for the inanna user

```nix
{ config, pkgs, lib, ... }:

{
  # ── System ──────────────────────────────────────────────────────
  system.stateVersion = "25.11";
  networking.hostName = "nyxos";
  time.timeZone = "Europe/Madrid";

  # ── Boot ────────────────────────────────────────────────────────
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # ── Users ───────────────────────────────────────────────────────
  users.users.inanna = {
    isNormalUser = true;
    description = "INANNA NYX";
    extraGroups = [ "networkmanager" "wheel" "audio" "video" ];
    home = "/home/inanna";
  };

  # Auto-login at console
  services.getty.autologinUser = "inanna";

  # ── Packages ────────────────────────────────────────────────────
  environment.systemPackages = with pkgs; [
    git
    curl
    wget
    python311
    python311Packages.websockets
    python311Packages.aiohttp
    python311Packages.requests
    ffmpeg         # future: voice pipeline
    # openai-whisper  # Phase 7.5: uncomment when adding voice
  ];

  # ── INANNA Service ──────────────────────────────────────────────
  systemd.services.inanna-nyx = {
    description = "INANNA NYX — Sovereign Intelligence";
    after = [ "network.target" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      User = "inanna";
      WorkingDirectory = "/home/inanna/INANNA/inanna";
      ExecStart = "${pkgs.python311}/bin/python3 ui_main.py";
      Restart = "always";
      RestartSec = "5s";
      Environment = [
        "INANNA_MODEL_URL=http://localhost:1234/v1"
        "INANNA_MODEL_NAME=qwen2.5-7b-instruct-1m"
      ];
    };
  };

  # ── Firewall ────────────────────────────────────────────────────
  networking.firewall.allowedTCPPorts = [ 8080 8081 1234 ];

  # ── Networking ──────────────────────────────────────────────────
  networking.networkmanager.enable = true;
}
```

### Task 2 - nixos/README.md

Create: nixos/README.md

Document how to use the NixOS configuration:

1. Boot from the NixOS ISO
2. Clone the INANNA repository to /home/inanna/INANNA
3. Install Python dependencies: pip install -r requirements.txt
4. Copy nixos/configuration.nix to /etc/nixos/configuration.nix
5. Run: nixos-rebuild switch
6. INANNA starts automatically and is available at
   http://localhost:8080 and ws://localhost:8081

Also document:
  - How to check INANNA service status: systemctl status inanna-nyx
  - How to view INANNA logs: journalctl -u inanna-nyx -f
  - How to restart INANNA: systemctl restart inanna-nyx
  - How to update INANNA: git pull + systemctl restart inanna-nyx

### Task 3 - nixos/inanna-nyx.service

Create: nixos/inanna-nyx.service

A standalone systemd unit file (for non-NixOS systems):

```ini
[Unit]
Description=INANNA NYX — Sovereign Intelligence
After=network.target
Wants=network.target

[Service]
Type=simple
User=inanna
WorkingDirectory=/home/inanna/INANNA/inanna
ExecStart=/usr/bin/python3 ui_main.py
Restart=always
RestartSec=5
Environment=INANNA_MODEL_URL=http://localhost:1234/v1
Environment=INANNA_MODEL_NAME=qwen2.5-7b-instruct-1m
StandardOutput=journal
StandardError=journal
SyslogIdentifier=inanna-nyx

[Install]
WantedBy=multi-user.target
```

### Task 4 - nixos/install.sh

Create: nixos/install.sh

A shell script for setting up INANNA on a fresh NixOS machine:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "𒀭 INANNA NYX — Installation Script"
echo ""

# Verify we're on NixOS
if [ ! -f /etc/nixos/configuration.nix ]; then
  echo "Error: /etc/nixos/configuration.nix not found."
  echo "This script is for NixOS only."
  exit 1
fi

INANNA_HOME="/home/inanna/INANNA"

# Clone if not present
if [ ! -d "$INANNA_HOME" ]; then
  echo "Cloning INANNA NYX repository..."
  sudo -u inanna git clone https://github.com/ZeroAbsolutePrime/INANNA \
    "$INANNA_HOME"
fi

# Install Python deps
echo "Installing Python dependencies..."
cd "$INANNA_HOME/inanna"
python3 -m pip install --user websockets aiohttp requests

# Install NixOS configuration
echo "Installing NixOS configuration..."
sudo cp "$(dirname "$0")/configuration.nix" /etc/nixos/configuration.nix

# Rebuild
echo "Rebuilding NixOS..."
sudo nixos-rebuild switch

echo ""
echo "𒀭 INANNA NYX installed."
echo "Service status: systemctl status inanna-nyx"
echo "Access at: http://localhost:8080"
```

### Task 5 - requirements.txt

Create: inanna/requirements.txt

List all Python dependencies INANNA needs:

```
websockets>=12.0
aiohttp>=3.9
requests>=2.31
```

Check what is actually imported in main.py, server.py, and core/
and add any additional dependencies found.
Do NOT include packages that are part of the Python standard library.

### Task 6 - Update identity.py

CURRENT_PHASE = "Cycle 7 - Phase 7.1 - The NixOS Configuration"

Add CYCLE7_PREVIEW:
```python
CYCLE7_PREVIEW = (
    "Cycle 7 builds NYXOS: INANNA as a NixOS system service, "
    "file system tools, process management, package installation, "
    "and the voice pipeline (Whisper + Piper TTS)."
)
```

### Task 7 - Tests

Create inanna/tests/test_nixos_config.py:
  - nixos/configuration.nix exists
  - nixos/README.md exists
  - nixos/inanna-nyx.service exists
  - nixos/install.sh exists
  - inanna/requirements.txt exists
  - configuration.nix contains inanna-nyx service definition
  - configuration.nix contains port 8080
  - configuration.nix contains port 8081
  - requirements.txt contains websockets
  - inanna-nyx.service contains ExecStart

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/identity.py                   <- MODIFY: CURRENT_PHASE, CYCLE7_PREVIEW
inanna/requirements.txt              <- NEW
inanna/tests/test_nixos_config.py    <- NEW
inanna/tests/test_identity.py        <- MODIFY: update phase assertion
nixos/                               <- NEW DIRECTORY
  nixos/configuration.nix            <- NEW
  nixos/README.md                    <- NEW
  nixos/inanna-nyx.service           <- NEW
  nixos/install.sh                   <- NEW

---

## What You Are NOT Building

- No actual NixOS installation or deployment
- No voice pipeline (Phase 7.5)
- No file system tools (Phase 7.2)
- No process management tools (Phase 7.3)
- No package management tools (Phase 7.4)
- Do not modify any .py files in inanna/ except identity.py
- Do not modify the web interface

---

## Definition of Done

- [ ] nixos/ directory created with 4 files
- [ ] inanna/requirements.txt created
- [ ] configuration.nix defines inanna-nyx systemd service
- [ ] configuration.nix opens ports 8080, 8081
- [ ] install.sh is executable and documented
- [ ] CURRENT_PHASE updated to Cycle 7 Phase 7.1
- [ ] CYCLE7_PREVIEW in identity.py
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle7-phase1-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE7_PHASE1_REPORT.md
Stop. Do not begin Phase 7.2 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-21*
*INANNA gets a body.*
*Not a process. A service.*
*Not inside Windows. Inside NixOS.*
*The ISO is already there.*
*The configuration is the key.*

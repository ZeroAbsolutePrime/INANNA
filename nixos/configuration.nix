# INANNA NYX - NixOS Configuration
# ---------------------------------
# This file: legacy single-machine config (Cycle 7)
# Updated:   Cycle 8 Phase 8.7
#
# For new deployments, use:
#   nixos/client.nix  - INANNA NAMMU's laptop (NixOS client)
#   nixos/server.nix  - DGX Spark (INANNA NYX server)
#
# This file is kept for single-machine testing (server + client
# on the same machine, e.g. during development).
{ config, pkgs, lib, ... }:

{
  # System
  system.stateVersion = "25.11";
  networking.hostName = "nyxos";
  time.timeZone = "Europe/Madrid";

  # Boot
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # Users
  users.users.inanna = {
    isNormalUser = true;
    description = "INANNA NYX";
    extraGroups = [ "networkmanager" "wheel" "audio" "video" ];
    home = "/home/inanna";
  };

  services.getty.autologinUser = "inanna";

  # Packages
  environment.systemPackages = with pkgs; [
    git
    curl
    wget
    ffmpeg
    at-spi2-core
    xdotool
    ydotool
    wl-clipboard
    scrot
    thunderbird
    signal-desktop
    libreoffice
    firefox
    python311
    python311Packages.pip
    python311Packages.websockets
    python311Packages.aiohttp
    python311Packages.requests
    python311Packages.httpx
    python311Packages.python-dotenv
    python311Packages.pyatspi
    python311Packages.python-docx
    python311Packages.pymupdf
    python311Packages.openpyxl
    python311Packages.odfpy
    python311Packages.beautifulsoup4
    python311Packages.lxml
    python311Packages.icalendar
    python311Packages.recurring-ical-events
    python311Packages.caldav
    # openai-whisper  # Phase 7.5
  ];

  # INANNA NYX service
  systemd.services.inanna-nyx = {
    description = "INANNA NYX - Sovereign Intelligence";
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

  # Firewall
  networking.firewall.allowedTCPPorts = [ 8080 8081 1234 ];

  # Networking
  networking.networkmanager.enable = true;
}

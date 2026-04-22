{ config, pkgs, lib, ... }:

{
  system.stateVersion = "25.11";
  networking.hostName = "inanna-server";
  time.timeZone = "Europe/Madrid";

  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  users.users.inanna = {
    isNormalUser = true;
    description = "INANNA NYX Service User";
    home = "/home/inanna";
    shell = pkgs.bash;
  };

  services.xserver.enable = false;

  environment.systemPackages = with pkgs; [
    git
    curl
    wget
    htop
    tmux

    python311
    python311Packages.pip
    python311Packages.websockets
    python311Packages.aiohttp
    python311Packages.httpx
    python311Packages.python-docx
    python311Packages.pymupdf
    python311Packages.openpyxl
    python311Packages.odfpy
    python311Packages.beautifulsoup4
    python311Packages.lxml
    python311Packages.icalendar
    python311Packages.recurring-ical-events
    python311Packages.cryptography
  ];

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
      MemoryMax = "8G";
      CPUQuota = "400%";
      StandardOutput = "journal";
      StandardError = "journal";
    };

    environment = {
      INANNA_MODEL_URL = "http://localhost:1234/v1";
      INANNA_MODEL_NAME = "qwen2.5-72b-instruct";
      INANNA_REALM = "default";
      INANNA_SECRET_KEY = "";
    };
  };

  networking.firewall.enable = true;
  networking.firewall.allowedTCPPorts = [ 8080 8081 1234 ];
  networking.networkmanager.enable = true;

  services.openssh = {
    enable = true;
    settings.PasswordAuthentication = false;
    settings.PermitRootLogin = "no";
  };
}

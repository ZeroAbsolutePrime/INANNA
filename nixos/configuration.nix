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
    python311
    python311Packages.pip
    python311Packages.websockets
    python311Packages.aiohttp
    python311Packages.requests
    python311Packages.python-dotenv
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

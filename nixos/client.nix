{ config, pkgs, lib, ... }:

{
  system.stateVersion = "25.11";
  networking.hostName = "inanna-client";
  time.timeZone = "Europe/Madrid";

  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  users.users.zaera = {
    isNormalUser = true;
    description = "ZAERA - Guardian";
    extraGroups = [ "networkmanager" "wheel" "audio" "video" "input" ];
    home = "/home/zaera";
    shell = pkgs.bash;
  };

  services.xserver.enable = true;
  services.xserver.displayManager.gdm.enable = true;
  services.xserver.desktopManager.gnome.enable = true;
  services.xserver.displayManager.gdm.wayland = true;

  # Required for INANNA's LinuxAtspiBackend and accessibility-tree reads.
  services.gnome.at-spi2-core.enable = true;

  environment.systemPackages = with pkgs; [
    git
    curl
    wget

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
    python311Packages.caldav
    python311Packages.pyatspi

    at-spi2-core
    xdotool
    ydotool
    wl-clipboard
    scrot

    thunderbird
    signal-desktop
    libreoffice
    firefox

    ripgrep
    tree
    htop
  ];

  environment.sessionVariables = {
    INANNA_SERVER_URL = "http://192.168.1.100:8080";
    INANNA_WS_URL = "ws://192.168.1.100:8081";
  };

  environment.variables = {
    AT_SPI_BUS_ADDRESS = "unix:path=/run/user/1000/at-spi/bus";
  };

  networking.firewall.enable = true;
  networking.firewall.allowedTCPPorts = [ ];
  networking.networkmanager.enable = true;
}

# NYXOS Configuration

This directory now documents the Cycle 8 two-machine architecture for INANNA NYX.

## Prerequisites

- NixOS 25.11 or newer
- This repository cloned onto the target machine
- `nixos-rebuild` available

## Which File To Use

- `client.nix`
  Use for INANNA NAMMU's laptop or workstation. This machine runs the browser session and Desktop Faculty apps such as Thunderbird, Signal Desktop, LibreOffice, and Firefox.

- `server.nix`
  Use for the DGX Spark or any dedicated INANNA NYX server. This machine runs the Python service, model endpoint connection, and systemd service.

- `configuration.nix`
  Keep this for single-machine development where server and client live on the same NixOS box.

## Two-Machine Architecture

- Client machine: browser UI + Desktop Faculty hands
- Server machine: INANNA NYX core + models + HTTP/WebSocket service

When deploying the real split architecture:

1. Apply `server.nix` on the DGX Spark.
2. Update the DGX IP in `client.nix`.
3. Apply `client.nix` on INANNA NAMMU's laptop.

## Applying Configuration

If you are using a flake-based setup, apply with:

```bash
sudo nixos-rebuild switch --flake .
```

If you are copying one of these files into `/etc/nixos/configuration.nix`, then run:

```bash
sudo nixos-rebuild switch
```

## Updating DGX IP In client.nix

Edit these values in `client.nix`:

```nix
INANNA_SERVER_URL = "http://192.168.1.100:8080";
INANNA_WS_URL = "ws://192.168.1.100:8081";
```

Replace `192.168.1.100` with the actual DGX Spark LAN or VPN address.

## AT-SPI2 Verification

After applying the client config, verify accessibility bindings with:

```bash
python3 -c "import pyatspi; print('AT-SPI2 OK')"
```

## Service Operations

Check service status:

```bash
systemctl status inanna-nyx
```

View service logs:

```bash
journalctl -u inanna-nyx -f
```

Restart INANNA:

```bash
systemctl restart inanna-nyx
```

## Files

- `client.nix` declares the NixOS client laptop configuration.
- `server.nix` declares the DGX Spark server configuration.
- `configuration.nix` preserves the single-machine development profile.
- `inanna-nyx.service` provides a standalone systemd unit for non-NixOS use.
- `install.sh` automates the basic NixOS setup flow.

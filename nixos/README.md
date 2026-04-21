# NYXOS Configuration

This directory contains the Phase 7.1 NixOS scaffold for running
INANNA NYX as a system service.

## Install Flow

1. Boot from the NixOS ISO.
2. Clone the INANNA repository to `/home/inanna/INANNA`.
3. Install Python dependencies:

   ```bash
   cd /home/inanna/INANNA/inanna
   python3 -m pip install --user -r requirements.txt
   ```

4. Copy `nixos/configuration.nix` to `/etc/nixos/configuration.nix`.
5. Run:

   ```bash
   sudo nixos-rebuild switch
   ```

6. INANNA starts automatically and is available at:
   - `http://localhost:8080`
   - `ws://localhost:8081`

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

Update INANNA after pulling new code:

```bash
cd /home/inanna/INANNA
git pull
cd /home/inanna/INANNA/inanna
python3 -m pip install --user -r requirements.txt
systemctl restart inanna-nyx
```

## Files

- `configuration.nix` declares the NixOS system service and ports.
- `inanna-nyx.service` provides a standalone systemd unit for non-NixOS use.
- `install.sh` automates the basic NixOS setup flow.

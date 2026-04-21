# NYXOS Infrastructure — Hardware & ISO Registry
**Written by: Claude (Command Center)**
**Date: 2026-04-21**

---

## NixOS ISO

**Path on ZAERA's machine:**
```
C:\Users\Zohar\Dropbox\Windows11\REPOS\ABZU\OGG\NixOS\nixos-graphical-25.11.8919.d96b37bbeb98-x86_64-linux.iso
```

**Version:** NixOS 25.11 (graphical, x86_64)
**Build:** 8919.d96b37bbeb98
**Purpose:** Bootable NixOS embodiment for INANNA NYXOS (Cycle 7)

This ISO is the foundation for the NYXOS phase:
INANNA running not in a Python process but as a living system on hardware.
Bootable from USB. Persistent. Always-on.

---

## Hardware Roadmap (DGX Scaling Ladder)

| Stage | Hardware | Purpose |
|---|---|---|
| Now | Development machine (Windows 11 + LM Studio) | Cycles 1-6 development |
| Next | DGX Spark | First dedicated INANNA node, local inference |
| Future | DGX Station GB300 | Full Faculty deployment |
| Horizon | DGX B300 / SuperPOD NVL72 | Multi-model orchestration at scale |

---

## Cycle 7 — NYXOS Vision

INANNA as a bootable sovereign OS substrate:
- NixOS base (declarative, reproducible)
- INANNA NYX server as a systemd service
- LM Studio models loaded at boot
- Persistent memory across reboots
- No Windows dependency
- Network-accessible from any device on the local network

The NixOS ISO above is the seed of this vision.
Phase 7.1 will define the NixOS configuration (configuration.nix)
that installs INANNA as a system service.

---

*This document grows as the hardware evolves.*
*The ISO path must be updated if the file moves.*

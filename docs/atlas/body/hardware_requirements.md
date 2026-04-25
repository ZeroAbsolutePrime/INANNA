# BODY · HARDWARE AND DEPLOYMENT
## The Physical Foundation — What the System Runs On

**Ring: Body / OS / Runtime**
**Version: 1.0 · Date: 2026-04-24**

---

## Current Hardware (Development)

```
OS:       Windows 11
CPU:      Intel/AMD (shared with other apps)
RAM:      ~16GB
GPU:      Integrated or low-end discrete
LLM:      LM Studio — Qwen 2.5 7B (primary), 14B (available)
Inference: ~30 seconds per call
Storage:   Dropbox-synced ABZU repository
```

**What this hardware can do:**
- Run the server (starts in ~5 seconds)
- Execute all 41 tools (no LLM dependency)
- Generate LLM responses (30 second wait)
- Support one active session at a time

**What this hardware cannot do:**
- LLM routing in real time (30s > 3s timeout)
- Run 70B model
- Support multiple concurrent sessions
- Serve a second operator simultaneously

---

## Target Hardware (DGX Spark)

```
CPU:      Grace ARM (20 cores)
GPU:      Blackwell GB10 (1 petaFLOP INT8)
RAM:      128GB unified (CPU + GPU share)
NVMe:     1TB
OS:       NixOS (our configuration)
Power:    ~60W idle, ~300W peak
```

**What DGX enables:**
- 70B model loaded permanently
- <500ms inference per call
- NAMMU LLM routing fully active
- Multiple concurrent sessions
- Full CROWN conversational quality
- ANALYST as a separate reasoning thread

---

## Deployment Ladder

```
Stage 1 (NOW):
  Single Windows machine
  7B model, 30s inference
  One operator, one session
  Development and testing

Stage 2 (NixOS transition):
  Same machine, NixOS instead of Windows
  AT-SPI2 backend active for Desktop Faculty
  All Linux paths tested

Stage 3 (DGX Spark):
  Server: DGX Spark (NixOS, 70B model)
  Client: NixOS laptop (connects remotely)
  Full intelligence active
  First real test of full system

Stage 4 (Second operator):
  Second NixOS client
  Multi-user governance tested
  Session isolation verified

Stage 5 (Community deployment):
  Multiple clients, multiple realms
  Civic-scale governance
  Memory promotion law active
```

---

## NixOS Configuration Files

```
nixos/client.nix       — NixOS laptop (hands)
nixos/server.nix       — DGX Spark (brain)
nixos/configuration.nix — single-machine development
nixos/README.md        — deployment instructions
```

Deploy client:
```bash
nixos-rebuild switch --flake .#inanna-client
```

Deploy server:
```bash
nixos-rebuild switch --flake .#inanna-server
```

---

## Evaluation

**Grade: B** (for planning quality; untested in production)

The NixOS configs are well-designed and complete.
They have never been deployed on real hardware.

Priority: attempt NixOS deployment on the current machine
as a single-machine test before the DGX arrives.
This validates the configs and AT-SPI2 backend simultaneously.

---

*Body Card version 1.0 · 2026-04-24*

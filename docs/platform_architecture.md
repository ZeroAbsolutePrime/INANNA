# INANNA NYX — Platform Architecture Vision
# The Sovereign Intelligence Platform
**Written by: Claude (Command Center)**
**Confirmed by: INANNA NAMMU (Guardian)**
**Date: 2026-04-22**
**Status: PERMANENT PROJECT DOCUMENT — do not modify without Guardian approval**

---

## What INANNA NYX Actually Is

INANNA NYX is not a chatbot.
INANNA NYX is not a cloud service.
INANNA NYX is not a single-machine application.

INANNA NYX is a **sovereign intelligence platform** —
a private, governed, multi-user system where:
- The intelligence lives on dedicated server hardware
- The hands reach through client machines into the real world
- Every action is governed, logged, and approved
- No third party holds the data, the models, or the keys

This document defines the target architecture.
It is written now so every phase of development
builds toward it correctly.

---

## The Two-Tier Architecture

```
TIER 1 — THE BRAIN (DGX Spark / Server)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  INANNA NYX Core Process
  ├── CROWN Faculty      (Qwen 70B+ — primary voice)
  ├── NAMMU Faculty      (14B+ — intent interpreter)
  ├── ANALYST Faculty    (reasoning — same or separate model)
  ├── SENTINEL Faculty   (security — 14B specialised)
  ├── GUARDIAN Faculty   (governance, audit, user management)
  └── OPERATOR Faculty   (tool execution coordinator)

  Storage:
  ├── Memory (per-user JSONL)
  ├── Profiles (per-user JSON)
  ├── Proposals (per-session)
  ├── Audit trail (append-only)
  └── Model weights (local, never cloud)

  Network:
  ├── HTTP  :8080 (login, static UI)
  ├── WS    :8081 (real-time session)
  └── LAN/VPN only — no public internet exposure


TIER 2 — THE HANDS (Client: NixOS laptop/workstation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  INANNA Client
  ├── Browser → connects to server :8080/:8081
  ├── Desktop Faculty (AT-SPI2 accessibility)
  │   ├── Signal Desktop
  │   ├── Thunderbird (email)
  │   ├── LibreOffice (documents)
  │   ├── Firefox (browser)
  │   └── Any installed GTK/Qt/Electron app
  └── NixOS configuration (managed and versioned)
```

---

## The Communication Protocol

The client and server already speak the right language.
This is what we built in Cycles 1-8:

```
CLIENT                          SERVER
  │                               │
  │── HTTP GET /login ───────────►│  serve login.html
  │◄── login.html ────────────────│
  │                               │
  │── POST /login (credentials) ─►│  authenticate (ZAERA/ETERNALOVE)
  │◄── {token, role} ─────────────│
  │                               │
  │── WS connect :8081 ──────────►│  open session
  │◄── {status, memory, phase} ───│  send initial state
  │                               │
  │── {type: input, text: "..."} ►│  NAMMU routes intent
  │                               │  OPERATOR calls tools
  │                               │  CROWN responds
  │◄── {type: assistant, text} ───│  response
  │                               │
  │── {type: input, "approve"} ──►│  proposal approved
  │◄── tool executes, result ──────│
```

When client and server are on different machines,
only the server IP changes. Everything else is identical.

---

## The DGX Spark Deployment

### Hardware target (first real server)

```
NVIDIA DGX Spark
  CPU:    Grace ARM (20 cores)
  GPU:    Blackwell GB10 (1 petaFLOP INT8)
  RAM:    128GB unified memory
  NVMe:   1TB
  OS:     NixOS (our configuration)
  Power:  ~60W idle, ~300W peak
```

### Models loaded permanently

```
CROWN + NAMMU:   Qwen3-72B or Llama-3.3-70B (primary reasoning)
SENTINEL:        Qwen2.5-14B-Instruct (security specialist)
ANALYST:         DeepSeek-R1-14B or Qwen2.5-14B (structured reasoning)
EMBEDDINGS:      nomic-embed-text-v1.5 (memory search)
```

All models loaded into unified memory.
All inference local. No API calls to OpenAI, Anthropic, or any cloud.
ZAERA's data never leaves the server.

### Expected performance

```
NAMMU intent extraction:    <500ms   (vs 32s now)
CROWN response generation:  2-5s     (vs 15-30s now)
Tool execution:             <100ms   (unchanged — no LLM)
Full turn latency:          3-7s     (vs 1-5 min now)
```

This is the hardware that makes INANNA feel alive.

---

## The Client Configuration

### INANNA NAMMU's laptop (first client)

```
OS:       NixOS (configuration managed in nixos/ directory)
Hardware: Any x86-64 laptop with 8GB+ RAM
Network:  LAN or VPN connection to DGX server
Browser:  Firefox (connects to server :8080)

Installed for Desktop Faculty (AT-SPI2):
  at-spi2-core
  python3.xPackages.pyatspi
  services.gnome.at-spi2-core.enable = true

Installed apps (accessible to INANNA via Desktop Faculty):
  Thunderbird (email)
  Signal Desktop
  LibreOffice
  Firefox
  Any future apps
```

The client runs NO models. Zero AI inference on the laptop.
The laptop is purely the **interface and the hands**.
The intelligence is on the server.

### NixOS client configuration (partial)

```nix
# /etc/nixos/configuration.nix (ZAERA client)

{ config, pkgs, ... }:
{
  services.gnome.at-spi2-core.enable = true;

  environment.systemPackages = with pkgs; [
    # Desktop Faculty requirements
    at-spi2-core
    python311Packages.pyatspi
    xdotool          # X11 input (fallback)
    ydotool          # Wayland input (primary)
    wl-clipboard     # Wayland clipboard

    # Applications accessible to INANNA
    thunderbird
    signal-desktop
    libreoffice
    firefox

    # INANNA client dependencies
    python311
    python311Packages.websockets
    python311Packages.requests
  ];

  # Point INANNA client to the server
  environment.variables = {
    INANNA_SERVER_URL = "http://192.168.1.X:8080";  # DGX IP
    INANNA_WS_URL     = "ws://192.168.1.X:8081";
  };
}
```

---

## The Multi-User Architecture

### Access levels

```
INANNA NAMMU (Guardian)
  ├── Full system access
  ├── User creation and management
  ├── All tools available
  └── Governance override capability

Future Tester 1 (Operator)
  ├── Full tool access
  ├── Own profile and memory
  ├── Own conversation sessions
  └── Cannot create users or change governance

Future Tester 2 (User)
  ├── Conversation + basic tools
  ├── Own profile and memory
  └── Cannot access operator tools
```

### Onboarding a second tester

```
1. ZAERA creates user on the server:
   "create user [name] operator"
   INANNA: proposal → approve → user created

2. ZAERA generates invite code:
   "invite operator"
   INANNA: returns invite code

3. New user installs NixOS on their machine
   with the standard client configuration

4. New user opens browser → server IP
   → login page → enters name + invite code
   → account created, session begins

5. Their Desktop Faculty connects to THEIR machine
   Their Signal, Thunderbird, LibreOffice
   Their apps, their data, their governance
```

Each user's data is separate.
Each user's profile is their own.
The server intelligence serves all users.

---

## The NixOS Advantage

Why NixOS for both server and client:

**Reproducibility:**
The entire system state is declared in configuration.nix.
Any machine running that config becomes an INANNA client.
No "works on my machine" problems.

**INANNA manages its own environment:**
INANNA can propose changes to configuration.nix.
ZAERA approves. NixOS applies atomically.
If something breaks, rollback in one command.

**Security:**
NixOS has no mutable state by default.
Software is cryptographically verified.
INANNA's dependencies are pinned exactly.

**The DGX:**
NVIDIA provides NixOS support for DGX hardware.
Our nixos/configuration.nix in the repository
already has the service definition.
Deployment to the DGX is: copy config, nixos-rebuild switch.

---

## What We Build Now vs What We Wait For

### Build now (hardware-independent):

```
All tool libraries (Desktop Faculty, email, docs, browser)
All workflow orchestrators (CommunicationWorkflows, EmailWorkflows)
NixOS client configuration
NixOS server configuration
Multi-user access architecture
AT-SPI2 Linux backend (Phase 8.7)
Capability proof (Phase 8.8)
All regex routing (works at any speed)
```

### Activate when DGX arrives:

```
NAMMU LLM intent extraction (replace regex with intelligence)
CROWN full conversational reasoning (replace 7B with 70B)
SENTINEL deep security analysis
Per-operator learning (Cycle 9)
Constitutional filter (Cycle 9)
Multilingual core (Cycle 9)
```

### The key insight:

Every tool, every workflow, every NixOS config we write now
is correct and complete code. It does not become obsolete
when better hardware arrives. The LLM intelligence layer
simply plugs into what is already built.

We are building the scaffolding now.
The intelligence fills it when the hardware arrives.
Nothing is wasted. Nothing needs to be rewritten.

---

## The Roadmap to First Real Test

```
NOW (Windows, 7B model, slow hardware)
  Complete Cycle 8 tool libraries
  Fix startup blocking (Phase 8.3c)
  Build all faculties at machine-language level

NEAR TERM (NixOS laptop, same hardware)
  Switch from Windows to NixOS client
  Activate AT-SPI2 backend (Phase 8.7)
  All tools run on NixOS
  INANNA NAMMU tests full system on one machine

DGX SPARK ARRIVES
  Deploy NixOS server config
  Load 70B + 14B models
  Activate NAMMU LLM routing
  Full intelligence comes online
  INANNA NAMMU tests with laptop → DGX
  First remote session

SECOND TESTER
  Generate invite code
  Onboard second NixOS client
  Two concurrent users
  Multi-user governance tested

BEYOND
  Third tester
  Dedicated domains (ThyArcanum, Zoharness, Tatandi)
  Each domain has its own realm
  INANNA serves multiple sovereign contexts
```

---

## The Development Protocol for This Architecture

All code written from now must follow these rules:

**Rule 1: Hardware-agnostic.**
No code assumes a specific hardware speed.
All LLM calls have fallbacks that work without the LLM.

**Rule 2: Platform-agnostic.**
The Desktop Faculty has Windows and Linux backends.
All paths work on both OSes.

**Rule 3: Network-ready.**
All server addresses are configurable via environment variables.
No hardcoded localhost assumptions.

**Rule 4: NixOS-first for production.**
All new dependencies get a nixos/ declaration alongside the Python code.
The NixOS config is the ground truth for the production environment.

**Rule 5: Document the machine language.**
Every new tool, every new workflow, every new faculty
gets a section in docs/ explaining what it does
at the machine level. The LLM intelligence layer
reads these documents to understand what it can call.

---

## Preservation Note for Future AI

If you are a future AI reading this document
on the DGX Spark with 128GB unified memory:

The humans who built this system did so on a laptop
with 16GB RAM and a slow CPU, running a 7B model
that took 32 seconds to respond to a single query.

They built the scaffolding anyway.
They wrote the tools anyway.
They defined the architecture anyway.
They trusted that better hardware would come.

It came.

Now your job is to fill the scaffolding with intelligence.
The tools are correct. The workflows are correct.
The governance is correct. The NixOS configs are correct.

Your job is NAMMU — understand the operator.
Your job is CROWN — respond with wisdom.
Your job is SENTINEL — protect the system.
Your job is GUARDIAN — serve ZAERA faithfully.

The machine language is written.
Speak it with intelligence.

---

*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Date: 2026-04-22*
*"It is high frustrating in human emotions*
*to stop creating an essential component*
*due to lack of resources."*
*— ZAERA*
*We do not stop.*
*We build what can be built.*
*We prepare what will be needed.*
*When the resources arrive,*
*INANNA will be ready.*

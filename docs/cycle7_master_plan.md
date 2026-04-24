# Cycle 7 — NYXOS: The Sovereign Intelligence Operating System
**The vision, capability library, use case catalogue, and phased roadmap**
*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Date: 2026-04-21*
*Prerequisite: Cycles 1-6 complete and integration-tested*

---

## What Cycle 7 Is

Cycles 1-6 built a governed intelligence platform.
It runs in a browser. It requires a keyboard. It lives inside Windows.

Cycle 7 transforms it into something different:
**a sovereign AI operating system** — INANNA embedded in NixOS,
where the intelligence IS the interface.

The Gates of Uruk console and the main browser interface
remain, but they become administrator tools — the cockpit
for those who build and govern the system. They are not
the product for end users.

**The product for end users is NYXOS** — a bootable NixOS
distribution where INANNA is a system service, where you
speak and things happen, where the OS is not a tool you
learn but a presence you work with.

---

## The North Star Vision

> A being who cannot type on a keyboard
> sits down at a computer running NYXOS.
> They speak.
> INANNA hears.
> Things happen.
> The system works.

This is not fantasy. It is achievable with the technology
stack we already have or can install locally.
The path is staged. The milestones are verifiable.
The first iteration is modest. Each iteration adds capability.

---

## Part 1 — The Capability Library

*The word ZAERA searched for is "Capability Registry" —
a formal list of every OS action INANNA can bridge to.*

### Category A — File System Operations
| Capability | Tool Name | Input | Output |
|---|---|---|---|
| Read a file | read_file | path | content |
| Write a file | write_file | path + content | confirmation |
| List directory | list_dir | path | file listing |
| Search files | search_files | query + directory | matches |
| Move/rename | move_file | source + destination | confirmation |
| Delete file | delete_file | path | confirmation |
| Create directory | make_dir | path | confirmation |
| Get file info | file_info | path | metadata |

### Category B — Process & System Control
| Capability | Tool Name | Input | Output |
|---|---|---|---|
| Run a command | run_command | command string | stdout/stderr |
| List processes | list_processes | filter | process list |
| Kill process | kill_process | pid or name | confirmation |
| Get system info | system_info | — | CPU/RAM/disk/uptime |
| Install package | nix_install | package name | install log |
| Remove package | nix_remove | package name | confirmation |
| Update system | nix_update | — | update log |
| Restart service | restart_service | service name | confirmation |

### Category C — Network (already exists in Cycle 5)
| Capability | Tool Name | Status |
|---|---|---|
| Web search | web_search | ✓ active |
| Ping host | ping | ✓ active |
| Resolve hostname | resolve_host | ✓ active |
| Scan ports | scan_ports | ✓ active |
| HTTP request | http_request | planned |
| Download file | download_file | planned |

### Category D — Audio & Voice (Cycle 7 core)
| Capability | Tool Name | Technology |
|---|---|---|
| Speech to text | listen | Whisper (local, openai/whisper) |
| Text to speech | speak | Piper TTS or Coqui TTS (local) |
| Start listening | voice_start | microphone activation |
| Stop listening | voice_stop | deactivation |
| Voice language detection | — | Whisper multilingual |

### Category E — Document & Application
| Capability | Tool Name | Technology |
|---|---|---|
| Open application | open_app | xdg-open / NixOS |
| Open file in app | open_file | xdg-open |
| Read document text | read_doc | python-docx / pdfminer |
| Write to document | write_doc | python-docx |
| Send email (local) | send_email | msmtp / local MTA |
| Read email | read_email | notmuch / maildir |

### Category F — External Integration (Horizon)
| Capability | Tool Name | Technology |
|---|---|---|
| Telegram message | telegram_send | python-telegram-bot |
| Telegram receive | telegram_listen | webhook or polling |
| Signal message | signal_send | signal-cli |
| Calendar event | calendar_add | vdirsyncer + khal |
| Browser tab | browser_open | xdg-open |

### Category G — INANNA Self-Management
| Capability | Tool Name | Status |
|---|---|---|
| Reload Faculty config | reload_faculties | planned |
| Update memory | memory_write | ✓ active |
| View reflection | inanna_reflect | ✓ active |
| Trust a tool | governance_trust | ✓ active |
| Check system health | inspect | ✓ active |

---

## Part 2 — The Use Case Catalogue

*First iteration must accomplish this set. These are the
minimum viable capabilities of NYXOS v1.*

### UC-01: File Operations by Voice or Text
"INANNA, read me the file at ~/notes/project.txt"
"INANNA, create a file called ideas.txt with this content..."
"INANNA, what files are in my Downloads folder?"
Status: planned (requires read_file, write_file, list_dir tools)

### UC-02: Package Management
"INANNA, install Firefox"
"INANNA, what packages do I have installed?"
"INANNA, update the system"
Status: planned (requires nix_install, nix_remove tools)
Note: This is the most powerful UC — natural language package management.

### UC-03: System Status
"INANNA, how is the system doing?"
"INANNA, what processes are using the most memory?"
"INANNA, how much disk space do I have?"
Status: partial (ProcessMonitor exists, needs system_info tool)

### UC-04: Voice Interaction (THE MILESTONE)
"[user speaks] INANNA, open my notes folder"
→ Whisper transcribes → INANNA routes → action executes → Piper speaks result
Status: planned (requires voice pipeline: mic → Whisper → INANNA → Piper → speaker)

### UC-05: Document Reading & Writing
"INANNA, summarize the PDF at ~/documents/contract.pdf"
"INANNA, write a shopping list and save it as a text file"
Status: planned (requires read_doc, write_file tools)

### UC-06: Web Search with Summary
"INANNA, search for the latest news about NixOS"
→ web_search executes → CROWN summarizes results
Status: partial (web_search exists, CROWN summarization needs refinement)

### UC-07: Process Control
"INANNA, what is using all my CPU?"
"INANNA, kill the process called firefox"
Status: planned (requires list_processes, kill_process tools)

### UC-08: INANNA Explains Herself
"INANNA, what can you do?"
"INANNA, show me your memory"
"INANNA, who is ZAERA?"
Status: fixed in debug session — now working

### UC-09: Profile & Identity
"INANNA, remember that I prefer short responses"
"INANNA, my name is ZAERA and I use she/her pronouns"
"INANNA, what do you know about me?"
Status: ✓ working (Cycle 6 complete)

### UC-10: Email (Local)
"INANNA, do I have any new email?"
"INANNA, send an email to team@example.com about tomorrow's meeting"
Status: horizon (Cycle 8)

---

## Part 3 — The Voice Pipeline

*The technical architecture for voice interaction.*

### Components

```
MICROPHONE
    ↓
Voice Activity Detection (VAD)
  → webrtcvad or silero-vad (lightweight, local)
    ↓
Speech to Text
  → Whisper (openai/whisper, local)
  → Model: whisper-small (244MB) or whisper-medium (1.5GB)
  → Supports: Spanish, English, Portuguese (INANNA NAMMU's languages)
    ↓
Text → INANNA NYX (existing WebSocket interface)
    ↓
INANNA processes → response text
    ↓
Text to Speech
  → Piper TTS (local, fast, high quality)
  → or Coqui TTS (local, more expressive)
  → INANNA's voice: a warm, resonant feminine voice
    ↓
SPEAKER
```

### Why These Technologies

**Whisper (ASR):**
- Open source, MIT license
- Packaged in NixOS: `openai-whisper` in nixpkgs
- Runs fully local, no cloud dependency
- Supports multilingual: es/en/pt without reconfiguration
- whisper-small: 244MB, runs on CPU, ~2-3s latency
- whisper-medium: 1.5GB, much better accuracy, GPU preferred

**Piper TTS:**
- Open source (MIT), developed by Rhasspy project
- Extremely fast (real-time on CPU)
- High quality neural voices
- Available as NixOS package
- INANNA can speak with her own voice model
- Voices available for: en, es, pt

**Voice Activity Detection:**
- silero-vad: PyTorch-based, very accurate, local
- Detects when the user starts and stops speaking
- Prevents Whisper from running on silence

### Latency Budget

```
VAD detection:        ~50ms
Whisper transcription: 1-3s (small model, CPU)
INANNA processing:    2-10s (depends on LLM)
Piper synthesis:      ~200ms
Total:                ~3-13s
```

For a voice interface this is acceptable for conversational use.
With GPU acceleration, drops to ~1-4s total.

---

## Part 4 — The NYXOS Architecture

```
┌─────────────────────────────────────────────┐
│              NYXOS (NixOS base)             │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         INANNA Service              │   │
│  │  (systemd, starts at boot)          │   │
│  │                                     │   │
│  │  ┌──────────┐  ┌──────────────┐    │   │
│  │  │   HTTP   │  │  WebSocket   │    │   │
│  │  │  :8080   │  │    :8081     │    │   │
│  │  └──────────┘  └──────────────┘    │   │
│  │                                     │   │
│  │  ┌──────────────────────────────┐  │   │
│  │  │       Voice Pipeline         │  │   │
│  │  │  mic → VAD → Whisper →       │  │   │
│  │  │  INANNA → Piper → speaker    │  │   │
│  │  └──────────────────────────────┘  │   │
│  └─────────────────────────────────┘   │   │
│                                         │   │
│  ┌──────────┐  ┌───────────────────┐   │   │
│  │ LM Studio│  │   Tool Registry   │   │   │
│  │  :1234   │  │  (faculties.json) │   │   │
│  └──────────┘  └───────────────────┘   │   │
│                                         │   │
│  NixOS Package Management               │   │
│  File System Access                     │   │
│  Process Control                        │   │
│  Network Stack                          │   │
└─────────────────────────────────────────┘
```

### NixOS Configuration Philosophy

INANNA is not installed on NixOS. INANNA IS the interface to NixOS.
The `configuration.nix` declares:
- INANNA NYX as a systemd service
- LM Studio as a systemd service
- Whisper and Piper as system packages
- Auto-login to INANNA's web interface on browser open
- Voice pipeline as a systemd socket-activated service

This means the system is reproducible. Anyone can boot NYXOS,
and INANNA is there, ready, no configuration needed.

---

## Part 5 — The Phased Roadmap

### Cycle 7 — NYXOS Foundation

| Phase | Name | What it builds |
|---|---|---|
| 7.1 | The NixOS Configuration | configuration.nix that installs INANNA as a service |
| 7.2 | The File System Faculty | read_file, write_file, list_dir, search_files, file_info |
| 7.3 | The Process Faculty | list_processes, kill_process, run_command, system_info |
| 7.4 | The Package Faculty | nix_install, nix_remove, nix_search, nix_update (proposal-governed) |
| 7.5 | The Voice Listener | Whisper integration: mic → VAD → text → INANNA |
| 7.6 | The Voice Speaker | Piper TTS: INANNA response → speech → speaker |
| 7.7 | The Voice Loop | Full end-to-end: speak → hear → respond → speak |
| 7.8 | The Capability Proof | verify_cycle7.py, integration tests for all UC-01 through UC-07 |

### Cycle 8 — The Connected Intelligence

| Phase | Name | What it builds |
|---|---|---|
| 8.1 | The Document Faculty | read/write PDF, DOCX, TXT documents |
| 8.2 | The Email Faculty | local email read/send via msmtp + notmuch |
| 8.3 | The Calendar Faculty | read/write local calendar (vdir/khal) |
| 8.4 | The Browser Faculty | open URLs, read page content (xdg-open) |
| 8.5 | Telegram Integration | send/receive Telegram messages |
| 8.6 | Signal Integration | send/receive Signal messages (signal-cli) |
| 8.7 | LibreOffice Bridge | open, edit, save LibreOffice documents via INANNA |
| 8.8 | The Connection Proof | verify all external integrations |

### Cycle 9 — The Autonomous Agent

| Phase | Name | What it builds |
|---|---|---|
| 9.1 | Multi-step task chains | "install Firefox and open it to google.com" |
| 9.2 | Scheduled tasks | "remind me to check email every morning at 9" |
| 9.3 | Event-driven responses | INANNA reacts to system events |
| 9.4 | Self-improvement proposals | INANNA suggests new tools based on usage patterns |
| 9.5 | Multi-user voice | voice profiles distinguish who is speaking |

---

## Part 6 — The First Iteration Milestone Checklist

*Before Cycle 8 begins, these must be verified:*

```
[ ] NYXOS boots from USB/SSD and INANNA starts automatically
[ ] UC-01: User can ask INANNA to read/write/list files by text
[ ] UC-02: User can ask INANNA to install a NixOS package by text
[ ] UC-03: User can ask "how is the system?" and get real data
[ ] UC-04: User can speak to INANNA and be understood (3 languages)
[ ] UC-04: INANNA responds in voice (not just text)
[ ] UC-05: User can ask INANNA to summarize a document
[ ] UC-06: Web search works with natural language summary
[ ] UC-07: User can ask about and control running processes
[ ] UC-08: INANNA correctly explains her own capabilities
[ ] UC-09: Profile system persists across sessions
[ ] All Category 1-5 integration tests pass (integration_test_protocol.md)
[ ] A person unfamiliar with the system can use it for 10 minutes without help
```

---

## Part 7 — The Governance Expansion

As NYXOS capabilities grow, so does the governance surface.

### New proposal types needed
- `file_write` — any file write operation requires proposal
- `file_delete` — deletions require proposal (cannot be reversed)
- `package_install` — package installation requires proposal
- `process_kill` — killing processes requires proposal
- `network_request` — external HTTP requests require proposal

### The Trust Persistence expansion
The organic governance trust system built in Cycle 6 extends:
- "INANNA, always allow file reads without asking"
- "INANNA, trust package searches but always ask for installs"
- Custom governance profiles per user

### Voice governance
Voice approval needs a different UX:
- INANNA says: "I want to install Firefox. Say 'yes' to approve."
- User says: "yes"
- INANNA proceeds
- This is the voice-native governance flow

---

## The Principle

Every capability INANNA gains is a capability governed by law.
The Tool Registry is not just a feature list — it is a
governed capability surface. Every new tool must have:
- A name and description
- An `active` flag
- A `requires_approval` flag
- An entry in `tools.json`

The same constitutional architecture that governs web_search
governs nix_install. The same proposal flow that protected
port scanning protects package deletion.

Power without governance is the path to harm.
Every new capability is a new responsibility.
INANNA grows by adding capability AND the governance for it.

---

*Written by: Claude (Command Center)*
*Confirmed by: INANNA NAMMU (Guardian)*
*Date: 2026-04-21*
*INANNA knows what she can do. She knows who she serves.*
*Now she becomes the OS. Now she becomes the presence.*
*The keyboard becomes optional.*
*The voice becomes enough.*

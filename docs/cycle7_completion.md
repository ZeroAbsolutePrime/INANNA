# Cycle 7 Completion Record
### NYXOS and the Capability Surface

*Written after Phase 7.8 verification.*
*Date: 2026-04-21*

---

## What Cycle 7 Set Out to Build

Cycle 7, as chartered in [cycle7_master_plan.md](cycle7_master_plan.md),
was the shift from browser-bound intelligence to NYXOS: INANNA as a
sovereign operating system layer. The goal was not only to add more
tools. The goal was to let INANNA act as the governed interface to
files, processes, packages, authentication, and eventually voice, while
keeping the constitutional model from the earlier cycles intact.

---

## What Was Actually Built

**Phase 7.1 - The NixOS Configuration.** The repository gained the
`nixos/` deployment scaffold: `configuration.nix`,
`inanna-nyx.service`, `install.sh`, and a `README.md` for the NixOS
embodiment path. Cycle 7 therefore began by defining how NYXOS boots
and how INANNA is meant to live as a system service rather than just a
script.

**Phase 7.2 - The File System Faculty.** `FileSystemFaculty` added
governed file reads, directory listings, metadata inspection, file
search, and writes, with path safety rules, forbidden locations, size
caps, and readable formatting. Natural-language filesystem requests now
route through OPERATOR instead of requiring raw command syntax.

**Phase 7.3 - The Process Faculty.** `ProcessFaculty` brought governed
system inspection: system health, process lists, safe command
execution, and process termination. The implementation supports
cross-platform fallbacks when `psutil` is absent, keeping the system
truth readable on more than one host.

**Phase 7.4 - The Package Faculty.** `PackageFaculty` added
cross-platform package search, package listing, install, and remove
operations across `winget`, `apt`, `brew`, and `nix`, while keeping
destructive actions under proposal governance. This is what made
Cycle 7 the start of natural-language software management.

**Phase 7.5 - The Voice Listener.** The voice listener scaffold was
added under `inanna/voice/`: microphone capture, VAD assumptions,
faster-whisper transcription, and WebSocket forwarding into INANNA.
This phase shipped as a built but deferred capability. The files exist,
the constants are in place, and the activation step remains
intentionally postponed.

**Phase 7.6 - Authentication & Login.** Cycle 7 added `AuthStore` with
PBKDF2-HMAC-SHA256 password hashing, the seeded Guardian account
`ZAERA / ETERNALOVE`, HTTP login routes, cookie-backed browser session
restoration, and the standalone full-page login surface at
`ui/static/login.html`.

**Phase 7.7 - The UX Polish Pass.** The main interface was sharpened:
proposal badges pulse visibly, help topics render as structured panels,
package follow-ups keep their short-term context, side panel expansion
state survives reconnects, and the welcome line now draws its tool count
from the live OPERATOR registry instead of a hard-coded number.

**Phase 7.8 - The Capability Proof.** The final phase did not add a new
runtime capability. It wrote the offline verifier, corrected proof-path
bugs, aligned identity state with the completed cycle, and documented
what Cycle 7 now reliably is.

---

## Current Capability Surface

The current governed tool registry contains **18 tools across 4
categories**:

- Network: `web_search`, `ping`, `resolve_host`, `scan_ports`
- Filesystem: `read_file`, `list_dir`, `file_info`, `search_files`, `write_file`
- Process: `list_processes`, `system_info`, `kill_process`, `run_command`
- Package / software: `search_packages`, `list_packages`, `install_package`, `remove_package`, `launch_app`

On the Guardian machine used for the proof run, the software registry
loads **152 local software entries** across `winget` and Windows App
Paths. `launch_app` is therefore backed not just by package metadata but
also by executable discovery.

---

## Authentication State

Cycle 7 now has a real login boundary.

- `AuthStore` stores password hashes, never plaintext passwords
- Password hashing uses PBKDF2-HMAC-SHA256
- The Guardian account `ZAERA` is seeded on server startup
- The Guardian password is `ETERNALOVE`
- Browser login is served from `GET /` and `GET /login`
- Authenticated users land at `GET /app`

This means INANNA's browser surface is no longer an open console by
default. Entry is now mediated by identity.

---

## What Remains Deferred

- Voice activation is still deferred. The voice listener files and
  constants exist, but the proof phase deliberately did not enable live
  microphone use.
- The Cycle 7 unfamiliar-user milestone remains pending:
  a person unfamiliar with the system has not yet been verified using it
  unaided for ten minutes.
- The voice speaker and voice loop remain part of the future NYXOS path,
  not the presently proven capability set.

---

## What verify_cycle7.py Confirmed

`inanna/verify_cycle7.py` runs **81 offline checks** and makes no
network calls. It verifies:

- Authentication and login artifacts
- File system faculty behavior
- Process faculty behavior
- Package faculty detection and offline parsing
- Software registry loading and launch surface
- Tool registry size and approval rules
- NixOS deployment files
- Deferred voice-listener scaffold files and constants
- UX polish hooks
- Final identity state for Phase 7.8

On the proof run for this completion, the verifier passed **81 / 81**
checks, and the full repository unit suite passed at **432 / 432**
tests.

---

## Cycle 7 Milestone Checklist

Taken from [cycle7_master_plan.md](cycle7_master_plan.md), the current
state is:

- [x] NYXOS NixOS service config ready (`nixos/` directory)
- [x] UC-01 File ops by text
- [x] UC-02 Package management by text
- [x] UC-03 System status by text
- [ ] UC-04 Voice pipeline activated end-to-end
- [x] UC-05 Document reading via file access
- [x] UC-06 Web search with natural-language summary
- [x] UC-07 Process control
- [x] UC-08 INANNA explains herself correctly
- [x] UC-09 Profile persists across sessions
- [x] Authentication: `ZAERA / ETERNALOVE`
- [x] Software cards with launch buttons
- [x] HTTP server path verified
- [ ] Unfamiliar user can operate the system unaided for ten minutes

That leaves **12 of 14** milestone items complete. The two remaining
items are intentionally deferred rather than missing by accident.

---

## What Cycle 7 Did Not Build

- No live voice activation in the proof phase
- No voice speaker path
- No unfamiliar-user usability certification yet
- No Cycle 8 external integrations such as documents, email, calendar,
  browser control, Telegram, or Signal

Cycle 7 therefore ends as a strong operating substrate, not yet as the
fully embodied NYXOS end state imagined in the master plan.

---

## Bridge to Cycle 8

Cycle 8 opens the connected layer: document handling, email, calendar,
browser actions, and broader external integration. Cycle 7 proved that
INANNA can now stand on a governed operating-system capability surface.
Cycle 8 determines how far that surface can extend into the rest of a
person's digital world without losing the law that made the system safe
to grow in the first place.

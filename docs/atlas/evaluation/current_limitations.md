# EVALUATION · Current Limitations
## An Honest Accounting

**Ring: Evaluation**
**Version: 1.0 · Date: 2026-04-24**

---

## Hardware Limitations

| Limitation | Impact | Resolution |
|---|---|---|
| 7B model, 30s inference | LLM routing disabled | DGX Spark |
| ~16GB RAM | One session at a time | DGX Spark |
| Shared VRAM | Multiple models slow each other | Dedicated GPU |
| Windows (not NixOS) | AT-SPI2 backend untested | NixOS transition |

---

## Architectural Gaps

| Gap | Description | Priority |
|---|---|---|
| No agentic loop | Single tool call per turn | High — Cycle 10 |
| No semantic memory | Cannot query past memory by meaning | High — Cycle 10 |
| ANALYST not built | Named but no implementation | High — Cycle 10 |
| SENTINEL partial | Merged into other organs | Medium — Cycle 10 |
| Multi-user untested | Auth exists, never used with 2 users | High before Stage 4 |
| No session persistence | Restart loses context | Medium |
| No response streaming | Full wait before display | Medium |

---

## Known Bugs and Fragilities

| Issue | Severity | Notes |
|---|---|---|
| Regex fallbacks imperfect | Medium | Novel phrasing may fail to route |
| Catalan/Portuguese lexicon partial | Low | Works for common phrases |
| Calendar shows 0 events | Low | Google Calendar not synced to local SQLite |
| Signal reading unverified | Medium | Architecture correct, untested |
| LLM routing times out always | High | Hardware ceiling, not code bug |

---

## What Has Never Been Tested

- NixOS deployment (configs written, never applied)
- Two simultaneous users
- Server on one machine, client on another
- Calendar events (local SQLite always empty)
- Signal message reading
- AT-SPI2 Linux Desktop Faculty
- Multi-user memory isolation
- Proposal approval by non-guardian user

---

## What Passed Every Test

- 770+ unit tests passing
- All 41 tools dispatch correctly
- Email reads real Thunderbird MBOX
- Browser fetches real web pages
- Document reads real files
- Constitutional filter blocks correctly, passes safely
- NAMMU profile persists and enriches
- Server starts in < 5 seconds
- Multilingual routing (en/es/ca/pt) works via regex

---

## Honest Overall Assessment

The system is **architecturally sound and locally functional**.

It is not ready for:
- Production deployment with real users
- Multi-user operation
- Relying on LLM quality for any safety-critical decision
- Civic-scale deployment

It is ready for:
- Single-operator daily use (INANNA NAMMU)
- Testing and development
- Demonstrating the architecture to collaborators
- Handing over to a multi-agent platform for the next spiral

The gap between current state and the vision is real.
It is a gap of hardware and time, not of architecture.
The scaffolding is correct. The intelligence will fill it.

---

*Evaluation Card version 1.0 · 2026-04-24*

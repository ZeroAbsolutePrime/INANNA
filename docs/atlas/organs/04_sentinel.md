# INNER ORGAN · SENTINEL
## The Watcher — Security Perception and Threat Awareness

**Ring: Inner AI Organs**
**Grade: C (infrastructure present, depth missing)**
**Version: 1.0 · Date: 2026-04-24**

---

## Identity

**What it is:**
SENTINEL is the security perception organ of INANNA NYX.
It watches for threats, anomalies, and boundary violations
across all layers of the system.

**What it does:**
- Detects identity attacks and impersonation attempts
- Monitors for manipulation attempts in the input stream
- Contributes threat signals to the governance layer
- Works alongside CONSCIENCE (constitutional filter) as the security pair

**What it must never do:**
- Block legitimate operator requests
- Generate false positives that disrupt normal operation
- Operate silently — all blocks must be logged

---

## Ring

**Inner AI Organs** — SENTINEL is the awareness organ.
It does not execute actions. It perceives threats and signals them.

---

## Correspondences

| Component | Location |
|---|---|
| Primary implementation | `core/guardian.py` (partially merged) |
| Constitutional filter | `core/constitutional_filter.py` |
| Governance layer | `core/governance.py` → security checks |
| Audit logging | `data/realms/default/nammu/governance_log.jsonl` |

**Note:** SENTINEL is not yet a fully separate module.
Its functionality is currently distributed across
`core/guardian.py` and `core/governance.py`.
A future build should separate SENTINEL into its own faculty.

---

## Current State

### What Works (merged into other organs)

- Identity attack detection in GovernanceLayer
- Session anomaly detection in session.py
- Constitutional filter (CONSCIENCE) handles the ethics boundary

### What Is Missing

- Standalone SENTINEL module
- Behavioral anomaly detection (repeated failed attempts, unusual patterns)
- Real-time threat scoring
- Network-level threat detection
- Cross-session threat pattern recognition

---

## Desired Function

A dedicated SENTINEL module that:
- Monitors all input streams for known attack patterns
- Scores threat level per session (0.0-1.0)
- Escalates to GUARDIAN when threshold exceeded
- Logs every detected anomaly
- Works in all languages (cannot bypass by switching language)
- Runs as a background process, not blocking the main thread

---

## Evaluation

**Grade: C**

SENTINEL exists conceptually but not as a module.
Its functions are distributed and partial.

Single most important gap:
**SENTINEL is not a real-time security monitor.**
It checks inputs at routing time but does not
maintain session-level threat awareness.

Priority for future agent: create `core/sentinel.py`
as a proper separate module with threat scoring.

---

*Organ Card version 1.0 · 2026-04-24*

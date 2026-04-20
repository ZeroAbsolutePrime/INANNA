# CURRENT PHASE: Cycle 5 - Phase 5.5 - The Faculty Registry
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 5 - The Operator Console**
**Replaces: Cycle 5 Phase 5.4 - The Process Monitor (COMPLETE)**

---

## What This Phase Is

Phase 5.4 gave INANNA eyes on its own processes.
Phase 5.5 gives INANNA a formal registry of its intelligences.

Right now, the four Faculties (CROWN, ANALYST, OPERATOR, GUARDIAN)
are defined in Python code and partially in FacultyMonitor.
They cannot be extended without changing code.
Their charters are not readable from a file.
A domain-specialized Faculty (SENTINEL, PYTHIA, AESCULAPIUS)
cannot be added without touching Python.

Phase 5.5 moves all Faculty definitions into:
  inanna/config/faculties.json

And builds the Faculty Registry panel in the Operator Console.

This is the foundation that Phase 5.6 (Faculty Router) and
Phase 5.7 (Domain Faculty) depend on.

---

## What You Are Building

### Task 1 - inanna/config/faculties.json

Create: inanna/config/faculties.json

```json
{
  "faculties": {
    "crown": {
      "display_name": "CROWN",
      "domain": "general",
      "description": "Primary conversational voice and relational presence.",
      "charter_preview": "I am CROWN, the primary voice of INANNA NYX. I speak with warmth, precision, and constitutional honesty. I do not fabricate. I ground every response in approved memory.",
      "model_url": "",
      "model_name": "",
      "governance_rules": [],
      "active": true,
      "built_in": true,
      "color": "rose"
    },
    "analyst": {
      "display_name": "ANALYST",
      "domain": "reasoning",
      "description": "Structured reasoning and comparative analysis.",
      "charter_preview": "I am ANALYST. I reason systematically. I compare, contrast, and synthesize. I show my work. I flag uncertainty explicitly.",
      "model_url": "",
      "model_name": "",
      "governance_rules": [],
      "active": true,
      "built_in": true,
      "color": "ivory"
    },
    "operator": {
      "display_name": "OPERATOR",
      "domain": "tools",
      "description": "Bounded tool execution with proposal governance.",
      "charter_preview": "I am OPERATOR. I execute only approved tools from the registry. I propose before acting. I report results transparently.",
      "model_url": "",
      "model_name": "",
      "governance_rules": [
        "All tool executions require proposal approval",
        "No tool executes outside the registered tool list"
      ],
      "active": true,
      "built_in": true,
      "color": "amber"
    },
    "guardian": {
      "display_name": "GUARDIAN",
      "domain": "governance",
      "description": "System observation and governance health.",
      "charter_preview": "I am GUARDIAN. I watch the system. I report what I see. I do not act — I observe and present findings for the Guardian's judgment.",
      "model_url": "",
      "model_name": "",
      "governance_rules": [
        "Guardian Faculty may only observe — never act",
        "All alerts require Guardian (human) acknowledgment"
      ],
      "active": true,
      "built_in": true,
      "color": "lapis"
    },
    "sentinel": {
      "display_name": "SENTINEL",
      "domain": "security",
      "description": "Cybersecurity analysis, network threat assessment, vulnerability reasoning.",
      "charter_preview": "I am SENTINEL. I analyze security posture. I reason about threats and vulnerabilities. I perform passive analysis only. Any offensive or active capability requires explicit Guardian proposal approval.",
      "model_url": "http://localhost:1234/v1",
      "model_name": "",
      "governance_rules": [
        "Passive analysis only without explicit Guardian approval",
        "All offensive actions require Guardian proposal",
        "Never recommend exploiting a vulnerability without consent"
      ],
      "active": false,
      "built_in": false,
      "color": "danger"
    }
  }
}
```

### Task 2 - Update FacultyMonitor to read faculties.json

Update inanna/core/faculty_monitor.py:

- Load faculties.json at init
- FacultyRecord gains fields from the JSON:
    display_name, domain, description, charter_preview,
    governance_rules, active, built_in, color
- all_records() returns records for active faculties only
- format_report() uses display_name from config

The four built-in Faculties (crown, analyst, operator, guardian)
continue to function as before. Their call tracking and timing
are preserved. The JSON adds metadata — it does not replace
the runtime behavior.

### Task 3 - "faculty-registry" WebSocket command

Add command: faculty-registry

Returns all Faculties from faculties.json (both active and inactive):
```json
{
  "type": "faculty_registry",
  "faculties": [
    {
      "name": "crown",
      "display_name": "CROWN",
      "domain": "general",
      "description": "Primary conversational voice...",
      "charter_preview": "I am CROWN...",
      "governance_rules": [],
      "active": true,
      "built_in": true,
      "color": "rose",
      "mode": "connected",
      "call_count": 5,
      "last_called": "22:15"
    }
  ],
  "total": 5,
  "active": 4,
  "inactive": 1
}
```

The runtime data (mode, call_count, last_called) is merged from
FacultyMonitor. Static data (charter, governance_rules, color)
comes from faculties.json.

Add "faculty-registry" to STARTUP_COMMANDS and capabilities.

### Task 4 - Faculty Registry panel in console.html

Replace the placeholder in the Faculties panel with a live view.

On panel activate: send faculty-registry command.

Display each Faculty as a card:

BUILT-IN FACULTIES:
```
𒀭 CROWN                          ● connected
  general · Primary conversational voice
  calls: 5 · last: 22:15
  "I am CROWN, the primary voice of INANNA NYX..."
  [ view charter ]

𒁹 ANALYST                        ● connected
  reasoning · Structured reasoning and analysis
  calls: 2 · last: 22:10
  [ view charter ]
```

DOMAIN FACULTIES (inactive shown differently):
```
⚔ SENTINEL                       ○ inactive
  security · Cybersecurity analysis
  Governance: passive analysis only without approval
  [ activate ]   (disabled — Phase 5.7)
```

[ view charter ] expands to show the full charter_preview inline.
[ activate ] is present but shows a tooltip: "Domain Faculty activation coming in Phase 5.7"

Color coding matches the UI language:
  rose = CROWN (matches INANNA's message color)
  ivory = ANALYST
  amber = OPERATOR
  lapis = GUARDIAN
  danger = SENTINEL

### Task 5 - Update FacultyMonitor.format_report()

The format_report() string sent in the status payload to the
main interface currently uses hardcoded Faculty names.
Update it to read display_name from the loaded faculties.json.

### Task 6 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 5 - Phase 5.5 - The Faculty Registry"
Add "faculty-registry" to STARTUP_COMMANDS and capabilities.

### Task 7 - Tests

Update inanna/tests/test_faculty_monitor.py:
  - FacultyMonitor loads from faculties.json
  - all_records() returns 4 records (active only)
  - FacultyRecord has domain field
  - FacultyRecord has display_name field from config
  - FacultyRecord has charter_preview field
  - format_report() contains "CROWN" (from display_name)
  - "sentinel" not in all_records() (inactive)

Update test_commands.py: add faculty-registry.
Update test_identity.py: update CURRENT_PHASE assertion.
Update test_state.py: add faculty-registry.

---

## Permitted file changes

inanna/identity.py
inanna/main.py                  <- add faculty-registry command
inanna/config/
  faculties.json                <- NEW
inanna/core/
  faculty_monitor.py            <- MODIFY: load faculties.json,
                                           enrich FacultyRecord
  state.py                      <- add faculty-registry
inanna/ui/
  server.py                     <- add faculty-registry command
  static/console.html           <- replace Faculties placeholder
                                   with live Faculty Registry panel
inanna/tests/
  test_faculty_monitor.py       <- MODIFY: add config-driven tests
  test_identity.py              <- update phase
  test_state.py                 <- add faculty-registry
  test_commands.py              <- add faculty-registry

---

## What You Are NOT Building

- No Faculty activation (Phase 5.7)
- No Faculty model endpoint switching
- No charter editing via the UI
- No new domain Faculty beyond defining SENTINEL in the JSON
  (SENTINEL remains inactive: false until Phase 5.7)
- Do not modify index.html

---

## Definition of Done

- [ ] faculties.json exists with 5 Faculty definitions
- [ ] FacultyMonitor reads from faculties.json
- [ ] FacultyRecord enriched with domain, display_name, charter_preview
- [ ] faculty-registry command returns merged static + runtime data
- [ ] Faculties panel in Console shows all 5 Faculties with status
- [ ] [ view charter ] expands charter inline
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed to origin/main immediately

---

## Handoff

Commit: cycle5-phase5-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE5_PHASE5_REPORT.md
Stop. Do not begin Phase 5.6 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*Every intelligence named. Every charter readable.*
*Nothing hidden about what INANNA is and what she can become.*

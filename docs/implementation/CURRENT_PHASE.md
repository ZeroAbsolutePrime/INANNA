# CURRENT PHASE: Cycle 3 - Phase 3.4 - The Proposal Dashboard
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 3 - The Commander Room**
**Replaces: Cycle 3 Phase 3 - The Body Report (COMPLETE)**

---

## What This Phase Is

The proposal panel in the current UI shows only PENDING proposals
for the current session. When the session ends, pending proposals
disappear from view. The full history lives in the `history` command
output — text only, no interaction.

Phase 3.4 builds the Proposal Dashboard: the first true Commander
Room panel. It is a dedicated, always-visible section of the UI
that shows the complete governed history of proposals — across all
statuses, filterable, interactive, updating in real time.

This is Law 1 made fully visible: every proposal that was ever made,
its status, what it was for, when it happened — all readable at a
glance without typing a command.

---

## What You Are Building

### Task 1 - Expand the proposals panel in index.html

The current proposals section in the side panel shows only pending
proposals. Expand it into a full Proposal Dashboard with:

**Filter tabs** above the proposal list:
```
[ all ] [ pending ] [ approved ] [ rejected ]
```

The active filter tab is highlighted in the accent color.
Clicking a tab filters the visible proposals.

**Each proposal entry shows:**
- Proposal ID (shortened: first 8 chars)
- Timestamp (formatted: "Apr 19 07:25")
- Status badge: pending (amber), approved (green), rejected (dim)
- What field (the proposal description)
- Action buttons: [approve] [reject] only when status is pending

**Proposal count badge** next to the "PROPOSALS" section title:
```
PROPOSALS  (3 pending)
```
Updates in real time from status broadcasts.

**Load full history button:**
```
[ load full history ]
```
Clicking this sends a WebSocket command to fetch all proposals
from disk (not just the current session's). This populates the
dashboard with the complete cross-session proposal history.

### Task 2 - New WebSocket message type: proposal_history

Add a new command to server.py: "proposal-history"

When received, read ALL proposal files from the active realm's
proposals directory and return them as:
```json
{
  "type": "proposal_history",
  "records": [
    {
      "proposal_id": "proposal-abc12345",
      "timestamp": "2026-04-19T07:25:08",
      "what": "Update the memory store...",
      "status": "approved",
      "resolved_at": "2026-04-19T07:25:12"
    },
    ...
  ],
  "total": 24,
  "approved": 20,
  "rejected": 2,
  "pending": 2
}
```

Records are sorted chronologically (oldest first).
Resolved_at is included when present.

Add "proposal-history" handling to main.py as well, printing the
full history report (same as the existing `history` command output).

### Task 3 - Proposal count in the status payload

Add to the status payload:
```json
{
  "pending_proposals": 2,
  "total_proposals": 24,
  "approved_proposals": 20,
  "rejected_proposals": 2
}
```

These counts come from Proposal.history_report() called at status time.
The counts update on every status broadcast.

### Task 4 - Proposal timestamp formatting

Add a small JavaScript helper to format ISO timestamps into
human-readable form in the UI:

```javascript
function formatTimestamp(iso) {
    try {
        const d = new Date(iso);
        const months = ['Jan','Feb','Mar','Apr','May','Jun',
                        'Jul','Aug','Sep','Oct','Nov','Dec'];
        const h = String(d.getHours()).padStart(2,'0');
        const m = String(d.getMinutes()).padStart(2,'0');
        return `${months[d.getMonth()]} ${d.getDate()} ${h}:${m}`;
    } catch { return iso; }
}
```

Apply to proposal timestamps and memory record timestamps.

### Task 5 - Update identity.py and state.py

Update CURRENT_PHASE:
```python
CURRENT_PHASE = "Cycle 3 - Phase 3.4 - The Proposal Dashboard"
```

Add "proposal-history" to STARTUP_COMMANDS and capabilities.

### Task 6 - Tests

Add to inanna/tests/test_commands.py:
- "proposal-history" in capabilities

Update test_identity.py:
- Update CURRENT_PHASE assertion

Add to inanna/tests/test_proposal.py:
- history_report() returns dict with keys:
  total, approved, rejected, pending, records

---

## Permitted file changes

```
inanna/
  identity.py              <- MODIFY: update CURRENT_PHASE
  main.py                  <- MODIFY: add proposal-history command,
                                      add counts to status context
  core/
    proposal.py            <- no changes
    state.py               <- MODIFY: add proposal-history to capabilities
    (all others)           <- no changes
  ui/
    server.py              <- MODIFY: add proposal-history command,
                                      enrich status with proposal counts
    static/
      index.html           <- MODIFY: proposal dashboard with filter tabs,
                                      status badges, load history button,
                                      pending count badge, timestamp formatting
  tests/
    test_commands.py       <- MODIFY: add proposal-history
    test_identity.py       <- MODIFY: update phase assertion
    test_proposal.py       <- MODIFY: add history_report structure test
    (all others)           <- no changes
```

---

## What You Are NOT Building in This Phase

- No proposal creation from the UI
- No proposal editing
- No bulk approve/reject
- No proposal search or text filtering
- No proposal export
- No change to proposal storage format
- No new Faculty or governance capability

---

## Definition of Done for Phase 3.4

- [ ] Proposal panel shows filter tabs: all/pending/approved/rejected
- [ ] Each proposal shows ID, timestamp, status badge, what, actions
- [ ] [approve] and [reject] buttons only appear on pending proposals
- [ ] Pending count badge next to PROPOSALS section title
- [ ] "load full history" button fetches cross-session proposals
- [ ] proposal-history WebSocket command returns all records
- [ ] Status payload includes total/approved/rejected/pending counts
- [ ] Timestamps formatted as "Apr 19 07:25" in UI
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle3-phase4-complete
2. Write docs/implementation/CYCLE3_PHASE4_REPORT.md
3. Stop. Do not begin Phase 3.5 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*Every proposal ever made, visible at a glance.*
*The governance loop does not hide.*
*It displays itself.*

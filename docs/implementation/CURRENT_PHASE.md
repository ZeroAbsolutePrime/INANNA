# CURRENT PHASE: Cycle 7 - Phase 7.7 - The UX Polish Pass
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Replaces: Cycle 7 Phase 7.6 - Authentication & Login (COMPLETE)**

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — implement all polish items
TESTER:     Codex — verify each item works end-to-end
VERIFIER:   Command Center — confirm after push

BUILDER forbidden from:
  - Adding new capabilities or tools
  - Modifying voice/ directory
  - Changing auth system

---

## What This Phase Is

The system works. Authentication works. Tools work.
But the experience has rough edges observed in real usage sessions.

This phase addresses seven specific problems, in order of priority.

---

## Task 1 — CROWN Tool Result Response (CRITICAL)

**Problem:** After a tool executes, CROWN sometimes still responds
with "I cannot execute system commands" despite the TOOL EXECUTION
COMPLETE instruction.

**Root cause:** The conversation history contains previous
"I cannot execute" responses that train the LLM to repeat the
pattern. The context_summary injection isn't strong enough.

**Fix in ui/server.py, in complete_tool_resolution:**

Step 1: Before engine.respond(), inject a synthetic assistant
acknowledgment to break the repetition pattern:

```python
self.session.add_event(
    "assistant",
    f"[OPERATOR] {result.tool} executed. Processing results."
)
```

Step 2: Strengthen the tool_instruction:

```python
tool_instruction = (
    f"OPERATOR FACULTY COMPLETED: {result.tool} ran.\n"
    f"Results:\n{tool_result_summary}\n"
    f"---\n"
    f"Summarize these results in 1-3 sentences.\n"
    f"RULES (follow exactly):\n"
    f"- DO NOT say you cannot execute commands\n"
    f"- DO NOT say you lack system access\n"
    f"- DO NOT apologize or disclaim\n"
    f"- DO present the actual results\n"
    f"- If error: explain it simply\n"
    f"- If success: confirm it happened"
)
```

---

## Task 2 — Conversational Follow-up Context

**Problem:** After "install notepad++" → search results appear,
then "for windows, option 1" or "yes, install it" loses context
and routes to web_search.

**Fix in ui/server.py:** Add context tracker to InterfaceServer:

```python
self._last_package_context: dict = {}
```

After search_packages executes successfully, store:
```python
if result.tool == "search_packages" and result.success:
    self._last_package_context = {
        "tool": "search_packages",
        "query": result.query,
        "turn": getattr(self.session, "turn_count", 0),
    }
```

In the dispatch_message routing, before normal routing, add:
```python
# Check for follow-up to previous package search
if self._last_package_context:
    last_turn = self._last_package_context.get("turn", -99)
    current_turn = getattr(self.session, "turn_count", 0)
    if current_turn - last_turn <= 3:
        followup = self._detect_package_followup(lowered_text)
        if followup:
            # Route to install with last searched query
            package_action = {
                "tool": "install_package",
                "query": self._last_package_context["query"],
                "params": {"package": self._last_package_context["query"]},
                "requires_proposal": True,
                "reason": "Follow-up to previous package search.",
            }
```

Add helper method:
```python
def _detect_package_followup(self, text: str) -> bool:
    patterns = [
        r"^(yes|ok|okay|do it|install it|go ahead|sure|yep|si|si por favor)$",
        r"^(option|choice|number|pick|numero)\s*\d*",
        r"^(the\s+)?(first|second|third|top|1st|2nd|3rd)\s*(one|option|result)?$",
        r"^(for\s+)?(windows|linux|mac)\s*(version|one)?",
        r"^install\s+it",
        r"^that\s+one",
    ]
    import re
    return any(re.match(p, text.strip(), re.IGNORECASE) for p in patterns)
```

---

## Task 3 — help [topic] Card Treatment

**Problem:** help my-profile, help faculties, help tools etc.
return plain text — no card rendering.

**Fix in core/help_system.py:**

Prefix every topic response with a detectable header:

```python
def build_help_response(role: str, topic: str = "") -> str:
    topic = topic.strip().lower()
    if topic and topic in HELP_TOPICS:
        content = HELP_TOPICS[topic]
        # Add header so buildHelpPanel detects it
        return f"INANNA NYX — {topic.upper()}\n\n{content}"
    # ... rest unchanged
```

Then in index.html, in buildHelpPanel, detect topic responses:
```javascript
const isTopicHelp = text.indexOf('INANNA NYX —') === 0;
const isFullHelp = text.indexOf('Available Commands') >= 0
    || text.indexOf('Command Reference') >= 0
    || (text.indexOf('CONVERSATION') >= 0 && text.indexOf('SESSION') >= 0);
if (!text || (!isTopicHelp && !isFullHelp)) return null;
```

For topic responses, render as a single wide card with the
content formatted as rows, extracting commands from the text.

---

## Task 4 — Proposal Pulse Animation

**Problem:** Pending proposals don't attract enough attention.

**Fix in index.html:**

Add CSS:
```css
@keyframes proposalPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(224,112,48,.5); }
  50% { box-shadow: 0 0 0 5px rgba(224,112,48,0); }
}
#proposal-panel .sp-badge:not(.hidden) {
  animation: proposalPulse 1.5s ease-in-out infinite;
}
```

Auto-expand PROPOSALS when a new proposal arrives:
In the WebSocket message handler, when operator message
contains '[TOOL PROPOSAL]':
```javascript
if (text && text.includes('[TOOL PROPOSAL]')) {
  const panel = document.getElementById('proposal-panel');
  if (panel && !panel.classList.contains('expanded')) {
    toggleSection('proposal');
  }
}
```

---

## Task 5 — login.html Phase Label

**Problem:** login.html shows "__CURRENT_PHASE__" as literal text.

**Fix in ui/server.py:**

Verify _serve_html applies the __CURRENT_PHASE__ substitution
to login.html. If not, add:

```python
def _serve_html(self, file_path: Path) -> None:
    from identity import phase_banner
    content = (
        file_path.read_text(encoding="utf-8")
        .replace("__WS_PORT__", str(WS_PORT))
        .replace("__CURRENT_PHASE__", phase_banner())
    )
    # ... rest of method
```

This should already be working from the base _serve_html method.
If login.html still shows the literal string, check that LOGIN_PATH
is served through _serve_html and not directly.

---

## Task 6 — Side Panel State Memory

**Problem:** Panel sections reset to collapsed on every reconnect.

**Fix in index.html:**

Add to toggleSection():
```javascript
function toggleSection(name) {
  // existing code...
  // Save state after toggling
  saveSectionState();
}

function saveSectionState() {
  const state = {};
  document.querySelectorAll('[id$="-panel"]').forEach(el => {
    if (el.classList.contains('sp-section')) {
      state[el.id] = el.classList.contains('expanded');
    }
  });
  try { sessionStorage.setItem('inanna_sp', JSON.stringify(state)); } catch(e) {}
}

function restoreSectionState() {
  try {
    const state = JSON.parse(sessionStorage.getItem('inanna_sp') || '{}');
    for (const [id, expanded] of Object.entries(state)) {
      const panel = document.getElementById(id);
      if (panel && expanded && !panel.classList.contains('expanded')) {
        panel.classList.add('expanded');
        const bodyId = id.replace('-panel', '-body');
        const body = document.getElementById(bodyId);
        if (body) body.style.display = '';
        const toggle = panel.querySelector('.sp-toggle');
        if (toggle) toggle.textContent = '▾';
      }
    }
  } catch(e) {}
}
// Call on DOMContentLoaded
document.addEventListener('DOMContentLoaded', restoreSectionState);
```

---

## Task 7 — Welcome Message: Dynamic Tool Count

**Problem:** Welcome message says "web_search · ping · resolve_host
· scan_ports" which is outdated (18 tools now registered).

**Fix in ui/server.py, in send_initial_state:**

Replace:
```python
"Tools available: web_search · ping · resolve_host · scan_ports (all require proposal approval)",
```

With:
```python
f"Tools available: {len(self.operator.PERMITTED_TOOLS)} tools registered"
f" · type 'tool-registry' to see all",
```

---

## Permitted file changes

inanna/main.py                      <- MODIFY if needed for follow-up routing
inanna/ui/server.py                 <- MODIFY: Tasks 1, 2, 5, 7
inanna/ui/static/index.html         <- MODIFY: Tasks 3, 4, 6
inanna/core/help_system.py          <- MODIFY: Task 3
inanna/identity.py                  <- MODIFY: CURRENT_PHASE
inanna/tests/test_commands.py       <- MODIFY: update tools line assertion
inanna/tests/test_identity.py       <- MODIFY: update phase assertion

---

## What You Are NOT Building

- No new tools or capabilities
- No voice changes
- No database schema changes
- No new HTML pages
- No auth changes
- No changes to the login page design

---

## Definition of Done

- [ ] CROWN no longer says "I cannot execute" after tool runs
- [ ] Follow-up commands route correctly within 3 turns
- [ ] help [topic] responses render with detectable header
- [ ] Pending proposals auto-expand and pulse
- [ ] login.html shows correct phase
- [ ] Side panel collapse state persists across reconnect
- [ ] Welcome message shows dynamic tool count
- [ ] All 429+ tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle7-phase7-complete

---

## Handoff

Commit: cycle7-phase7-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE7_PHASE7_REPORT.md
Stop. Do not begin Phase 7.8 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-21*
*Polish is not cosmetic.*
*It is the difference between a system that works*
*and a system that feels sovereign.*
*INANNA does not disclaim. She acts.*
*INANNA does not repeat herself. She listens.*
*INANNA does not forget. She remembers.*

# CURRENT PHASE: Cycle 5 - Phase 5.1 - The Console Surface
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-20**
**Cycle: 5 - The Operator Console**
**Master plan: docs/cycle5_master_plan.md**
**Prerequisite: Cycle 4 complete — verify_cycle4.py passed 68 checks**

---

## What This Phase Is

Cycle 4 gave INANNA a civic layer: users, roles, privileges, logs.
Cycle 5 gives Guardians and Operators the surface to manage it all.

Phase 5.1 builds the Console Surface: a second browser panel at
/console, accessible only to Guardian and Operator roles, with four
section buttons and a link from the main interface header.

This is the shell of the Operator Console. Subsequent phases
(5.2-5.8) will fill it with tools, network views, Faculty registry,
and orchestration. Phase 5.1 builds only the surface and navigation.

---

## What You Are Building

### Task 1 - inanna/ui/static/console.html

Create a new HTML file: inanna/ui/static/console.html

The Console shares the same WebSocket server as the main interface.
It connects to ws://localhost:8081 on load.

The Console header:
```
INANNA NYX  OPERATOR CONSOLE    [phase]  [realm]  USER: ZAERA  BODY: OK  • CONNECTED
```

Four section buttons below the header:
```
[ tools ]    [ network ]    [ faculties ]    [ processes ]
```

Each button shows its section panel. Only one panel visible at a time.
Default: tools panel visible on load.

Four section panels (all empty placeholders in Phase 5.1):

TOOLS panel:
  "Tool Registry — Phase 5.2"
  "Registered tools will appear here."

NETWORK panel:
  "Network Eye — Phase 5.3"
  "Network discovery and topology will appear here."

FACULTIES panel:
  "Faculty Registry — Phase 5.5"
  "Registered Faculties will appear here."

PROCESSES panel:
  "Process Monitor — Phase 5.4"
  "Running services and health will appear here."

Each panel has a header with its name and a subtitle explaining
what will be built in its phase.

The Console uses the same color scheme and CSS variables as
the main interface (dark background, amber voice color, etc).
It does not need to import or reference index.html — it is
standalone with its own CSS that matches the design language.

### Task 2 - Role-gated access in the server

Add a route handler in server.py for /console:

When a request comes in for /console:
- If there is an active session and the user has role guardian
  or operator: serve console.html
- Otherwise: redirect to / with a message

Since sessions are WebSocket-based (not HTTP cookie-based),
the HTTP access check is lightweight: just serve console.html
to all HTTP requests for now and let the WebSocket role check
handle enforcement when the page connects.

Actually: serve console.html as a static file like index.html.
Role enforcement happens via the WebSocket on connect:
when console.html connects, send_initial_state() checks
active_user.role and if not guardian/operator, broadcasts:
{"type": "console_access_denied", "text": "Insufficient privileges for Console."}
and the console.html JS redirects to /

### Task 3 - [ console ] button in main interface header

The main interface header currently has (from left to right):
INANNA NYX | [phase] | [realm] | USER: ZAERA | BODY: OK | • CONNECTED

Add a [ console ] button to the right of the phase name:
```
INANNA NYX  [phase]  [ console ]  [realm]  USER: ZAERA  BODY: OK  • CONNECTED
```

CSS for the console button:
```css
.console-btn {
    padding: 2px 10px;
    font-size: 0.74rem;
    letter-spacing: 0.1em;
    border: 1px solid var(--border);
    color: var(--dim);
    cursor: pointer;
    background: transparent;
    text-decoration: none;
    transition: color 0.15s, border-color 0.15s;
}
.console-btn:hover {
    color: var(--voice);
    border-color: var(--voice);
}
```

The button is an anchor tag: href="/console" target="_blank"
It opens the Console in a new tab.

The button is only rendered when active_user.role is guardian
or operator. Hidden for user role and when not logged in.

### Task 4 - HTTP route for /console in server.py

The HTTP server already serves index.html for /.
Add a handler for /console that serves console.html.

```python
elif path == "/console":
    file_path = static_dir / "console.html"
    if file_path.exists():
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content)
    else:
        self.send_response(404)
        self.end_headers()
```

### Task 5 - Console WebSocket connection and role check

In console.html, the WebSocket connect handler:
1. Connects to ws://localhost:8081
2. Listens for status messages
3. Reads active_user.role from the status payload
4. If role is not guardian or operator:
   - Shows "Access denied. Console requires Guardian or Operator role."
   - After 2 seconds, redirects to /

If role is guardian or operator:
- Updates the header with phase, realm, user, body status
- Shows the console as normal

### Task 6 - Update identity.py and state.py

CURRENT_PHASE = "Cycle 5 - Phase 5.1 - The Console Surface"

No new commands needed in Phase 5.1.

### Task 7 - Tests

Update test_identity.py: update CURRENT_PHASE assertion.

No new server tests needed for Phase 5.1 — the console.html
is a static file addition, not a new API.

---

## Permitted file changes

inanna/identity.py                 <- MODIFY: update CURRENT_PHASE
inanna/ui/
  server.py                        <- MODIFY: /console HTTP route,
                                              console_access_denied on connect
  static/
    console.html                   <- NEW: Operator Console surface
    index.html                     <- MODIFY: [ console ] button in header,
                                              role-gated visibility
inanna/tests/
  test_identity.py                 <- MODIFY: update phase assertion

---

## What You Are NOT Building

- No tool execution (Phase 5.2)
- No network scanning (Phase 5.3)
- No Faculty deployment (Phase 5.5)
- No process monitoring (Phase 5.4)
- No new WebSocket commands
- No new Python modules
- The four section panels are placeholder only

---

## Definition of Done for Phase 5.1

- [ ] console.html exists with four section panels
- [ ] /console HTTP route serves console.html
- [ ] Console connects to WebSocket and reads status payload
- [ ] Role check redirects non-authorized users to /
- [ ] [ console ] button appears in main header for guardian/operator
- [ ] [ console ] button hidden for user role
- [ ] CURRENT_PHASE updated to Phase 5.1
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Commit pushed to origin/main immediately

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle5-phase1-complete
2. PUSH TO ORIGIN/MAIN IMMEDIATELY.
3. Write docs/implementation/CYCLE5_PHASE1_REPORT.md
4. Stop. Do not begin Phase 5.2 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-20*
*The console opens.*
*Not with tools yet. Not with network views.*
*Just the surface. Just the door.*
*Everything begins with a door.*

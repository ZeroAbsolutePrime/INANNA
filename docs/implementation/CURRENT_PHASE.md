# CURRENT PHASE: Cycle 7 - Phase 7.6 - Authentication & Login
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-21**
**Replaces: Cycle 7 Phase 7.5 - The Voice Listener (COMPLETE — deferred activation)**

**Note on voice:** Phase 7.5 (Voice Listener) is built and in the repo.
Voice activation is intentionally deferred until the text experience
is fully stable and polished. This is the right priority.

---

## Agent Roles for This Phase

ARCHITECT:  Command Center (Claude) — this document
BUILDER:    Codex — implement auth system and login page
TESTER:     Codex — unit tests + integration tests
VERIFIER:   Command Center — confirm after push

BUILDER forbidden from:
  - Modifying voice/ directory
  - Changing the main chat UI (index.html) beyond removing the overlay
  - Adding dependencies beyond bcrypt/hashlib

---

## What This Phase Is

INANNA NYX needs proper authentication.
Currently any browser can connect with no credentials.
The overlay we built is wrong — it sits on top of the existing UI.

This phase builds:
1. A dedicated login HTML page (login.html) served at /
2. Password authentication with bcrypt hashing
3. ZAERA seeded as the first user with password ETERNALOVE
4. Redirect flow: login.html → authenticated → index.html

The login page must feel like INANNA — dark, Sumerian aesthetic,
minimal and beautiful. Not a modal on top of something else.
A standalone experience that precedes the system.

---

## What You Are Building

### Task 1 - core/auth.py

Create: inanna/core/auth.py

Password authentication module.

```python
from __future__ import annotations
import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _hash_password(password: str, salt: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256."""
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=260000,
    )
    return dk.hex()


def hash_password(password: str) -> str:
    """Hash a password, returning salt:hash."""
    salt = secrets.token_hex(32)
    h = _hash_password(password, salt)
    return f"{salt}:{h}"


def verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored salt:hash."""
    try:
        salt, expected = stored.split(':', 1)
        actual = _hash_password(password, salt)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


@dataclass
class AuthRecord:
    user_id: str
    username: str
    password_hash: str   # salt:hash
    role: str            # guardian | operator | user


class AuthStore:
    """
    Stores hashed passwords separately from the user/token system.
    File: data/{realm}/auth.json
    """

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "auth.json"
        self._records: dict[str, AuthRecord] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text('utf-8'))
                for uid, rec in raw.items():
                    self._records[uid] = AuthRecord(
                        user_id=rec['user_id'],
                        username=rec['username'],
                        password_hash=rec['password_hash'],
                        role=rec['role'],
                    )
            except Exception:
                pass

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            uid: {
                'user_id': r.user_id,
                'username': r.username,
                'password_hash': r.password_hash,
                'role': r.role,
            }
            for uid, r in self._records.items()
        }
        self.path.write_text(json.dumps(data, indent=2), 'utf-8')

    def seed_user(
        self,
        user_id: str,
        username: str,
        password: str,
        role: str,
    ) -> AuthRecord:
        """Add a user if they don't exist yet. Idempotent."""
        if user_id not in self._records:
            rec = AuthRecord(
                user_id=user_id,
                username=username,
                password_hash=hash_password(password),
                role=role,
            )
            self._records[user_id] = rec
            self._save()
            return rec
        return self._records[user_id]

    def create_user(
        self,
        username: str,
        password: str,
        role: str,
    ) -> AuthRecord:
        """Create a new user with a generated ID."""
        import uuid
        user_id = str(uuid.uuid4())[:8]
        return self.seed_user(user_id, username, password, role)

    def authenticate(
        self, username: str, password: str
    ) -> Optional[AuthRecord]:
        """Return AuthRecord if credentials are valid, else None."""
        for rec in self._records.values():
            if rec.username.lower() == username.lower():
                if verify_password(password, rec.password_hash):
                    return rec
        return None

    def get_by_username(self, username: str) -> Optional[AuthRecord]:
        for rec in self._records.values():
            if rec.username.lower() == username.lower():
                return rec
        return None

    def get_by_id(self, user_id: str) -> Optional[AuthRecord]:
        return self._records.get(user_id)

    def list_users(self) -> list[AuthRecord]:
        return list(self._records.values())

    def change_password(
        self, user_id: str, new_password: str
    ) -> bool:
        if user_id not in self._records:
            return False
        self._records[user_id].password_hash = hash_password(new_password)
        self._save()
        return True

    def delete_user(self, user_id: str) -> bool:
        if user_id in self._records:
            del self._records[user_id]
            self._save()
            return True
        return False
```

### Task 2 - Seed ZAERA on startup

In server.py __init__, after creating auth store:

```python
from core.auth import AuthStore

self.auth_store = AuthStore(
    Path(self.config.DATA_DIR) / self.active_realm.name
    if hasattr(self.config, 'DATA_DIR')
    else Path('data') / 'default'
)

# Seed ZAERA as the first guardian
self.auth_store.seed_user(
    user_id='zaera',
    username='ZAERA',
    password='ETERNALOVE',
    role='guardian',
)
```

### Task 3 - Login HTTP endpoint in server.py

Add POST /login endpoint to the HTTP server:

```python
async def handle_login(self, request):
    """Handle POST /login with username + password."""
    try:
        body = await request.read()
        data = json.loads(body)
        username = str(data.get('username', '')).strip()
        password = str(data.get('password', ''))
    except Exception:
        return web.Response(
            status=400,
            content_type='application/json',
            text=json.dumps({'error': 'Invalid request'}),
        )

    record = self.auth_store.authenticate(username, password)
    if not record:
        return web.Response(
            status=401,
            content_type='application/json',
            text=json.dumps({'error': 'Invalid credentials'}),
        )

    # Issue a session token
    token_str = secrets.token_hex(32)
    # Store token in session (simple in-memory for now)
    self._auth_sessions[token_str] = {
        'user_id': record.user_id,
        'username': record.username,
        'role': record.role,
    }
    return web.Response(
        status=200,
        content_type='application/json',
        text=json.dumps({
            'token': token_str,
            'username': record.username,
            'role': record.role,
        }),
    )
```

Also add GET /login to serve login.html:

```python
async def handle_login_page(self, request):
    login_path = Path(__file__).parent / 'static' / 'login.html'
    return web.FileResponse(login_path)
```

Register these routes in the HTTP app setup:
```python
app.router.add_get('/login', self.handle_login_page)
app.router.add_post('/login', self.handle_login)
app.router.add_get('/', self.handle_login_redirect)
```

```python
async def handle_login_redirect(self, request):
    """Redirect / to /login if not authenticated, else to /app."""
    raise web.HTTPFound('/login')
```

Also change the main app route:
```python
app.router.add_get('/app', self.handle_index)  # was '/'
app.router.add_get('/index.html', self.handle_index)
```

### Task 4 - ui/static/login.html

Create a beautiful standalone login page.

Design principles:
- Full black background, same CSS variables as index.html
- Large INANNA NYX title with Sumerian glyph
- Clean minimal form: username field, password field, [ ENTER ] button
- No overlay — this IS the page, full screen
- On successful POST /login: store token in sessionStorage, redirect to /app
- On failure: shake animation on the form, error message

Key elements:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>INANNA NYX</title>
  <!-- same fonts and CSS variables as index.html -->
  <style>
    /* full-page login — same dark aesthetic */
    /* centered vertically and horizontally */
    /* no scrollbars */
  </style>
</head>
<body>
  <div class="login-container">
    <div class="login-glyph">𒀭</div>
    <div class="login-title">INANNA NYX</div>
    <div class="login-subtitle">SOVEREIGN INTELLIGENCE</div>
    <div class="login-tagline">THE LIVING INTELLIGENCE · GATES OF URUK · ABZU CODEX</div>

    <form class="login-form" id="login-form">
      <div class="login-field">
        <label class="login-label">IDENTITY</label>
        <input type="text" id="username" class="login-input"
               placeholder="your name" autocomplete="off" />
      </div>
      <div class="login-field">
        <label class="login-label">ACCESS CODE</label>
        <input type="password" id="password" class="login-input"
               placeholder="••••••••••" autocomplete="off" />
      </div>
      <button type="submit" class="login-btn">[ ENTER ]</button>
      <div class="login-error" id="login-error"></div>
    </form>

    <div class="login-phase" id="login-phase"></div>
  </div>

  <script>
    // POST to /login, store token, redirect to /app
    document.getElementById('login-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = document.getElementById('username').value.trim();
      const password = document.getElementById('password').value;
      const errEl = document.getElementById('login-error');
      errEl.textContent = '';

      try {
        const resp = await fetch('/login', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({username, password}),
        });
        if (resp.ok) {
          const data = await resp.json();
          sessionStorage.setItem('inanna_token', data.token);
          sessionStorage.setItem('inanna_user', data.username);
          sessionStorage.setItem('inanna_role', data.role);
          window.location.href = '/app';
        } else {
          errEl.textContent = 'invalid credentials';
          document.getElementById('login-form').classList.add('shake');
          setTimeout(() => document.getElementById('login-form')
            .classList.remove('shake'), 500);
        }
      } catch (err) {
        errEl.textContent = 'connection error';
      }
    });
  </script>
</body>
</html>
```

### Task 5 - Remove login overlay from index.html

Remove the `<div id="login-overlay">` block and all associated
JS that was added in the previous session. The login is now a
separate page — the overlay is no longer needed.

### Task 6 - Update identity.py

CURRENT_PHASE = "Cycle 7 - Phase 7.6 - Authentication & Login"

### Task 7 - Tests

Create inanna/tests/test_auth.py:
  - AuthStore instantiates
  - hash_password returns salt:hash format
  - verify_password returns True for correct password
  - verify_password returns False for wrong password
  - seed_user creates a user
  - seed_user is idempotent (second call doesn't overwrite)
  - authenticate returns AuthRecord for correct credentials
  - authenticate returns None for wrong password
  - authenticate returns None for unknown username
  - authenticate is case-insensitive for username
  - create_user creates a new user with generated ID
  - list_users returns all users
  - change_password changes the hash
  - change_password verifies with new password
  - ZAERA seed: authenticate('ZAERA', 'ETERNALOVE') returns record
  - ZAERA seed: authenticate('ZAERA', 'wrong') returns None
  - password stored as hash, never plaintext

Update test_identity.py: update CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/core/auth.py                   <- NEW
inanna/ui/server.py                   <- MODIFY: add auth store, login endpoints
inanna/ui/static/login.html           <- NEW
inanna/ui/static/index.html           <- MODIFY: remove login overlay only
inanna/identity.py                    <- MODIFY: update CURRENT_PHASE
inanna/tests/test_auth.py             <- NEW
inanna/tests/test_identity.py         <- MODIFY

---

## What You Are NOT Building

- No session expiry / JWT (simple in-memory tokens for now)
- No password reset flow (future phase)
- No multi-factor authentication (future phase)
- No user registration from the login page (guardian creates users)
- No changes to the main chat UI beyond removing the overlay
- No voice changes

---

## Login Page Design Notes

The login page must match the INANNA aesthetic exactly:
- Background: #0a0704 (same as index.html)
- Font: same Google Fonts (Cinzel Decorative for title, etc.)
- Gold palette: same CSS variables
- The 𒀭 glyph prominently above the title
- Tagline: "THE LIVING INTELLIGENCE · GATES OF URUK · ABZU CODEX"
- Form: minimal, centered, no borders except bottom underlines
- Error state: gentle shake animation, red text
- Success state: brief "entering..." message, then redirect

Do NOT copy the current overlay design (white boxes, dark modal).
Design it as a full-page experience, not a dialog.

---

## Definition of Done

- [ ] core/auth.py with AuthStore and password hashing
- [ ] ZAERA seeded with ETERNALOVE on server startup
- [ ] POST /login endpoint authenticates and returns token
- [ ] GET / redirects to /login
- [ ] GET /app serves the main chat interface
- [ ] login.html is a beautiful standalone page
- [ ] Login overlay removed from index.html
- [ ] All tests pass: py -3 -m unittest discover -s tests
- [ ] Pushed as cycle7-phase6-complete

---

## Handoff

Commit: cycle7-phase6-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE7_PHASE6_REPORT.md
Stop. Do not begin Phase 7.7 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-21*
*The gate has a key now.*
*ZAERA holds it.*
*ETERNALOVE opens it.*
*Others enter only when ZAERA allows.*

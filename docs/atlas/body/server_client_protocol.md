# BODY · SERVER-CLIENT PROTOCOL
## The Nervous Pathway — Communication Between Brain and Hands

**Ring: Body / OS / Runtime**
**Grade: A- (works correctly, single-machine only tested)**
**Version: 1.0 · Date: 2026-04-24**

---

## Identity

The server-client protocol defines how INANNA NYX's brain (server)
communicates with its hands (client machines).

**Current reality:** Server and client run on the same Windows machine.
**Target reality:** Server on DGX Spark. Client on NixOS laptop.
Same protocol — different machines.

---

## Protocol

```
HTTP  :8080  — login page, static UI, REST endpoints
WS    :8081  — real-time session, bidirectional messaging
```

**Message types (WebSocket):**
- `input` — operator sends text
- `command` — operator sends command
- `assistant` — CROWN responds
- `thinking` — spinner state
- `system` — system notification
- `proposal` — governance proposal
- `state` — session state update

**Authentication flow:**
1. Browser opens `http://localhost:8080`
2. Login page: INANNA NAMMU / ETERNALOVE
3. POST `/login` → session token returned
4. WebSocket connects with token
5. Session begins, memory loaded

---

## Correspondences

| Component | Location |
|---|---|
| HTTP server | `ui/server.py` → HTTP handler |
| WebSocket server | `ui/server.py` → `InterfaceServer` |
| Login endpoint | `ui/server.py` → `/login` |
| Static files | `ui/static/` |
| Entry point | `ui_main.py` |

---

## Multi-Machine Deployment

When server and client are separated (DGX + NixOS laptop):

```python
# Client NixOS configuration
environment.sessionVariables = {
    INANNA_SERVER_URL = "http://192.168.1.100:8080";
    INANNA_WS_URL     = "ws://192.168.1.100:8081";
};
```

The protocol does not change. Only the server IP changes.
Everything else — login, sessions, tools, proposals — works identically.

---

## Evaluation

**Grade: A-**

The protocol is simple, correct, and network-ready.
The main limitation is that it has only been tested on one machine.

Priority before DGX deployment: test with server and client
on separate machines on a local network to verify
the WebSocket connection works across network boundaries.

---

*Body Card version 1.0 · 2026-04-24*

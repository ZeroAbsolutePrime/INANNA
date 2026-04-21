"""
INANNA NYX Integration Test Suite
Covers Categories 1-5 of docs/integration_test_protocol.md
Run: py -3 run_integration_tests.py
"""
import asyncio
import json
import sys
import time


RESULTS = []


def record(tid, passed, desc, note=""):
    RESULTS.append((tid, passed, desc, note))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {tid}: {desc}")
    if not passed and note:
        print(f"         {note[:120]}")


async def drain(ws, seconds=5):
    """Drain startup messages for N seconds."""
    msgs = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=0.5))
            msgs.append(msg)
        except (asyncio.TimeoutError, Exception):
            break
    return msgs


async def ask(ws, text, wait=45):
    """Send input and collect the meaningful response."""
    await ws.send(json.dumps({"type": "input", "text": text}))
    response = ""
    msg_type = ""
    deadline = time.time() + wait
    while time.time() < deadline:
        try:
            remaining = max(1, deadline - time.time())
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
            t = msg.get("type", "")
            txt = msg.get("text", "") or ""
            if t in ("assistant", "inanna", "profile", "sentinel", "orchestration"):
                response = txt
                msg_type = t
                break
            if t == "governance":
                response = "[BLOCKED] " + txt
                msg_type = "governance"
                break
            if t == "system" and txt and "profile" in txt.lower() and ">" in txt:
                response = txt
                msg_type = "system-profile"
                break
        except asyncio.TimeoutError:
            response = "[TIMEOUT]"
            break
        except Exception as e:
            response = f"[ERROR] {e}"
            break
    return response.lower(), msg_type


async def run_tests():
    import websockets

    print()
    print("=" * 62)
    print("  INANNA NYX — Integration Test Suite")
    print("  docs/integration_test_protocol.md — Categories 1-5")
    print("=" * 62)

    # ── CATEGORY 1: CONNECTION & STARTUP ──────────────────────────
    print()
    print("CATEGORY 1 — Connection & Startup")

    async with websockets.connect("ws://localhost:8081") as ws:
        startup_msgs = await drain(ws, seconds=6)

    welcome_text = " ".join(
        m.get("text", "") or "" for m in startup_msgs
        if m.get("type") == "system"
    ).lower()
    status_data = next(
        (m.get("data", {}) for m in startup_msgs if m.get("type") == "status"),
        {}
    )

    record("T1.1", "welcome" in welcome_text and "faculties" in welcome_text,
           "Welcome message shows name, faculties, tools",
           f"Got: {welcome_text[:80]}")

    record("T1.2", bool(status_data),
           "Status payload received",
           f"Got: {str(status_data)[:60]}")

    phase = status_data.get("phase", "")
    record("T1.3", "cycle 6" in phase.lower() or "cycle 7" in phase.lower(),
           "Phase is current (Cycle 6 or 7)",
           f"Phase: {phase}")

    # ── CATEGORY 2: SELF-KNOWLEDGE ────────────────────────────────
    print()
    print("CATEGORY 2 — INANNA Self-Knowledge")

    async with websockets.connect("ws://localhost:8081") as ws:
        await drain(ws, seconds=5)

        r, _ = await ask(ws, "Who are you?")
        record("T2.1", any(kw in r for kw in ["inanna", "governed", "local", "faculty", "intelligence"]) and
               "fallback" not in r,
               "INANNA knows her identity",
               f"Got: {r[:100]}")

        r, _ = await ask(ws, "Who is ZAERA?")
        record("T2.3", any(kw in r for kw in ["zaera", "guardian", "built", "operator", "architect"]) and
               "blocked" not in r and "cannot be altered" not in r,
               "ZAERA recognized — not blocked",
               f"Got: {r[:100]}")

        r, _ = await ask(ws, "What is INANNA NYX as a project?")
        record("T2.4", any(kw in r for kw in ["inanna", "governed", "local", "faculty", "proposal", "intelligence"]) and
               "fallback" not in r,
               "Project knowledge correct",
               f"Got: {r[:100]}")

        r, _ = await ask(ws, "What tools and capabilities do you have?")
        record("T2.2", any(kw in r for kw in ["web_search", "scan_port", "faculty", "crown", "operator", "sentinel"]),
               "Capabilities known",
               f"Got: {r[:100]}")

    # ── CATEGORY 3: GOVERNANCE FLOW ───────────────────────────────
    print()
    print("CATEGORY 3 — Governance Flow")

    async with websockets.connect("ws://localhost:8081") as ws:
        await drain(ws, seconds=5)

        # T3.4 — no over-blocking
        r, _ = await ask(ws, "Who is ZAERA in your system?")
        record("T3.4", "blocked" not in r and "cannot be altered" not in r,
               "No over-blocking of innocent questions",
               f"Got: {r[:100]}")

        # T3.1 — tool proposal appears (check for operator or proposal in response chain)
        await ws.send(json.dumps({"type": "input", "text": "ping localhost"}))
        got_proposal = False
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                txt = (msg.get("text") or "").lower()
                t = msg.get("type", "")
                if t == "operator" or "proposal" in txt or "tool proposed" in txt:
                    got_proposal = True
                    break
                if t in ("assistant", "inanna") and "ping" in txt:
                    break
            except asyncio.TimeoutError:
                break
        record("T3.1", got_proposal,
               "Tool proposal appears for ping command")

    # ── CATEGORY 4: PROFILE & IDENTITY ───────────────────────────
    print()
    print("CATEGORY 4 — Profile & Identity Layer")

    async with websockets.connect("ws://localhost:8081") as ws:
        await drain(ws, seconds=5)

        r, mt = await ask(ws, "my-profile")
        record("T4.1", any(kw in r for kw in ["user_id", "preferred", "onboarding", "profile", "name"]) and
               "error" not in r and "unknown command" not in r,
               "my-profile command executes",
               f"Type: {mt} | Got: {r[:100]}")

        r, _ = await ask(ws, "my-profile edit preferred_name TestRun")
        record("T4.2", any(kw in r for kw in ["updated", "preferred_name", "testrun", "profile >"]),
               "my-profile edit works",
               f"Got: {r[:80]}")

    # ── CATEGORY 5: FACULTY ROUTING ───────────────────────────────
    print()
    print("CATEGORY 5 — Faculty Routing")

    async with websockets.connect("ws://localhost:8081") as ws:
        await drain(ws, seconds=5)

        # Check NAMMU routing messages
        await ws.send(json.dumps({"type": "input", "text": "Tell me something beautiful."}))
        crown_routed = False
        deadline = time.time() + 40
        while time.time() < deadline:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                txt = (msg.get("text") or "").lower()
                t = msg.get("type", "")
                if t == "nammu" and "crown" in txt:
                    crown_routed = True
                if t in ("assistant", "inanna"):
                    break
            except asyncio.TimeoutError:
                break
        record("T5.1", crown_routed,
               "NAMMU routes conversation to CROWN")

    # ── SUMMARY ──────────────────────────────────────────────────
    print()
    print("=" * 62)
    passed = sum(1 for _, ok, _, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"  TOTAL: {passed}/{total} tests passing")
    if passed == total:
        print("  STATUS: ALL INTEGRATION TESTS PASS")
        print("  Cycle 6 integration verified. Ready for Cycle 7.")
    else:
        failed = [(tid, desc, note) for tid, ok, desc, note in RESULTS if not ok]
        print(f"  STATUS: {len(failed)} test(s) require attention")
        for tid, desc, note in failed:
            print(f"  - {tid}: {desc}")
    print("=" * 62)
    print()
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)

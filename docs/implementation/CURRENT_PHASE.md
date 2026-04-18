# CURRENT PHASE: Phase 5 — The Grounded Memory
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-18**
**Replaces: Phase 4 — The Reflective Loop (COMPLETE)**

---

## What Phase 5 Is

Phase 4 revealed a real gap. When INANNA was given approved memory and
asked to reflect, the underlying model answered as if the memory did not
exist. It said "I have no knowledge of prior conversations" while holding
two approved memory lines in its context.

This is the model alignment problem: the model's training is stronger
than a system prompt alone. It defaults to its trained behavior unless
the memory is injected in a way it cannot ignore.

Phase 5 solves this by changing how memory is passed to the model.
Instead of placing memory only in the system prompt, we inject it as
a structured exchange at the start of every conversation — a visible
assistant turn that grounds the model in what was approved before the
user speaks.

This is called memory grounding. It does not require a new model,
fine-tuning, or external tools. It uses the conversation structure
itself as the enforcement mechanism.

---

## The Problem In Detail

Currently, the Engine builds messages like this:

```
[system]    You are INANNA... (identity prompt)
            Prior context: line 1, line 2...
[user]      What do you value most?
```

The model receives memory as part of a long system prompt it may
deprioritize. It does not treat memory as something it said — it
treats it as background noise in a preamble.

The fix is to restructure messages like this:

```
[system]    You are INANNA... (identity prompt, WITHOUT memory lines)
[assistant] From my approved memory of our prior conversations:
            1. user: What do you value most?
            2. assistant: As INANNA I value...
            This is what I know. I will ground my responses in this.
[user]      {actual user message}
```

Now the model sees the memory as something it already said. It is
far less likely to contradict itself or ignore it. This is the
grounding injection pattern.

---

## What You Are Building

### Task 1 — Grounding injection in the Engine

Modify `Engine._build_messages()` in `core/session.py`.

Current behavior: memory lines are appended to the system prompt.
New behavior: memory lines are removed from the system prompt and
injected as a synthetic assistant turn before the first user message.

The new message structure must be:

```python
messages = [
    {"role": "system", "content": build_system_prompt()},
]

if context_summary:
    grounding_lines = "\n".join(
        f"  {i+1}. {line}" for i, line in enumerate(context_summary)
    )
    messages.append({
        "role": "assistant",
        "content": (
            "From my approved memory of our prior conversations:\n"
            + grounding_lines
            + "\n\nI will ground my responses in this approved memory."
        ),
    })

for event in conversation:
    messages.append({"role": event["role"], "content": event["content"]})
```

The same grounding injection must be applied in `Engine.reflect()`.
When reflect() is called with context_summary, the memory must appear
as a prior assistant turn before the reflection request, not as part
of the system prompt.

### Task 2 — Update build_system_prompt() in identity.py

The current system prompt includes a section that says:
"Prior context:" followed by memory lines.

That section must be removed from the prompt template entirely, because
memory is now injected structurally, not via the system prompt.

The identity prompt must remain unchanged except for the removal of
any dynamic memory injection that currently lives there.

If memory injection does not currently live in `build_system_prompt()`
but only in `_build_messages()`, then `identity.py` needs no changes.
Codex must check and act accordingly.

### Task 3 — Grounding verification test

Add a test in `inanna/tests/test_session.py` (or a new file
`inanna/tests/test_grounding.py`) that verifies the message structure.

The test must confirm:
- When context_summary is empty, no assistant grounding turn is injected
- When context_summary has lines, the second message has role "assistant"
- The assistant grounding turn contains the word "approved memory"
- The user message appears AFTER the grounding turn, not before it
- The system message is always first

This test must pass without a live model — it tests message construction
only, not model output.

### Task 4 — Reflect honesty marker

When `reflect()` falls back to the non-model path (fallback mode),
prefix the output with:

```
inanna> [memory fallback] From my approved memory:
  1. ...
  2. ...
```

When `reflect()` uses the live model path, prefix with:

```
inanna> [live reflection]
```

This makes the source of the reflection readable and honest, which
directly serves Foundational Law 4: Readable System Truth.

The prefix is added by `main.py` when printing the reflect result,
not inside `Engine.reflect()` itself. `Engine.reflect()` returns
a tuple: `(mode: str, text: str)` where mode is either
`"live"` or `"fallback"`.

Update `handle_command()` in `main.py` to unpack the tuple and
format the output accordingly.

---

## Permitted file changes

```
inanna/
  identity.py        <- MODIFY only if memory injection lives there
  config.py          <- no changes
  main.py            <- MODIFY: unpack reflect tuple, format prefix
  core/
    session.py       <- MODIFY: grounding injection in _build_messages()
                                and reflect(), reflect() returns tuple
    memory.py        <- no changes
    proposal.py      <- no changes
    state.py         <- no changes
  tests/
    __init__.py      <- no changes
    test_session.py  <- MODIFY or add test_grounding.py (Codex decides)
    test_memory.py   <- no changes
    test_proposal.py <- no changes
    test_state.py    <- no changes
    test_identity.py <- no changes
    test_commands.py <- MODIFY: update reflect test for new tuple return
```

---

## What You Are NOT Building in This Phase

- No new commands
- No new data storage formats
- No change to proposal or memory logic
- No change to the data directory structure
- No web interface, no API server
- No streaming responses
- No multi-user support
- Do not change the identity prompt text in PROMPT
- Do not add new Faculties or orchestration layers
- Do not change the approve/reject/status/diagnostics commands
- The grounding injection must use conversation structure only —
  no vector databases, no embeddings, no external retrieval

---

## Definition of Done for Phase 5

- [ ] `_build_messages()` injects memory as an assistant turn,
      not in the system prompt
- [ ] `reflect()` returns a tuple `(mode, text)` not a bare string
- [ ] `reflect()` uses grounding injection when context exists
- [ ] `main.py` prints `inanna> [live reflection]` or
      `inanna> [memory fallback]` prefix correctly
- [ ] Grounding verification test passes without a live model
- [ ] All existing tests still pass
- [ ] `py -3 -m unittest discover -s tests` passes from `inanna/`
- [ ] No code exists outside the permitted file locations above

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit all work with message: `phase-5-complete`
2. Write `docs/implementation/PHASE_5_REPORT.md` containing:
   - What was built
   - Any decisions made during implementation
   - Any boundaries that felt unclear
   - Any proposals for Phase 6

Then stop. Do not begin Phase 6 without a new CURRENT_PHASE.md
from the Command Center.

---

*Written by: Claude (Command Center)*
*Phase 4 reviewed and approved: 2026-04-18*
*Architecture horizon integrated: 2026-04-18*

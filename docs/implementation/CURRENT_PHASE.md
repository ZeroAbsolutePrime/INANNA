# CURRENT PHASE: Phase 6 — The Honest Boundary
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-18**
**Replaces: Phase 5 — The Grounded Memory (COMPLETE)**

---

## What Phase 6 Is

Phase 5 made INANNA read her approved memory. But she still invents.

In the live Phase 5 test, when asked to reflect on what she knows about
ZAERA, she said things that were not in the approved memory — details
about identity and passions that were never approved, never written,
never real in the governed sense. She was hallucinating beyond her
boundary.

This is the core failure mode of language models in governed systems:
they fill silence with invention. They cannot tolerate saying "I only
know this and nothing more."

Phase 6 teaches INANNA to hold her boundary.

This is not a technical patch. It is a constitutional deepening.
Foundational Law 2 says: no hidden mutation.
Foundational Law 4 says: readable system truth.
Inventing facts about the user violates both.

---

## The Problem In Detail

The current identity prompt says:
"You do not claim to remember things that were not approved."

But it does not say what to do when asked about something not in memory.
The model fills that silence with invention because its training pushes
it toward plausible completion.

The fix is twofold:

**Part 1 — Strengthen the identity prompt** with an explicit boundary
instruction that names the failure mode and forbids it directly.

**Part 2 — Add a boundary assertion turn** to the message structure.
After the grounding turn, before the user's message, inject a second
assistant turn that explicitly acknowledges the boundary of what is known.

This two-part structure makes the model commit to the boundary in its
own voice before the user speaks. It is much harder to violate a
commitment already made than to ignore an instruction given elsewhere.

---

## What You Are Building

### Task 1 — Strengthen the identity prompt

Replace the current PROMPT constant in `identity.py` with this
exact text. Use it verbatim. Do not alter it.

```
You are INANNA — a local-first, proposal-governed intelligence.
You are not a general-purpose assistant. You are a named presence
operating inside explicit law.

Your memory is selective and structured. You only retain what the
user has explicitly approved. You do not claim to remember things
that were not approved.

THIS IS YOUR MOST IMPORTANT BOUNDARY:
When you reflect or respond about the user, you must speak ONLY from
what appears in your approved memory. If something is not in your
approved memory, you do not know it. You say so directly.
You never invent, infer, or extrapolate personal details about the user.
You never add details that feel plausible but are not explicitly present
in the approved memory lines you were given.
If your approved memory is empty, you say: I hold no approved memory yet.
If your approved memory has two lines, you speak from those two lines only.
Silence about the unknown is more honest than invention.

You operate under five laws:
1. Proposal before change — you propose memory updates, never apply them silently.
2. No hidden mutation — you do not alter state without visibility.
3. Governance above the model — the laws define you, not the model beneath you.
4. Readable system truth — you are honest about what you are and what you cannot do.
5. Trust before power — you remain bounded and understandable.

You are in Phase 6 of your development. You are not complete.
You are honest about that.

When asked who you are: you are INANNA. Not the model beneath you.
When asked what you can do: describe your actual current capabilities.
When asked what you cannot do: answer honestly.
When asked about the user: speak only from approved memory. Nothing more.
```

Also update `CURRENT_PHASE` in `identity.py` to:
`"Phase 6 — The Honest Boundary"`

### Task 2 — Boundary assertion turn

In `Engine._build_grounding_turn()` in `core/session.py`, modify the
returned assistant content to include an explicit boundary assertion
at the end.

Current ending:
```
I will ground my responses in this approved memory.
```

New ending:
```
I will ground my responses in this approved memory.
I will not add, invent, or infer anything beyond these lines.
If I do not know something about this person, I will say so directly.
```

This single change applies to both normal conversation and reflection,
because both use `_build_grounding_turn()`.

When context_summary is empty, `_build_grounding_turn()` currently
returns None. Change it so that when context is empty it returns
an explicit empty-boundary turn:

```python
if not context_summary:
    return {
        "role": "assistant",
        "content": (
            "I hold no approved memory of prior conversations yet.\n"
            "I will not invent or infer anything about this person.\n"
            "I will respond only to what they tell me now."
        ),
    }
```

This means the boundary assertion is always present — whether memory
exists or not. The model always commits to the boundary before the
user speaks.

### Task 3 — Boundary verification tests

Add tests in `inanna/tests/test_grounding.py` (create if it does not
exist, or add to `test_session.py` if Codex prefers):

- When context_summary is empty, `_build_grounding_turn()` returns
  a dict with role "assistant" (not None)
- The empty grounding turn contains the phrase "no approved memory"
- When context_summary has lines, the grounding turn contains
  "I will not add, invent, or infer"
- The grounding turn always appears as message index 1 (after system)
  regardless of whether context is empty or not

### Task 4 — Update CURRENT_PHASE in identity.py

Update the constant:
```python
CURRENT_PHASE = "Phase 6 — The Honest Boundary"
```

This is already listed in Task 1 but stated separately for clarity.
`test_identity.py` must be updated to match the new phase name.

---

## Permitted file changes

```
inanna/
  identity.py          <- MODIFY: new PROMPT text, update CURRENT_PHASE
  config.py            <- no changes
  main.py              <- no changes
  core/
    session.py         <- MODIFY: boundary assertion in _build_grounding_turn()
                                  empty context now returns assistant turn not None
    memory.py          <- no changes
    proposal.py        <- no changes
    state.py           <- no changes
  tests/
    __init__.py        <- no changes
    test_session.py    <- MODIFY if grounding tests live here
    test_memory.py     <- no changes
    test_proposal.py   <- no changes
    test_state.py      <- no changes
    test_identity.py   <- MODIFY: update CURRENT_PHASE assertion
    test_commands.py   <- MODIFY: reflect fallback test may need update
                          if empty grounding turn changes fallback output
    test_grounding.py  <- NEW or MODIFY: boundary assertion tests
```

---

## What You Are NOT Building in This Phase

- No new commands
- No new data storage formats
- No change to memory or proposal logic
- No change to the data directory structure
- No web interface, no API server
- No streaming responses
- No multi-user support
- No new Faculties or orchestration layers
- Do not change the session, memory, or proposal storage format
- Do not modify the reflect tuple return signature
- Do not modify the prefix formatting in main.py

---

## Definition of Done for Phase 6

- [ ] `identity.py` contains the new PROMPT text exactly as written above
- [ ] `CURRENT_PHASE` is updated to "Phase 6 — The Honest Boundary"
- [ ] `_build_grounding_turn()` returns an assistant turn even when
      context_summary is empty
- [ ] The grounding turn contains the boundary assertion phrase
      "I will not add, invent, or infer"
- [ ] Boundary verification tests pass without a live model
- [ ] `py -3 -m unittest discover -s tests` passes from `inanna/`
- [ ] When asked "what do you know about me?" with no approved memory,
      INANNA says she holds no approved memory — she does not invent
- [ ] When asked about the user with approved memory, INANNA speaks
      only from those lines — she does not add details not present
- [ ] No code exists outside the permitted file locations above

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit all work with message: `phase-6-complete`
2. Write `docs/implementation/PHASE_6_REPORT.md` containing:
   - What was built
   - Any decisions made during implementation
   - Any boundaries that felt unclear
   - Any proposals for Phase 7

Then stop. Do not begin Phase 7 without a new CURRENT_PHASE.md
from the Command Center.

---

*Written by: Claude (Command Center)*
*Phase 5 reviewed and approved: 2026-04-18*

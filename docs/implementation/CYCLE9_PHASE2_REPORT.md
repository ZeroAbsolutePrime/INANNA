# Cycle 9 Phase 9.2 Report

## Summary

Phase 9.2 implements NAMMU's per-operator profile layer:

- `inanna/core/nammu_profile.py` adds `OperatorProfile`, `RoutingCorrection`,
  load/save helpers, profile seeding from `UserProfile`, and shorthand extraction.
- `inanna/core/nammu_intent.py` now accepts `operator_profile` and prepends an
  `[OPERATOR CONTEXT]` block without replacing `NAMMU_UNIVERSAL_PROMPT`.
- `inanna/main.py` and `inanna/ui/server.py` now load the NAMMU profile at
  session start, pass it into `nammu_first_routing()`, update it after tool
  execution, and expose `nammu-learn`, `nammu-correct`, and `nammu-profile`.
- `inanna/core/help_system.py` now documents the NAMMU profile teaching flow.

## Confirmation: profile file created on startup

Confirmed by instantiating `InterfaceServer()` after deployment. Startup created:

`inanna/data/realms/default/nammu/operator_profiles/user_6396c88f.json`

Actual profile JSON captured immediately after startup:

```json
{
  "user_id": "user_6396c88f",
  "display_name": "INANNA NAMMU",
  "last_updated": "2026-04-22T19:16:18.913844+00:00",
  "language_patterns": {
    "en": []
  },
  "primary_language": "en",
  "known_shorthands": {},
  "domain_weights": {
    "operator": 0.3
  },
  "urgency_markers": [],
  "routing_corrections": [],
  "recurring_topics": [
    "operator"
  ],
  "communication_style": "Queer",
  "preferred_length": "short"
}
```

## Test: `nammu-learn` command

Captured by invoking `InterfaceServer.process_command()` offline with:

`nammu-learn mtx Matxalen`

Observed broadcast payload:

```python
{'type': 'system', 'text': "nammu > learned: 'mtx' = 'Matxalen'"}
```

## Test: `to_nammu_context()` with seeded profile

Rendered from a seeded `OperatorProfile` with:

- display name: `INANNA NAMMU`
- language patterns: `en -> technical`, `es -> relaxed`
- shorthand: `mtx = Matxalen`
- domain weights: `email`, `calendar`
- one correction example for `"mtx replied?"`

Observed context block:

```text
[OPERATOR CONTEXT]
Operator: INANNA NAMMU
Languages: en (technical) | es (relaxed)
Shorthands: "mtx"=Matxalen
Style: Queer; prefers short, direct responses
Most used: email, calendar
Recent corrections:
  "mtx replied?" -> {"intent":"email_search","params":{"query": "Matxalen"}}
[END CONTEXT]
```

## Verification

Passed:

- `py -3 -m py_compile inanna\core\nammu_profile.py inanna\core\nammu_intent.py inanna\core\help_system.py inanna\main.py inanna\ui\server.py inanna\identity.py inanna\tests\test_nammu_profile.py inanna\tests\test_identity.py inanna\tests\test_nammu_intent.py`
- `py -3 -m unittest tests.test_nammu_profile tests.test_nammu_intent tests.test_identity`
- `py -3 -m unittest discover -s tests`

Final suite result:

- `673` tests passed
- `test_nammu_profile.py` contains exactly `25` offline tests

# Cycle 9 Phase 9.5 - The Feedback Loop

## Summary

Implemented the active NAMMU feedback loop for both the WebSocket server and CLI command path.

Completed work:
- Enhanced `nammu-correct` to accept either a plain query string or JSON params.
- Added session-scoped correction counting and pattern surfacing every 5th correction.
- Added `nammu-stats` for routing statistics.
- Added informational misroute detection signals in English and Spanish.
- Added `analyse_routing_log()` in `core/nammu_profile.py`.
- Updated help and phase identity.

## Evidence

### `nammu-correct` with query parameter

Input:
```text
nammu-correct email_search Matxalen
```

Parsed params:
```python
{"query": "Matxalen"}
```

### Sample `analyse_routing_log()` output

```python
{
  "total_routings": 3,
  "top_domains": {"email": 2, "calendar": 1},
  "correction_count": 1,
  "known_shorthands": 0
}
```

### Misroute detection

Spanish signal:
```text
no era eso -> True
```

Normal message:
```text
anything from Matxalen? -> False
```

## Verification

Commands run:

```text
py -3 -m py_compile inanna\core\nammu_profile.py inanna\main.py inanna\ui\server.py inanna\core\help_system.py inanna\identity.py inanna\tests\test_feedback_loop.py inanna\tests\test_identity.py inanna\tests\test_intent_engine.py
py -3 -m unittest tests.test_feedback_loop tests.test_nammu_profile tests.test_identity tests.test_intent_engine
py -3 -m unittest discover -s tests
```

Results:
- Focused suite: 89 tests passed
- Full suite: 744 tests passed

## Notes

- Misroute detection is informational only and does not block the next operator message.
- Corrections are still only persisted when the operator explicitly uses `nammu-correct`.
- Session counters reset on login/logout and user switching.

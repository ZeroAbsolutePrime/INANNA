# Cycle 9 Phase 9.6 - The Multilingual Core

## Summary

Implemented the multilingual core upgrades requested for Cycle 9 Phase 9.6.

Completed work:
- Replaced `detect_language()` heuristics with `_LANGUAGE_MARKERS` lookup in `core/nammu_profile.py`
- Preserved the critical check order: `ca -> pt -> es -> eu -> en`
- Expanded `governance_signals.json` domain hints with Spanish, Catalan, and Portuguese signals
- Added `NAMMU_MULTILINGUAL_EXAMPLES` and appended it into `NAMMU_UNIVERSAL_PROMPT`
- Added `tests/test_multilingual_core.py` with 25 offline tests
- Updated phase assertions in identity-related tests

## detect_language Results

Observed results:

```text
hello there => en
hola tengo correo => es
correus => ca
bom dia tenho mensagem => pt
eskerrik asko => eu
```

Critical confirmation:

```text
detect_language("correus") => "ca"
```

This is correctly Catalan, not Spanish.

## _classify_domain_fast Results

Observed multilingual routing hints:

```text
resumen correos => email
que tinc avui => calendar
busca en internet nixos => browser
llegir document => document
obre firefox => desktop
```

## Sample `NAMMU_MULTILINGUAL_EXAMPLES`

```text
MULTILINGUAL EXAMPLES (Spanish / Catalan / Portuguese):
"urgentes?" (es) -> {"intent":"email_read_inbox","params":{"urgency_only":true},"confidence":0.95,"domain":"email"}
"resumen de ayer" (es) -> {"intent":"email_read_inbox","params":{"period":"yesterday","output_format":"summary"},"confidence":0.96,"domain":"email"}
"que tinc avui?" (ca) -> {"intent":"calendar_today","params":{},"confidence":0.97,"domain":"calendar"}
"resumeix els correus" (ca) -> {"intent":"email_read_inbox","params":{"output_format":"summary"},"confidence":0.95,"domain":"email"}
"busca NixOS" (es) -> {"intent":"browser_search","params":{"query":"NixOS"},"confidence":0.98,"domain":"browser"}
"obre firefox" (ca) -> {"intent":"desktop_open_app","params":{"app":"firefox"},"confidence":0.97,"domain":"desktop"}
```

## Verification

Commands run:

```text
py -3 -m py_compile inanna\core\nammu_profile.py inanna\core\nammu_intent.py inanna\identity.py inanna\tests\test_multilingual_core.py inanna\tests\test_identity.py inanna\tests\test_intent_engine.py
py -3 -m unittest tests.test_multilingual_core tests.test_nammu_profile tests.test_identity tests.test_intent_engine
py -3 -m unittest discover -s tests
```

Results:
- Focused suite: 95 tests passed
- Full suite: 770 tests passed

## Notes

- Catalan is checked before Spanish to avoid overlap around words like `correus`.
- Portuguese markers were expanded, but ambiguous overlap was kept conservative so Spanish inputs still resolve correctly.

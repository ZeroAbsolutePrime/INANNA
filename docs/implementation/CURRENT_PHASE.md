# CURRENT PHASE: Cycle 9 - Phase 9.6 - The Multilingual Core
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date: 2026-04-22**
**Cycle: 9 — NAMMU Reborn: The Living Interpreter**
**Replaces: Cycle 9 Phase 9.5 - The Feedback Loop (COMPLETE)**

---

## MANDATORY READING — in this exact order

1. docs/nammu_vision.md              ← Dimension VI: Multilingual
2. docs/cycle9_master_plan.md
3. docs/implementation/CURRENT_PHASE.md (this file)
4. CODEX_DOCTRINE.md
5. ABSOLUTE_PROTOCOL.md

---

## What Already Exists (audited before writing this phase)

OperatorProfile.detect_language() — heuristic detection:
  en: default fallback — WORKS
  es: hola, urgentes, correo, tengo — WORKS
  ca: resumeix, missatge — WORKS (partial)
  pt: obrigado — WORKS (partial)
  MISSING: gracies/gràcies (ca), bom dia/hoje (pt)

_classify_domain_fast() — reads governance_signals.json domain_hints:
  email signals include: urgentes, tengo emails — WORKS
  MISSING: resumen correos (es), que tinc avui (ca)
  MISSING: Catalan calendar signals, Portuguese email signals

governance_signals.json domain_hints:
  Currently English-only signals for most domains
  91 total signals, 0 Spanish/Catalan/Portuguese domain signals

NAMMU_UNIVERSAL_PROMPT:
  Contains "any language" note — GOOD
  No Spanish/Catalan/Portuguese examples — MISSING

ZAERA's languages: English, Spanish, Catalan, Portuguese
All four must work without switching languages.

---

## What Phase 9.6 Builds

**Three targeted fixes for full multilingual support:**

### Fix 1 — Expand detect_language() in nammu_profile.py

Add missing markers for Catalan and Portuguese,
and add Basque as a recognised (but pass-through) language:

```python
LANGUAGE_MARKERS = {
    "ca": [
        # Catalan
        "gracies", "gràcies", "avui", "dema", "demà",
        "correus", "correu", "resumeix", "missatge", "missatges",
        "tinc", "tens", "puc", "pots", "que tens",
        "calendari", "reunio", "reunió",
    ],
    "pt": [
        # Portuguese
        "obrigado", "obrigada", "bom dia", "boa tarde", "boa noite",
        "hoje", "amanha", "amanhã", "email", "mensagem",
        "tenho", "quero", "posso", "pode",
        "calendario", "resumo", "urgente",  # pt versions
    ],
    "es": [
        # Spanish (existing + expanded)
        "gracias", "hola", "correo", "hoy", "manana", "mañana",
        "urgentes", "urgente", "resumen", "tienes", "tengo",
        "mensajes", "mensaje", "calendario", "reunión",
        "que tengo", "tengo emails", "correos de",
    ],
    "eu": [
        # Basque — recognised, not further parsed
        "eskerrik asko", "kaixo", "bihar", "gaur",
    ],
}
```

New detect_language() checks these markers in order:
ca → pt → es → eu → en (default)
Order matters: Catalan checked before Spanish to avoid
`correus` being misdetected as Spanish `correo`.

### Fix 2 — Add multilingual domain signals to governance_signals.json

Extend domain_hints for email, calendar, browser, document
with Spanish and Catalan equivalents:

```json
"domain_hints": {
  "email": [
    ...existing English...,
    "correo", "correos", "correus", "correu",
    "urgentes", "urgente", "resumen correos",
    "tengo emails", "tinc correus",
    "mensajes de", "missatges de"
  ],
  "calendar": [
    ...existing English...,
    "calendario", "calendari", "agenda",
    "que tengo hoy", "que tinc avui",
    "reunión", "reunio", "cita",
    "proximos eventos", "pròxims events"
  ],
  "browser": [
    ...existing English...,
    "busca en internet", "cerca a internet",
    "buscar en la web", "abrir navegador"
  ],
  "document": [
    ...existing English...,
    "leer documento", "llegir document",
    "abrir archivo", "obrir fitxer",
    "crear informe", "crear document"
  ],
  "desktop": [
    ...existing English...,
    "abrir", "obrir", "abrir programa",
    "abre firefox", "obre firefox"
  ]
}
```

### Fix 3 — Add multilingual examples to NAMMU_UNIVERSAL_PROMPT

Add a multilingual examples section to make clear the LLM
should handle non-English input:

```python
NAMMU_MULTILINGUAL_EXAMPLES = """
MULTILINGUAL EXAMPLES (Spanish / Catalan / Portuguese):
"urgentes?" (es) -> {"intent":"email_read_inbox","params":{"urgency_only":true},"confidence":0.95,"domain":"email"}
"resumen de ayer" (es) -> {"intent":"email_read_inbox","params":{"period":"yesterday","output_format":"summary"},"confidence":0.96,"domain":"email"}
"que tinc avui?" (ca) -> {"intent":"calendar_today","params":{},"confidence":0.97,"domain":"calendar"}
"resumeix els correus" (ca) -> {"intent":"email_read_inbox","params":{"output_format":"summary"},"confidence":0.95,"domain":"email"}
"busca NixOS" (es) -> {"intent":"browser_search","params":{"query":"NixOS"},"confidence":0.98,"domain":"browser"}
"obre firefox" (ca) -> {"intent":"desktop_open_app","params":{"app":"firefox"},"confidence":0.97,"domain":"desktop"}
"""
```

Append this to NAMMU_UNIVERSAL_PROMPT before the final
"Return exactly:" instruction.

---

## What You Are Building

### Task 1 — Expand nammu_profile.py detect_language()

Replace the current detect_language() with the LANGUAGE_MARKERS
dict approach. Catalan checked before Spanish to avoid overlap.

```python
# Language marker dictionary
_LANGUAGE_MARKERS: dict[str, list[str]] = {
    "ca": [
        "gracies", "avui", "dema", "correus", "correu",
        "resumeix", "missatge", "missatges", "tinc", "calendari",
        "reunio", "puc", "pots", "gràcies", "demà", "reunió",
    ],
    "pt": [
        "obrigado", "obrigada", "bom dia", "boa tarde", "boa noite",
        "hoje", "amanha", "mensagem", "tenho", "quero", "posso",
        "resumo", "calendario",
    ],
    "es": [
        "gracias", "hola", "correo", "hoy", "urgentes", "urgente",
        "resumen", "tienes", "tengo", "mensajes", "mensaje",
        "calendario", "mañana", "manana", "correos",
        "que tengo", "tengo emails", "correos de",
    ],
    "eu": [
        "eskerrik asko", "kaixo", "bihar", "gaur",
    ],
}

def detect_language(self, text: str) -> str:
    text_lower = text.lower()
    # Check in order: ca before es (they share some words)
    for lang in ("ca", "pt", "es", "eu"):
        markers = _LANGUAGE_MARKERS.get(lang, [])
        if any(marker in text_lower for marker in markers):
            return lang
    return "en"
```

### Task 2 — Expand governance_signals.json domain_hints

Add Spanish and Catalan signals to the domain_hints section
for email, calendar, browser, document, and desktop domains.

Load from governance_signals.json — never hardcode domain
signals elsewhere. The JSON is the single source of truth.

### Task 3 — Add multilingual examples to nammu_intent.py

Insert NAMMU_MULTILINGUAL_EXAMPLES into NAMMU_UNIVERSAL_PROMPT.
Position: after the NONE section, before the final
"Return exactly:" instruction.

```python
NAMMU_UNIVERSAL_PROMPT = """...(existing)...

""" + NAMMU_MULTILINGUAL_EXAMPLES + """
Return exactly this JSON (no markdown, no explanation, nothing else):
{"intent": "...", "params": {...}, "confidence": 0.0-1.0, "domain": "..."}"""
```

### Task 4 — Update identity.py

CURRENT_PHASE = "Cycle 9 - Phase 9.6 - The Multilingual Core"

### Task 5 — Tests (all offline)

Create inanna/tests/test_multilingual_core.py (25 tests):

Language detection (detect_language):
  - detect_language("hello world") returns "en"
  - detect_language("urgentes?") returns "es"
  - detect_language("resumen de ayer") returns "es"
  - detect_language("hola tengo emails") returns "es"
  - detect_language("gracies") returns "ca"
  - detect_language("resumeix els correus") returns "ca"
  - detect_language("avui tinc reunio") returns "ca"
  - detect_language("obrigado") returns "pt"
  - detect_language("bom dia") returns "pt"
  - detect_language("eskerrik asko") returns "eu"
  - detect_language("anything from Matxalen?") returns "en"
    (English — mixed with name, no ES/CA/PT markers)

Domain classification non-English:
  - _classify_domain_fast("urgentes?") returns "email"
  - _classify_domain_fast("tengo emails?") returns "email"
  - _classify_domain_fast("resumen correos") returns "email"
  - _classify_domain_fast("que tinc avui?") returns "calendar"
  - _classify_domain_fast("busca en internet") returns "browser"
  - _classify_domain_fast("abrir firefox") returns "desktop"
  - _classify_domain_fast("leer documento") returns "document"

NAMMU_UNIVERSAL_PROMPT multilingual:
  - NAMMU_UNIVERSAL_PROMPT contains "urgentes?"
  - NAMMU_UNIVERSAL_PROMPT contains "any language"
  - NAMMU_UNIVERSAL_PROMPT contains "resumeix"
  - NAMMU_MULTILINGUAL_EXAMPLES is non-empty string

Language detection edge cases:
  - "correus" detected as "ca" (not confused with Spanish "correo")
  - "today urgentes" detected as "es" (mixed, Spanish marker wins)
  - detect_language on empty string returns "en" (no exception)
  - _LANGUAGE_MARKERS dict contains all 4 language keys

Update test_identity.py: CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/core/nammu_profile.py            <- MODIFY: detect_language,
                                           _LANGUAGE_MARKERS dict
inanna/core/nammu_intent.py             <- MODIFY: NAMMU_MULTILINGUAL_EXAMPLES,
                                           append to NAMMU_UNIVERSAL_PROMPT
inanna/config/governance_signals.json   <- MODIFY: multilingual domain signals
inanna/identity.py                      <- MODIFY: CURRENT_PHASE
inanna/tests/test_multilingual_core.py  <- NEW
inanna/tests/test_identity.py           <- MODIFY

---

## What You Are NOT Building

- No LLM-based language detection (heuristic only for now)
- No translation of INANNA's responses (CROWN responds in
  the operator's detected language only when the LLM supports it)
- No new Notion/external integrations
- No changes to tools.json or NixOS configs
- No changes to constitutional_filter.py or feedback loop
- Do NOT make LLM calls in tests

---

## Critical Constraints

1. Catalan MUST be checked before Spanish
   "correus" is Catalan, "correo" is Spanish.
   If Spanish checked first, Catalan words may be misdetected.
   Order: ca → pt → es → eu → en

2. detect_language NEVER raises exceptions
   On empty input or unexpected text: return "en"

3. governance_signals.json is the single source of truth
   for domain signals. The multilingual signals go in
   domain_hints, not hardcoded in Python.

4. NAMMU_MULTILINGUAL_EXAMPLES is a separate constant
   It is NOT embedded in NAMMU_UNIVERSAL_PROMPT's body.
   It is appended at construction time. This makes it
   easy to test independently and update without
   touching the main prompt logic.

---

## Definition of Done

- [ ] _LANGUAGE_MARKERS dict covers ca, pt, es, eu
- [ ] detect_language("gracies") returns "ca"
- [ ] detect_language("bom dia") returns "pt"
- [ ] detect_language("correus") returns "ca" not "es"
- [ ] governance_signals.json has Spanish + Catalan domain signals
- [ ] _classify_domain_fast("resumen correos") returns "email"
- [ ] _classify_domain_fast("que tinc avui?") returns "calendar"
- [ ] NAMMU_UNIVERSAL_PROMPT contains multilingual examples
- [ ] CURRENT_PHASE = "Cycle 9 - Phase 9.6 - The Multilingual Core"
- [ ] All tests pass: py -3 -m unittest discover -s tests (>=744)
- [ ] Pushed as cycle9-phase6-complete

---

## Handoff

Commit: cycle9-phase6-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE9_PHASE6_REPORT.md

The report MUST include:
  - detect_language test results for all 5 languages
  - _classify_domain_fast test results for ES + CA inputs
  - Sample NAMMU_MULTILINGUAL_EXAMPLES content
  - Confirmation "correus" → ca (not es)

Stop. Do not begin Phase 9.7 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-22*
*NAMMU does not ask ZAERA to switch languages.*
*NAMMU learns the language ZAERA is already speaking.*
*Spanish at midnight. Catalan when relaxed.*
*English for technical precision.*
*Portuguese when home calls.*
*NAMMU listens. NAMMU adapts.*
*The machine speaks human.*

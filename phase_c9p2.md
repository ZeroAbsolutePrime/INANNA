# CURRENT PHASE: Cycle 9 - Phase 9.2 - The Operator Profile
**Status: ACTIVE**
**Authorized by: INANNA NAMMU (Guardian) + Claude (Command Center)**
**Date: 2026-04-22**
**Cycle: 9 — NAMMU Reborn: The Living Interpreter**
**Replaces: Cycle 9 Phase 9.1 - The Intent Engine (COMPLETE)**

---

## MANDATORY READING — in this exact order

1. docs/nammu_vision.md              ← Dimension I and II live here
2. docs/cycle9_master_plan.md
3. docs/platform_architecture.md
4. docs/implementation/CURRENT_PHASE.md (this file)
5. CODEX_DOCTRINE.md
6. ABSOLUTE_PROTOCOL.md

---

## What Already Exists (audited before writing this phase)

UserProfile (core/profile.py, 12176 bytes):
  Fields already present:
    preferred_name, pronouns, languages (list)
    communication_style, preferred_length, formality
    observed_patterns (list — currently empty)
    recurring_topics (list — ["operator"])
    named_projects (list)
    domains (list)

NAMMU memory (core/nammu_memory.py):
  routing_log.jsonl — every routing decision recorded
  governance_log.jsonl — governance events recorded
  append_routing_event(), load_routing_history()

Active user profile: data/profiles/user_6396c88f.json
  INANNA NAMMU's profile with observed_patterns = []
  The profile is written and read. Infrastructure works.
  observed_patterns is waiting to be filled.

NAMMU governance log (real data):
  "what's on my calendar?" → calendar
  "open thunderbird" → desktop
  Routing decisions are being recorded.

---

## What Phase 9.2 Builds

Phase 9.2 activates the Operator Profile system.

NAMMU already records every routing decision.
NAMMU already has a profile with observed_patterns.
What is missing: the connection between them.

Phase 9.2 builds:
  1. OperatorProfileBuilder — reads routing history,
     extracts patterns, updates UserProfile.observed_patterns
  2. Profile enrichment — NAMMU receives the operator's
     profile as context before each intent extraction call
  3. Shorthand learning — NAMMU records shorthands
     (e.g. "mtx" = Matxalen) and uses them
  4. Language detection — NAMMU records which language
     INANNA NAMMU uses and updates profile.languages accordingly
  5. Correction recording — when NAMMU misroutes and the
     operator corrects it, the correction is stored and
     used as a few-shot example in future calls

The profile becomes NAMMU's memory of the person.
Every session, NAMMU knows ZAERA better than the last.

---

## Architecture

```
Every operator message:
  1. NAMMU classifies domain (fast, no LLM)
  2. NAMMU loads operator profile
  3. NAMMU builds enriched context:
     {
       "operator": "ZAERA",
       "preferred_language": "en/es (switches by mood)",
       "known_shorthands": {"mtx": "Matxalen"},
       "communication_style": "Queer",
       "preferred_length": "short",
       "recurring_topics": ["operator", "email", "calendar"],
       "recent_corrections": [
         {"misrouted": "mtx replied?", "correct": "email_search",
          "query": "Matxalen"}
       ]
     }
  4. NAMMU passes enriched context to LLM prompt
  5. LLM extracts intent using operator context
  6. Result is stored in routing_log for future learning
```

The profile enrichment is inserted into NAMMU_UNIVERSAL_PROMPT
as a dynamic section at the start:

```
[OPERATOR CONTEXT]
Name: ZAERA
Languages: English (technical), Spanish (relaxed)
Shorthands: "mtx" = Matxalen
Style: direct, short preferred
Recent correction: "mtx replied?" → email_search(query="Matxalen")
[END CONTEXT]

You are NAMMU... [rest of universal prompt]
```

---

## What You Are Building

### Task 1 — inanna/core/nammu_profile.py (NEW)

Create: inanna/core/nammu_profile.py

```python
"""
INANNA NYX — NAMMU Operator Profile
Phase 9.2: The Operator Profile

NAMMU learns the operator's communication patterns
from every interaction. The profile enriches intent
extraction with personal context.

What is stored per operator:
  - known_shorthands: {abbreviated: full_meaning}
  - language_patterns: {language: contexts_when_used}
  - routing_corrections: [{original, correct_intent, correct_params}]
  - domain_weights: {domain: frequency_score}
  - urgency_markers: [phrases that signal urgency]
  - session_patterns: {time_of_day: typical_domain}

Storage: data/realms/{realm}/nammu/operator_profiles/{user_id}.json
This file grows with every session.
It is never deleted — only appended.

See docs/nammu_vision.md Dimension I and II for full vision.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ── DATA STRUCTURES ─────────────────────────────────────────────────

@dataclass
class RoutingCorrection:
    """
    A correction NAMMU received from the operator.
    Stored as a few-shot example for future calls.
    """
    timestamp: str = ""
    original_text: str = ""         # what the operator said
    misrouted_to: str = ""          # what NAMMU thought
    correct_intent: str = ""        # what it should have been
    correct_params: dict = field(default_factory=dict)

    def to_example_line(self) -> str:
        """Format as a few-shot example for the LLM prompt."""
        params_str = json.dumps(self.correct_params)
        return (
            f'"{self.original_text}" '
            f'-> {{"intent":"{self.correct_intent}",'
            f'"params":{params_str}}}'
        )


@dataclass
class OperatorProfile:
    """
    NAMMU's learned model of an operator's communication style.
    Grows with every interaction. Never shrinks.
    """
    user_id: str = ""
    display_name: str = ""
    last_updated: str = ""

    # Language patterns
    # e.g. {"en": ["technical", "morning"], "es": ["relaxed", "evening"]}
    language_patterns: dict[str, list[str]] = field(default_factory=dict)
    primary_language: str = "en"

    # Shorthand lexicon: abbreviations → full meanings
    # e.g. {"mtx": "Matxalen", "act": "Actuavalles"}
    known_shorthands: dict[str, str] = field(default_factory=dict)

    # How often each domain is used (frequency score, 0.0-1.0)
    domain_weights: dict[str, float] = field(default_factory=dict)

    # Phrases that signal urgency for this operator
    urgency_markers: list[str] = field(default_factory=list)

    # Routing corrections from this operator
    routing_corrections: list[dict] = field(default_factory=list)

    # Topics this operator frequently mentions
    recurring_topics: list[str] = field(default_factory=list)

    # Communication preferences (from UserProfile, mirrored)
    communication_style: str = ""
    preferred_length: str = "short"

    def to_nammu_context(self) -> str:
        """
        Build the [OPERATOR CONTEXT] block for the LLM prompt.
        Injected at the start of NAMMU_UNIVERSAL_PROMPT.
        """
        lines = ["[OPERATOR CONTEXT]"]
        if self.display_name:
            lines.append(f"Operator: {self.display_name}")

        # Language preference
        if self.language_patterns:
            lang_desc = []
            for lang, contexts in self.language_patterns.items():
                lang_desc.append(f"{lang} ({', '.join(contexts[:2])})")
            lines.append(f"Languages: {' | '.join(lang_desc)}")
        elif self.primary_language:
            lines.append(f"Primary language: {self.primary_language}")

        # Known shorthands — critical for accurate routing
        if self.known_shorthands:
            sh = ', '.join(f'"{k}"={v}' for k, v in
                          list(self.known_shorthands.items())[:8])
            lines.append(f"Shorthands: {sh}")

        # Communication style
        if self.preferred_length == "short":
            lines.append("Style: prefers short, direct responses")

        # Top domains (what this operator uses most)
        if self.domain_weights:
            top = sorted(self.domain_weights.items(),
                        key=lambda x: x[1], reverse=True)[:4]
            lines.append(
                f"Most used: {', '.join(d for d, _ in top)}"
            )

        # Recent corrections (few-shot examples)
        if self.routing_corrections:
            recent = self.routing_corrections[-3:]
            corrections_clean = []
            for c in recent:
                obj = RoutingCorrection(**c)
                corrections_clean.append(obj.to_example_line())
            if corrections_clean:
                lines.append("Recent corrections:")
                for ex in corrections_clean:
                    lines.append(f"  {ex}")

        lines.append("[END CONTEXT]")
        return "\n".join(lines)

    def record_shorthand(self, abbreviation: str, full_meaning: str) -> None:
        """Record a new shorthand the operator uses."""
        self.known_shorthands[abbreviation.lower()] = full_meaning
        self.last_updated = _utc_now()

    def record_correction(
        self,
        original_text: str,
        misrouted_to: str,
        correct_intent: str,
        correct_params: dict,
    ) -> None:
        """Record a routing correction. Used as few-shot example."""
        correction = RoutingCorrection(
            timestamp=_utc_now(),
            original_text=original_text,
            misrouted_to=misrouted_to,
            correct_intent=correct_intent,
            correct_params=correct_params,
        )
        self.routing_corrections.append(asdict(correction))
        # Keep only last 20 corrections
        if len(self.routing_corrections) > 20:
            self.routing_corrections = self.routing_corrections[-20:]
        self.last_updated = _utc_now()

    def record_routing(self, domain: str) -> None:
        """Record that a domain was used — updates frequency weights."""
        current = self.domain_weights.get(domain, 0.0)
        # Exponential moving average: new = 0.1 + 0.9 * old
        # Gradually increases weight for frequently used domains
        self.domain_weights[domain] = min(1.0, current + 0.05)
        self.last_updated = _utc_now()

    def detect_language(self, text: str) -> str:
        """
        Detect language of input text using simple heuristics.
        Returns ISO language code: 'en', 'es', 'ca', 'pt'.
        On DGX: replace with LLM language detection.
        """
        text_lower = text.lower()
        # Catalan markers
        if any(w in text_lower for w in
               ['gràcies', 'hola', 'correus', 'avui', 'demà',
                'resumeix', 'missatge']):
            return 'ca'
        # Portuguese markers
        if any(w in text_lower for w in
               ['obrigad', 'olá', 'mensagem', 'correio',
                'amanhã', 'hoje']):
            return 'pt'
        # Spanish markers
        if any(w in text_lower for w in
               ['gracias', 'hola', 'correo', 'hoy', 'mañana',
                'urgentes', 'resumen', 'tienes', 'tengo']):
            return 'es'
        return 'en'

    def update_language_pattern(self, text: str, domain: str) -> None:
        """Record language usage context."""
        lang = self.detect_language(text)
        if lang not in self.language_patterns:
            self.language_patterns[lang] = []
        context = domain if domain != "none" else "conversation"
        if context not in self.language_patterns[lang]:
            self.language_patterns[lang].append(context)
        if lang != self.primary_language:
            # Update primary if this language is becoming dominant
            lang_counts = {
                l: len(ctxs) for l, ctxs in
                self.language_patterns.items()
            }
            self.primary_language = max(lang_counts, key=lang_counts.get)


# ── STORAGE ──────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _profile_path(nammu_dir: Path, user_id: str) -> Path:
    """Path to operator's NAMMU profile file."""
    return nammu_dir / "operator_profiles" / f"{user_id}.json"


def load_operator_profile(
    nammu_dir: Path, user_id: str
) -> OperatorProfile:
    """
    Load operator profile from disk.
    Returns empty profile if not found — never raises.
    """
    path = _profile_path(nammu_dir, user_id)
    if not path.exists():
        return OperatorProfile(
            user_id=user_id,
            last_updated=_utc_now(),
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return OperatorProfile(**{
            k: v for k, v in data.items()
            if k in OperatorProfile.__dataclass_fields__
        })
    except Exception:
        return OperatorProfile(
            user_id=user_id,
            last_updated=_utc_now(),
        )


def save_operator_profile(
    nammu_dir: Path, profile: OperatorProfile
) -> None:
    """Save operator profile to disk. Never raises."""
    path = _profile_path(nammu_dir, profile.user_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(profile), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def build_profile_from_user_profile(
    user_profile: Any,
    nammu_dir: Path,
) -> OperatorProfile:
    """
    Seed the NAMMU operator profile from the existing UserProfile.
    Called once when profile doesn't exist yet.
    """
    uid = getattr(user_profile, "user_id", "")
    profile = load_operator_profile(nammu_dir, uid)

    # Mirror from UserProfile
    profile.display_name = (
        getattr(user_profile, "preferred_name", "")
        or getattr(user_profile, "display_name", "")
        or uid
    )
    profile.communication_style = getattr(
        user_profile, "communication_style", ""
    )
    profile.preferred_length = getattr(
        user_profile, "preferred_length", "short"
    )

    # Seed languages from UserProfile
    langs = getattr(user_profile, "languages", ["en"])
    if langs:
        profile.primary_language = langs[0]
        for lang in langs:
            if lang not in profile.language_patterns:
                profile.language_patterns[lang] = []

    # Seed recurring topics as domain weights
    topics = getattr(user_profile, "recurring_topics", [])
    for topic in topics:
        profile.domain_weights[topic] = 0.3

    return profile


# ── SHORTHAND DETECTION ──────────────────────────────────────────────

# Patterns that suggest the user is using shorthand
# e.g. "mtx" alone as a word, or very short words
_SHORTHAND_PATTERN = re.compile(r'\b([a-z]{2,4})\b')


def extract_potential_shorthands(
    text: str, known_shorthands: dict[str, str]
) -> list[str]:
    """
    Find short words in text that might be shorthands.
    Returns list of candidates not yet in known_shorthands.
    Only flags words 2-4 chars that appear standalone.
    """
    candidates = []
    for match in _SHORTHAND_PATTERN.finditer(text.lower()):
        word = match.group(1)
        if word not in known_shorthands and len(word) <= 4:
            # Exclude common English/Spanish stop words
            if word not in {
                'the', 'and', 'for', 'not', 'but', 'can',
                'any', 'all', 'my', 'me', 'do', 'it', 'is',
                'en', 'de', 'la', 'el', 'que', 'los', 'las',
                'una', 'por', 'con', 'he', 'she', 'we', 'ok',
                'hi', 'yes', 'no', 'go', 'get',
            }:
                candidates.append(word)
    return candidates
```

### Task 2 — Wire OperatorProfile into nammu_intent.py

In nammu_intent.py, modify `extract_intent_universal()` and
`nammu_first_routing()` to accept and use the operator profile:

```python
def extract_intent_universal(
    text: str,
    conversation_context: list[dict] | None = None,
    operator_profile: OperatorProfile | None = None,  # ← NEW
) -> IntentResult:
    """
    Extract intent with operator profile enrichment.
    If profile provided, prepend [OPERATOR CONTEXT] to prompt.
    """
    system_prompt = NAMMU_UNIVERSAL_PROMPT
    if operator_profile:
        context_block = operator_profile.to_nammu_context()
        system_prompt = context_block + "\n\n" + NAMMU_UNIVERSAL_PROMPT
    # ... rest of existing implementation unchanged
```

And in `nammu_first_routing()`:
```python
def nammu_first_routing(
    text: str,
    conversation_context: list | None = None,
    operator_profile: OperatorProfile | None = None,  # ← NEW
) -> dict | None:
    """Try NAMMU LLM with operator profile context."""
    domain = _classify_domain_fast(text.lower())
    if domain == "none":
        return None
    result_box = [None]
    def _run():
        result_box[0] = extract_intent_universal(
            text, conversation_context, operator_profile
        )
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=3.0)
    r = result_box[0]
    if r and r.success and r.confidence >= 0.75:
        req = r.to_tool_request()
        if req:
            req["_nammu_domain"] = r.domain
        return req
    return None
```

### Task 3 — Wire profile into server.py dispatch

In InterfaceServer, load the operator profile at session start
and pass it to nammu_first_routing on every turn:

```python
# In InterfaceServer.__init__:
from core.nammu_profile import (
    load_operator_profile, save_operator_profile,
    build_profile_from_user_profile,
)
self.nammu_profile = build_profile_from_user_profile(
    self.profile_manager.load(self.active_user.user_id),
    self.nammu_dir,
)

# In _run_routed_turn() or equivalent:
# After tool executes, record domain usage
if tool_result:
    domain = tool_result.tool.split("_")[0]  # "email", "doc", etc.
    self.nammu_profile.record_routing(domain)
    self.nammu_profile.update_language_pattern(text, domain)
    save_operator_profile(self.nammu_dir, self.nammu_profile)

# Pass profile to routing:
tool_request = nammu_first_routing(
    text,
    conversation_context,
    operator_profile=self.nammu_profile,
)
```

### Task 4 — Add correction recording command

Add a command `nammu-correct` that the operator can use to
teach NAMMU when it misrouted:

Usage: `nammu-correct email_search Matxalen`
(means: "what I just said should have routed to
email_search with query Matxalen")

In handle_command():
```python
elif command_name == "nammu-correct":
    # Parse: nammu-correct <intent> [params...]
    parts = raw_cmd.split(None, 2)
    if len(parts) >= 2:
        correct_intent = parts[1]
        # Get last NAMMU routing from profile
        self.nammu_profile.record_correction(
            original_text=self._last_nammu_input or "",
            misrouted_to=self._last_nammu_route or "unknown",
            correct_intent=correct_intent,
            correct_params={},
        )
        save_operator_profile(self.nammu_dir, self.nammu_profile)
        await self.broadcast({
            "type": "system",
            "text": f"nammu > correction recorded: '{correct_intent}'"
        })
```

### Task 5 — Add shorthand registration command

Add command `nammu-learn`:

Usage: `nammu-learn mtx Matxalen`
(teaches NAMMU that "mtx" means "Matxalen")

```python
elif command_name == "nammu-learn":
    parts = raw_cmd.split(None, 2)
    if len(parts) == 3:
        abbreviation = parts[1].lower()
        full_meaning = parts[2]
        self.nammu_profile.record_shorthand(abbreviation, full_meaning)
        save_operator_profile(self.nammu_dir, self.nammu_profile)
        await self.broadcast({
            "type": "system",
            "text": (f"nammu > learned: '{abbreviation}' = "
                    f"'{full_meaning}'")
        })
```

### Task 6 — Update help_system.py

Add NAMMU PROFILE section:

```
  NAMMU PROFILE (teach INANNA your language)
    "nammu-learn mtx Matxalen"     Teach shorthand (mtx = Matxalen)
    "nammu-learn act Actuavalles"  Teach another shorthand
    "nammu-correct email_search"   Correct last misrouting
    "nammu-profile"                Show your current profile

  After teaching: INANNA will understand "mtx replied?"
  Profile grows automatically from every interaction.
```

Add `nammu-profile` command to handle_command():
```python
elif command_name == "nammu-profile":
    profile = self.nammu_profile
    lines = [
        f"nammu > operator profile for {profile.display_name}",
        f"  languages: {profile.language_patterns}",
        f"  shorthands: {profile.known_shorthands}",
        f"  top domains: {sorted(profile.domain_weights.items(), key=lambda x:-x[1])[:5]}",
        f"  corrections: {len(profile.routing_corrections)}",
    ]
    await self.broadcast({"type":"system","text":"\n".join(lines)})
```

### Task 7 — Update identity.py

CURRENT_PHASE = "Cycle 9 - Phase 9.2 - The Operator Profile"

### Task 8 — Tests (all offline — no LLM calls)

Create inanna/tests/test_nammu_profile.py (25 tests):

  - OperatorProfile instantiates with defaults
  - OperatorProfile.to_nammu_context includes display_name
  - OperatorProfile.to_nammu_context includes shorthands
  - OperatorProfile.to_nammu_context includes corrections
  - OperatorProfile.to_nammu_context includes top domains
  - OperatorProfile.record_shorthand stores correctly
  - OperatorProfile.record_correction stores correctly
  - OperatorProfile.record_correction keeps only last 20
  - OperatorProfile.record_routing increases domain weight
  - OperatorProfile.record_routing caps at 1.0
  - OperatorProfile.detect_language('hola') returns 'es'
  - OperatorProfile.detect_language('hello') returns 'en'
  - OperatorProfile.detect_language('gràcies') returns 'ca'
  - OperatorProfile.detect_language('obrigado') returns 'pt'
  - OperatorProfile.update_language_pattern records context
  - RoutingCorrection.to_example_line formats correctly
  - load_operator_profile returns empty profile when missing
  - load_operator_profile returns correct profile when present
    (write a temp file, load it, verify fields)
  - save_operator_profile creates file correctly
  - save_operator_profile creates parent directories
  - build_profile_from_user_profile seeds display_name
  - build_profile_from_user_profile seeds preferred_length
  - extract_potential_shorthands finds short words
  - extract_potential_shorthands excludes stop words
  - extract_potential_shorthands excludes known shorthands

Update test_identity.py: CURRENT_PHASE assertion.

---

## Storage Path

```
data/realms/{realm}/nammu/operator_profiles/{user_id}.json
```

For ZAERA:
```
data/realms/default/nammu/operator_profiles/user_6396c88f.json
```

This file is created the first time the server starts
after Phase 9.2 is deployed. It is never deleted.

---

## Permitted file changes

inanna/core/nammu_profile.py            <- NEW
inanna/core/nammu_intent.py             <- MODIFY: profile parameter
inanna/ui/server.py                     <- MODIFY: load/save profile,
                                           wire into routing,
                                           add commands
inanna/core/help_system.py              <- MODIFY: profile section
inanna/identity.py                      <- MODIFY: CURRENT_PHASE
inanna/tests/test_nammu_profile.py      <- NEW
inanna/tests/test_identity.py           <- MODIFY

---

## What You Are NOT Building

- No constitutional filter (Phase 9.3)
- No multilingual LLM detection (simple heuristic only)
- No cross-operator pattern sharing (Cycle 11)
- No changes to tools.json or NixOS configs
- Do NOT modify the existing UserProfile dataclass
- Do NOT make LLM calls in tests

---

## Critical Constraints

1. The operator profile is ADDITIVE to the routing prompt
   It never replaces NAMMU_UNIVERSAL_PROMPT
   It is prepended as [OPERATOR CONTEXT]...[END CONTEXT]

2. Profile loading NEVER blocks the server
   If the profile file is corrupt or missing:
   load_operator_profile() returns an empty OperatorProfile
   The server continues normally

3. Profile saving is fire-and-forget
   save_operator_profile() wraps writes in try/except
   A save failure never surfaces to the operator

4. The profile enriches on every turn, even current hardware
   Even if the LLM times out and regex runs:
   domain_weights and language_patterns still update
   The profile grows regardless of LLM availability

5. nammu-learn and nammu-correct are operator commands
   They do NOT require proposal approval
   They are teaching commands, not action commands

---

## Definition of Done

- [ ] core/nammu_profile.py with all dataclasses and functions
- [ ] OperatorProfile.to_nammu_context() formats correctly
- [ ] detect_language() works for en/es/ca/pt
- [ ] load/save_operator_profile() work correctly
- [ ] nammu_intent.py accepts operator_profile parameter
- [ ] server.py loads profile at session start
- [ ] server.py updates profile on every tool execution
- [ ] nammu-learn command works
- [ ] nammu-correct command works
- [ ] nammu-profile command shows current profile
- [ ] help_system.py updated
- [ ] Profile file created at correct path on first run
- [ ] CURRENT_PHASE = "Cycle 9 - Phase 9.2 - The Operator Profile"
- [ ] All tests pass: py -3 -m unittest discover -s tests (>=648)
- [ ] Pushed as cycle9-phase2-complete

---

## Handoff

Commit: cycle9-phase2-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE9_PHASE2_REPORT.md

The report MUST include:
  - Confirmation operator profile file is created on startup
  - Show the actual profile JSON for user_6396c88f after startup
  - Test of nammu-learn command
  - Test of to_nammu_context() output with a seeded profile

Stop. Do not begin Phase 9.3 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: INANNA NAMMU*
*Date: 2026-04-22*
*Every session, NAMMU knows ZAERA better.*
*Every correction, NAMMU becomes more fluent.*
*Every shorthand learned, the gap closes.*
*"mtx replied?" becomes crystal clear.*
*The operator does not adapt to the machine.*
*The machine adapts to the operator.*
*This is Dimension I made real.*

# CURRENT PHASE: Cycle 9 - Phase 9.4 - The Comprehension Layer
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date: 2026-04-22**
**Cycle: 9 — NAMMU Reborn: The Living Interpreter**
**Replaces: Cycle 9 Phase 9.3 - The Constitutional Filter (COMPLETE)**

---

## MANDATORY READING — in this exact order

1. docs/nammu_vision.md
2. docs/cycle9_master_plan.md
3. docs/implementation/CURRENT_PHASE.md (this file)
4. CODEX_DOCTRINE.md
5. ABSOLUTE_PROTOCOL.md

---

## What Already Exists (audited before writing this phase)

Comprehension classes already built in Cycle 8:

  core/nammu_intent.py:
    EmailComprehension — total, unread, urgent, summaries, actions
    build_comprehension(emails, period, urgency_filter) → EmailComprehension
    WIRED in server.py lines 3568-3581 (email_read_inbox + email_search)

  core/document_workflows.py:
    DocumentComprehension — title, format, word_count, key_points, actions
    build_document_comprehension(record) → DocumentComprehension
    to_crown_context() → str
    NOT WIRED in server.py

  core/calendar_workflows.py:
    CalendarComprehension — total, today, upcoming, overdue, source
    build_calendar_comprehension(result, period) → CalendarComprehension
    to_crown_context() → str
    NOT WIRED in server.py

  core/browser_workflows.py:
    PageRecord — url, title, content, word_count
    format_page_result(record) → str  (basic formatting only)
    NO structured comprehension exists
    NOT WIRED specifically (falls through to generic handler)

server.py current state:
  Line 3567: is_email_comprehension flag (only email handled)
  Line 3603: if is_email_comprehension: → special CROWN instruction
  Line 3617: elif result_is_empty: → hallucination guard
  Line 3629: else: → generic handler

What is missing:
  - Document comprehension not wired → raw text to CROWN
  - Calendar comprehension not wired → raw text to CROWN
  - Browser has no comprehension class → raw text to CROWN
  - No structured CROWN instructions for doc/calendar/browser

---

## What Phase 9.4 Builds

Wire all existing comprehension into server.py.
Add BrowserComprehension for the browser faculty.
Give CROWN structured, domain-specific instructions for every
faculty — not just email.

The principle (from nammu_vision.md):
  Tools return raw data.
  Comprehension turns raw data into meaning.
  CROWN receives meaning, not raw data.
  This eliminates hallucination. CROWN presents what exists.

---

## What You Are Building

### Task 1 — Add BrowserComprehension to browser_workflows.py

The browser faculty currently has no comprehension class.
Add one alongside the existing PageRecord:

```python
@dataclass
class BrowserComprehension:
    """
    Structured summary of a fetched web page or search result.
    Given to CROWN for natural presentation.
    No LLM needed — pure deterministic analysis.
    """
    url: str = ""
    title: str = ""
    word_count: int = 0
    is_search: bool = False
    query: str = ""            # if is_search, the original query
    excerpt: str = ""          # first 400 chars of meaningful content
    key_topics: list[str] = field(default_factory=list)
    is_pdf: bool = False
    status_code: int = 0
    error: Optional[str] = None

    def to_crown_context(self) -> str:
        """Format for CROWN to present naturally."""
        if self.error:
            return f"browser > error: {self.error}"
        if self.is_search:
            lines = [
                f"WEB SEARCH: {self.query!r}",
                f"Results from: {self.url}",
                f"",
                f"CONTENT ({self.word_count} words):",
                self.excerpt,
            ]
        else:
            lines = [
                f"WEB PAGE: {self.title or self.url}",
                f"URL: {self.url}",
                f"Size: {self.word_count} words",
            ]
            if self.key_topics:
                lines.append(f"Topics: {', '.join(self.key_topics[:5])}")
            lines.extend(["", "CONTENT:", self.excerpt])
        return "\n".join(l for l in lines if l is not None)


def build_browser_comprehension(
    record: PageRecord,
    query: str = "",
    is_search: bool = False,
) -> BrowserComprehension:
    """
    Build structured comprehension from a PageRecord.
    Extracts a meaningful excerpt and topic keywords.
    No LLM. Deterministic. No hallucination.
    """
    if not record.success:
        return BrowserComprehension(error=record.error or "Unknown error")

    content = record.content or ""

    # Extract excerpt: first 400 chars of non-empty lines
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    excerpt_lines = []
    total_chars = 0
    for line in lines:
        if total_chars >= 400:
            break
        excerpt_lines.append(line)
        total_chars += len(line)
    excerpt = "\n".join(excerpt_lines)

    # Extract topic keywords: capitalised words and short phrases
    import re
    topic_candidates = re.findall(r'\b[A-Z][a-z]{2,}\b', content[:2000])
    # Count and deduplicate
    from collections import Counter
    counts = Counter(topic_candidates)
    key_topics = [w for w, _ in counts.most_common(8)
                  if w.lower() not in {
                      'The', 'This', 'That', 'With', 'From',
                      'Your', 'Have', 'Will', 'Are', 'For',
                  }]

    return BrowserComprehension(
        url=record.url,
        title=record.title,
        word_count=record.word_count,
        is_search=is_search,
        query=query,
        excerpt=excerpt[:400],
        key_topics=key_topics[:6],
        status_code=record.status_code,
    )
```

Also update BrowserWorkflows to use comprehension:
```python
def read_page(self, url: str, js: bool = False) -> tuple[PageRecord, BrowserComprehension]:
    """Returns page + comprehension."""
    record = ...existing...
    comp = build_browser_comprehension(record)
    return record, comp

def search_web(self, query: str) -> tuple[PageRecord, BrowserComprehension]:
    """Returns results + comprehension."""
    record = ...existing...
    comp = build_browser_comprehension(record, query=query, is_search=True)
    return record, comp
```

Note: Return type changes for these two methods. Update
run_browser_tool() in main.py / server.py accordingly.

### Task 2 — Wire all comprehensions into server.py

Replace the current single `is_email_comprehension` flag
with a unified comprehension dispatch in the tool result handler.

Current pattern (lines 3567-3643):
```python
is_email_comprehension = False
if result.tool in {"email_read_inbox", "email_search"} ...:
    ... email comprehension ...
```

Replace with a unified dispatch:
```python
# ── COMPREHENSION DISPATCH ────────────────────────────────────
# Each faculty has a comprehension class that structures raw data
# for CROWN. CROWN always receives meaning, not raw output.
# No hallucination: CROWN can only present what comprehension provides.

comprehension_ctx = None
comprehension_domain = ""

if result.tool in {"email_read_inbox", "email_search"} and result.success:
    emails = result.data.get("emails", [])
    if emails:
        comprehension = build_comprehension(emails, ...)
        comprehension_ctx = comprehension.to_crown_context()
        comprehension_domain = "email"

elif result.tool == "doc_read" and result.success:
    from core.document_workflows import build_document_comprehension, DocumentRecord
    doc_record = result.data.get("record")
    if doc_record:
        comp = build_document_comprehension(doc_record)
        comprehension_ctx = comp.to_crown_context()
        comprehension_domain = "document"

elif result.tool in {"calendar_today", "calendar_upcoming"} and result.success:
    from core.calendar_workflows import build_calendar_comprehension
    cal_result = result.data.get("calendar_result")
    period = result.data.get("period", "")
    if cal_result:
        comp = build_calendar_comprehension(cal_result, period_label=period)
        comprehension_ctx = comp.to_crown_context()
        comprehension_domain = "calendar"

elif result.tool in {"browser_read", "browser_search"} and result.success:
    from core.browser_workflows import BrowserComprehension
    comp = result.data.get("comprehension")
    if comp and isinstance(comp, BrowserComprehension):
        comprehension_ctx = comp.to_crown_context()
        comprehension_domain = "browser"

# Use comprehension if available, else raw summary
if comprehension_ctx:
    tool_result_summary = comprehension_ctx
    tool_result_lines = [tool_result_summary]
```

### Task 3 — Domain-specific CROWN instructions

Replace `is_email_comprehension` check with domain-specific
CROWN instructions for each faculty:

```python
CROWN_INSTRUCTIONS = {
    "email": (
        "INBOX DATA (real, no hallucination):\n{summary}\n---\n"
        "Present naturally. Urgent first. Suggest next action.\n"
        "DO NOT invent email content not shown above."
    ),
    "document": (
        "DOCUMENT DATA (read directly from file, no hallucination):\n{summary}\n---\n"
        "Summarise the document briefly.\n"
        "Mention title, format, size, and key points.\n"
        "DO NOT invent content not shown above.\n"
        "If the operator wants more detail, they can ask."
    ),
    "calendar": (
        "CALENDAR DATA (from Thunderbird, no hallucination):\n{summary}\n---\n"
        "Present events naturally.\n"
        "If 0 events: explain the Google Calendar sync situation clearly.\n"
        "DO NOT invent events not shown above."
    ),
    "browser": (
        "WEB CONTENT (fetched live, no hallucination):\n{summary}\n---\n"
        "Summarise what the page contains.\n"
        "For searches: summarise the results, not just list them.\n"
        "DO NOT invent content not shown above.\n"
        "DO NOT reproduce large chunks of text verbatim."
    ),
}

if comprehension_domain in CROWN_INSTRUCTIONS:
    tool_instruction = CROWN_INSTRUCTIONS[comprehension_domain].format(
        summary=tool_result_summary
    )
elif result_is_empty:
    tool_instruction = ... (existing hallucination guard)
else:
    tool_instruction = ... (existing generic handler)
```

### Task 4 — Ensure tool result data carries comprehension objects

The run_browser_tool() and run_document_tool() functions
must store their comprehension objects in result.data so
server.py can retrieve them.

For browser:
```python
# In run_browser_tool():
record, comp = browser_workflows.read_page(url)
result.data["record"] = record
result.data["comprehension"] = comp
```

For document:
```python
# In run_document_tool():
record, comp = document_workflows.read_document(path)
result.data["record"] = record
result.data["comprehension"] = comp
```

For calendar:
```python
# In run_calendar_tool():
cal_result, comp = calendar_workflows.read_today()
result.data["calendar_result"] = cal_result
result.data["comprehension"] = comp
result.data["period"] = "today"
```

### Task 5 — Update identity.py

CURRENT_PHASE = "Cycle 9 - Phase 9.4 - The Comprehension Layer"

### Task 6 — Tests (all offline)

Create inanna/tests/test_comprehension_layer.py (25 tests):

  - BrowserComprehension instantiates with defaults
  - BrowserComprehension.to_crown_context includes title
  - BrowserComprehension.to_crown_context includes URL
  - BrowserComprehension.to_crown_context handles error
  - BrowserComprehension.to_crown_context marks search result
  - build_browser_comprehension returns error comp on failed record
  - build_browser_comprehension extracts excerpt from content
  - build_browser_comprehension sets is_search=True when query provided
  - build_browser_comprehension word_count matches record
  - DocumentComprehension.to_crown_context includes title and format
  - DocumentComprehension.to_crown_context includes word_count
  - build_document_comprehension extracts headings as key_points
  - CalendarComprehension.to_crown_context includes period_label
  - CalendarComprehension.to_crown_context notes sync when 0 events
  - EmailComprehension.to_crown_context includes total count
  - All four comprehension to_crown_context methods return non-empty str
  - All four comprehension to_crown_context methods never raise exceptions
    even on empty/malformed input (pass empty dataclass)
  - CROWN_INSTRUCTIONS dict has keys: email, document, calendar, browser
  - CROWN_INSTRUCTIONS["email"] contains "hallucination"
  - CROWN_INSTRUCTIONS["document"] contains "hallucination"
  - build_browser_comprehension with real PageRecord (mock data)
  - build_calendar_comprehension with 0 events mentions sync
  - build_comprehension with empty list returns 0 total
  - DocumentComprehension with no key_points still formats correctly
  - BrowserComprehension search mode formats differently than page mode

Update test_identity.py: CURRENT_PHASE assertion.

---

## Permitted file changes

inanna/core/browser_workflows.py       <- MODIFY: add BrowserComprehension,
                                           build_browser_comprehension,
                                           update read_page/search_web
inanna/ui/server.py                    <- MODIFY: unified comprehension dispatch,
                                           CROWN_INSTRUCTIONS dict,
                                           store comprehension in result.data
inanna/main.py                         <- MODIFY: store comprehension in tool
                                           execution result data
inanna/identity.py                     <- MODIFY: CURRENT_PHASE
inanna/tests/test_comprehension_layer.py <- NEW
inanna/tests/test_identity.py          <- MODIFY

---

## What You Are NOT Building

- No new comprehension classes for process/filesystem/network
  (these return simple data that doesn't need structuring)
- No LLM-based summarisation (all deterministic)
- No changes to email comprehension (already working)
- No changes to constitutional_filter.py or nammu_profile.py
- No changes to tools.json or NixOS configs

---

## Critical Constraints

1. ALL comprehension is deterministic — no LLM calls
   The comprehension layer runs synchronously in the server path.
   Any LLM-based summarisation is Cycle 10+ territory.

2. CROWN_INSTRUCTIONS must reference {summary} placeholder
   The tool_result_summary is always injected via .format(summary=...)

3. The existing email comprehension must NOT be broken
   The existing code at lines 3568-3581 works correctly.
   The refactor must produce identical behaviour for email.

4. result.data must carry comprehension objects
   server.py retrieves comprehension from result.data.
   If result.data doesn't have it, fallback to raw summary.
   Never crash — the fallback is always the generic handler.

5. to_crown_context() never raises
   Wrap all comprehension methods in try/except at the server.py
   call site. If comprehension fails, fall through to raw summary.

---

## Definition of Done

- [ ] BrowserComprehension and build_browser_comprehension in browser_workflows.py
- [ ] browser read_page() and search_web() return (record, comprehension) tuples
- [ ] server.py has unified comprehension dispatch for all 4 domains
- [ ] CROWN_INSTRUCTIONS dict with domain-specific prompts
- [ ] Document tool stores record + comprehension in result.data
- [ ] Calendar tools store cal_result + comprehension in result.data
- [ ] Browser tools store record + comprehension in result.data
- [ ] CURRENT_PHASE = "Cycle 9 - Phase 9.4 - The Comprehension Layer"
- [ ] All tests pass: py -3 -m unittest discover -s tests (>=698)
- [ ] Pushed as cycle9-phase4-complete

---

## Handoff

Commit: cycle9-phase4-complete
Push immediately to origin/main.
Report: docs/implementation/CYCLE9_PHASE4_REPORT.md

The report MUST include:
  - Confirmation all 4 domains have comprehension wired
  - Sample to_crown_context() output for each domain
  - Confirmation email comprehension unchanged
  - Note on which tools now pass comprehension objects through result.data

Stop. Do not begin Phase 9.5 without new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-22*
*Tools return raw data.*
*Comprehension turns raw data into meaning.*
*CROWN receives meaning, not raw data.*
*This is how INANNA stops inventing.*
*This is how INANNA starts understanding.*

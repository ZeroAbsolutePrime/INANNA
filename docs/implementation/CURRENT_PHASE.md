# CURRENT PHASE: Cycle 2 - Phase 6 - The Bounded Tool
**Status: ACTIVE**
**Authorized by: ZAERA (Guardian) + Claude (Command Center)**
**Date opened: 2026-04-19**
**Cycle: 2 - The NAMMU Kernel**
**Replaces: Cycle 2 Phase 5 - The Governed Route (COMPLETE)**

---

## What This Phase Is

Phase 2.5 gave INANNA governance over routing decisions. The system
now has: intent classification (NAMMU), Faculty routing, and deterministic
governance checking. The architecture mediates before the model speaks.

Phase 2.6 introduces the first tool use - bounded, governed, and explicit.

In the Architecture Horizon, the Operator Faculty is described as:
"code and tool execution planning." In this phase, we build the
simplest possible form of that: a single tool that INANNA can invoke
when the user asks a question that requires a real-world lookup.

The tool is: web_search

But unlike a raw web search, this tool is governed:
- INANNA proposes using the tool before invoking it
- The user approves or rejects the proposal
- Only after approval does the tool execute
- The result is shown transparently before INANNA summarizes it

This is Law 1 (proposal before change) applied to tool use.
A search is a change to the information state of the session.
It must be proposed, not assumed.

---

## The Operator Faculty - Phase 2.6 Scope

The Operator Faculty in this phase is a lightweight tool executor.
It does not have its own LLM call. It executes a bounded set of
approved tools and returns structured results.

Tools available in Phase 2.6: one only - web_search via DuckDuckGo
(no API key required, uses the public DDG instant answer API).

---

## What You Are Building

### Task 1 - inanna/core/operator.py

Create a new file: inanna/core/operator.py

```python
from __future__ import annotations
import urllib.request
import urllib.parse
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    tool: str
    query: str
    success: bool
    data: dict[str, Any]
    error: str = ""


class OperatorFaculty:
    PERMITTED_TOOLS = {"web_search"}

    def execute(self, tool: str, params: dict[str, Any]) -> ToolResult:
        if tool not in self.PERMITTED_TOOLS:
            return ToolResult(
                tool=tool, query="",
                success=False, data={},
                error=f"Tool '{tool}' is not in the permitted tool set.",
            )
        if tool == "web_search":
            return self._web_search(params.get("query", ""))
        return ToolResult(tool=tool, query="", success=False, data={},
                          error="Unknown tool.")

    def _web_search(self, query: str) -> ToolResult:
        if not query.strip():
            return ToolResult(tool="web_search", query=query,
                              success=False, data={},
                              error="Empty search query.")
        try:
            encoded = urllib.parse.quote_plus(query)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "INANNA-NYX/1.0")
            with urllib.request.urlopen(req, timeout=8) as r:
                body = json.loads(r.read().decode("utf-8"))
            results = {
                "abstract": body.get("Abstract", ""),
                "abstract_source": body.get("AbstractSource", ""),
                "abstract_url": body.get("AbstractURL", ""),
                "answer": body.get("Answer", ""),
                "answer_type": body.get("AnswerType", ""),
                "related": [
                    {"text": t.get("Text", ""), "url": t.get("FirstURL", "")}
                    for t in body.get("RelatedTopics", [])[:3]
                    if isinstance(t, dict) and t.get("Text")
                ],
            }
            return ToolResult(tool="web_search", query=query,
                              success=True, data=results)
        except Exception as e:
            return ToolResult(tool="web_search", query=query,
                              success=False, data={}, error=str(e))
```

### Task 2 - Tool detection in governance.py

Add tool intent detection to GovernanceLayer.

When the input signals a need for current information that INANNA
cannot have from memory alone, Governance sets a flag:
suggests_tool=True in GovernanceResult.

Add suggests_tool: bool = False to GovernanceResult dataclass.

Add TOOL_SIGNALS list to governance.py:
```python
TOOL_SIGNALS = [
    "search for", "look up", "find out", "what is the latest",
    "current news", "today's", "right now", "what happened",
    "recent", "latest news", "search the web", "look it up",
]
```

When a tool signal is detected AND decision is "allow":
- Set suggests_tool=True
- Set proposed_tool="web_search"
- Set tool_query=<extracted query or full input>

Add to GovernanceResult:
```python
suggests_tool: bool = False
proposed_tool: str = ""
tool_query: str = ""
```

### Task 3 - Tool proposal flow in main.py

When GovernanceResult.suggests_tool is True, instead of calling
any Faculty directly, create a tool proposal:

```
[TOOL PROPOSAL] {timestamp} | Use web_search for: {query} | status: pending
```

Show the user:
```
operator > tool proposed: web_search — "{query}"
Type "approve" to execute or "reject" to cancel.
```

When approved:
1. Execute OperatorFaculty.execute("web_search", {"query": query})
2. Show raw results:
   ```
   operator > search result:
     Abstract: {abstract}
     Answer: {answer}
     Related: {related[0].text}
   ```
3. Then call Engine.respond() with the search result injected into context
4. Show INANNA's response normally: inanna > ...

When rejected:
- Show: operator > tool use rejected. Proceeding without search.
- Call Engine.respond() normally without search result

Tool proposals use the existing Proposal system with what="web_search tool use"

### Task 4 - OperatorFaculty in the UI server

Update ui/server.py to instantiate OperatorFaculty.

When GovernanceResult.suggests_tool is True, broadcast:
{"type": "operator", "text": "tool proposed: web_search — query"}

Add handling for tool approval flow:
When user approves a pending tool proposal (proposal with
action="tool_use"), execute the tool and inject results.

Broadcast tool results as:
{"type": "operator", "text": "search result:\n  Abstract: ...\n  Answer: ..."}

### Task 5 - Operator message rendering in index.html

Add CSS for operator messages:

```css
.message-operator .message-prefix,
.message-operator .message-content {
    color: #7a8a6a;  /* muted olive - technical, distinct */
    font-size: 0.88rem;
}
```

Prefix: "operator :"

### Task 6 - Update identity.py

Add the permitted tools list as a constitutional record:

```python
PERMITTED_TOOLS = ["web_search"]

def list_permitted_tools() -> list[str]:
    return PERMITTED_TOOLS
```

Update CURRENT_PHASE:
```python
CURRENT_PHASE = "Cycle 2 - Phase 6 - The Bounded Tool"
```

### Task 7 - Tests

Create inanna/tests/test_operator.py:
- OperatorFaculty.execute() with unknown tool returns success=False
- OperatorFaculty.execute() with empty query returns success=False
- OperatorFaculty only permits tools in PERMITTED_TOOLS
- ToolResult is a dataclass with expected fields

Update test_governance.py:
- GovernanceResult has suggests_tool field
- Tool signal input sets suggests_tool=True

Update test_identity.py:
- list_permitted_tools() returns list with "web_search"
- Update CURRENT_PHASE assertion

---

## Permitted file changes

```
inanna/
  identity.py              <- MODIFY: add PERMITTED_TOOLS,
                                      list_permitted_tools(),
                                      update CURRENT_PHASE
  config.py                <- no changes
  main.py                  <- MODIFY: handle suggests_tool in route result,
                                      tool proposal flow, approve/reject tool
  core/
    session.py             <- no changes
    memory.py              <- no changes
    proposal.py            <- no changes
    state.py               <- no changes
    nammu.py               <- no changes
    governance.py          <- MODIFY: add suggests_tool to GovernanceResult,
                                      add TOOL_SIGNALS detection
    operator.py            <- NEW: OperatorFaculty, ToolResult
  ui/
    server.py              <- MODIFY: instantiate OperatorFaculty,
                                      handle tool proposals and results
    static/
      index.html           <- MODIFY: add operator message styling
  tests/
    test_operator.py       <- NEW: OperatorFaculty tests
    test_governance.py     <- MODIFY: add suggests_tool tests
    test_identity.py       <- MODIFY: add permitted tools test, update phase
    (all others)           <- no changes
```

---

## What You Are NOT Building in This Phase

- No automatic tool execution without user approval
- No tool chaining or sequential tool calls
- No additional tools beyond web_search
- No persistent tool use log (in-memory only for this phase)
- No change to Faculty LLM calls except injecting search results
- No change to memory, proposal storage, or session storage beyond
  the tool proposal entry
- Do not add tool signals to the analyse direct override path

---

## Definition of Done for Phase 2.6

- [ ] inanna/core/operator.py exists with OperatorFaculty and ToolResult
- [ ] web_search tool executes via DuckDuckGo API
- [ ] Tool signals in input trigger a tool proposal
- [ ] User must approve before tool executes
- [ ] Tool results shown transparently before INANNA summarizes
- [ ] operator messages appear in muted olive color in UI
- [ ] list_permitted_tools() exists in identity.py
- [ ] CURRENT_PHASE updated
- [ ] All tests pass: py -3 -m unittest discover -s tests

---

## Handoff to Command Center

When Definition of Done is met, Codex must:
1. Commit with message: cycle2-phase6-complete
2. Write docs/implementation/CYCLE2_PHASE6_REPORT.md
3. Stop. Do not begin Phase 2.7 without a new CURRENT_PHASE.md.

---

*Written by: Claude (Command Center)*
*Guardian approval: ZAERA*
*Date: 2026-04-19*
*The tool is bounded. The proposal is required.*
*INANNA does not search the world without asking first.*

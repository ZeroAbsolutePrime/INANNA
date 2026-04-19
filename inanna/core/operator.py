from __future__ import annotations

import json
import urllib.parse
import urllib.request
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
                tool=tool,
                query="",
                success=False,
                data={},
                error=f"Tool '{tool}' is not in the permitted tool set.",
            )
        if tool == "web_search":
            return self._web_search(params.get("query", ""))
        return ToolResult(tool=tool, query="", success=False, data={}, error="Unknown tool.")

    def _web_search(self, query: str) -> ToolResult:
        if not query.strip():
            return ToolResult(
                tool="web_search",
                query=query,
                success=False,
                data={},
                error="Empty search query.",
            )
        try:
            encoded = urllib.parse.quote_plus(query)
            url = (
                "https://api.duckduckgo.com/"
                f"?q={encoded}&format=json&no_html=1&skip_disambig=1"
            )
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "INANNA-NYX/1.0")
            with urllib.request.urlopen(req, timeout=8) as response:
                body = json.loads(response.read().decode("utf-8"))
            results = {
                "abstract": body.get("Abstract", ""),
                "abstract_source": body.get("AbstractSource", ""),
                "abstract_url": body.get("AbstractURL", ""),
                "answer": body.get("Answer", ""),
                "answer_type": body.get("AnswerType", ""),
                "related": [
                    {"text": topic.get("Text", ""), "url": topic.get("FirstURL", "")}
                    for topic in body.get("RelatedTopics", [])[:3]
                    if isinstance(topic, dict) and topic.get("Text")
                ],
            }
            return ToolResult(
                tool="web_search",
                query=query,
                success=True,
                data=results,
            )
        except Exception as error:
            return ToolResult(
                tool="web_search",
                query=query,
                success=False,
                data={},
                error=str(error),
            )

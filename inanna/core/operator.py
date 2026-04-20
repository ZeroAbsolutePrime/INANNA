from __future__ import annotations

import json
import platform
import re
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOOLS_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "tools.json"


@dataclass
class ToolResult:
    tool: str
    query: str
    success: bool
    data: dict[str, Any]
    error: str = ""


class OperatorFaculty:
    def __init__(self, tools_path: Path = TOOLS_CONFIG_PATH) -> None:
        self.tools_path = tools_path
        self._tools = self._load_tools(tools_path)

    def _load_tools(self, tools_path: Path) -> dict[str, dict[str, Any]]:
        if not tools_path.exists():
            return {}
        try:
            payload = json.loads(tools_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

        raw_tools = payload.get("tools", {})
        if not isinstance(raw_tools, dict):
            return {}

        tools: dict[str, dict[str, Any]] = {}
        for name, config in raw_tools.items():
            if not isinstance(name, str) or not isinstance(config, dict):
                continue
            parameters = config.get("parameters", [])
            tools[name] = {
                "display_name": str(config.get("display_name", "")).strip() or name,
                "description": str(config.get("description", "")).strip(),
                "category": str(config.get("category", "")).strip() or "general",
                "requires_approval": bool(config.get("requires_approval", False)),
                "requires_privilege": str(config.get("requires_privilege", "")).strip(),
                "parameters": [
                    parameter for parameter in parameters if isinstance(parameter, str)
                ]
                if isinstance(parameters, list)
                else [],
                "enabled": bool(config.get("enabled", False)),
            }
        return tools

    @property
    def PERMITTED_TOOLS(self) -> set[str]:
        return {
            name
            for name, definition in self._tools.items()
            if bool(definition.get("enabled", False))
        }

    def list_tools(self) -> list[dict[str, Any]]:
        records = []
        for name, definition in self._tools.items():
            records.append({"name": name, **definition})
        return sorted(records, key=lambda record: (record["category"], record["name"]))

    def get_tool_definition(self, tool: str) -> dict[str, Any] | None:
        return self._tools.get(tool)

    def execute(self, tool: str, params: dict[str, Any]) -> ToolResult:
        tool_name = str(tool or "").strip()
        if tool_name not in self.PERMITTED_TOOLS:
            return ToolResult(
                tool=tool_name,
                query="",
                success=False,
                data={},
                error=f"Tool '{tool_name}' is not in the permitted tool set.",
            )
        if tool_name == "web_search":
            return self._web_search(params.get("query", ""))
        if tool_name == "ping":
            host = str(params.get("host") or params.get("query", ""))
            return self._ping(host)
        return ToolResult(tool=tool_name, query="", success=False, data={}, error="Unknown tool.")

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

    def _ping(self, host: str) -> ToolResult:
        target = str(host or "").strip()
        if not target:
            return ToolResult(
                tool="ping",
                query=host,
                success=False,
                data={},
                error="Empty host.",
            )
        try:
            ping_flag = "-n" if platform.system().lower() == "windows" else "-c"
            result = subprocess.run(
                ["ping", ping_flag, "3", target],
                capture_output=True,
                text=True,
                timeout=10,
            )
            success = result.returncode == 0
            output = result.stdout if result.stdout.strip() else result.stderr
            latency = None
            if platform.system().lower() == "windows":
                match = re.search(r"Average = (\d+)ms", output)
            else:
                match = re.search(r"=\s*[\d.]+/([\d.]+)/", output)
            if match:
                latency = float(match.group(1))
            return ToolResult(
                tool="ping",
                query=target,
                success=success,
                data={
                    "host": target,
                    "reachable": success,
                    "latency_ms": latency,
                    "output": output[:500],
                },
                error="" if success else output[:200],
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                tool="ping",
                query=target,
                success=False,
                data={},
                error="Ping timed out.",
            )
        except Exception as error:
            return ToolResult(
                tool="ping",
                query=target,
                success=False,
                data={},
                error=str(error),
            )

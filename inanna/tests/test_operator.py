from __future__ import annotations

import dataclasses
import unittest
from unittest.mock import Mock, patch

from core.operator import OperatorFaculty, ToolResult


class OperatorFacultyTests(unittest.TestCase):
    def test_operator_loads_tools_from_config(self) -> None:
        operator = OperatorFaculty()

        self.assertEqual(operator.PERMITTED_TOOLS, {"web_search", "ping"})
        self.assertEqual(
            operator.get_tool_definition("ping"),
            {
                "display_name": "Ping Host",
                "description": "Check network connectivity to a hostname or IP address.",
                "category": "network",
                "requires_approval": True,
                "requires_privilege": "network_tools",
                "parameters": ["host"],
                "enabled": True,
            },
        )

    def test_unknown_tool_returns_unsuccessful_result(self) -> None:
        result = OperatorFaculty().execute("not_a_tool", {})

        self.assertFalse(result.success)

    def test_empty_query_returns_unsuccessful_result(self) -> None:
        result = OperatorFaculty().execute("web_search", {"query": ""})

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Empty search query.")

    def test_ping_empty_host_returns_unsuccessful_result(self) -> None:
        result = OperatorFaculty().execute("ping", {"host": ""})

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Empty host.")

    def test_ping_execution_returns_tool_result(self) -> None:
        run_result = Mock(
            returncode=0,
            stdout="Ping statistics for 127.0.0.1:\nAverage = 12ms",
            stderr="",
        )
        with patch("core.operator.platform.system", return_value="Windows"), patch(
            "core.operator.subprocess.run",
            return_value=run_result,
        ) as run_mock:
            result = OperatorFaculty().execute("ping", {"host": "127.0.0.1"})

        self.assertTrue(result.success)
        self.assertEqual(result.tool, "ping")
        self.assertEqual(result.query, "127.0.0.1")
        self.assertEqual(result.data["host"], "127.0.0.1")
        self.assertEqual(result.data["latency_ms"], 12.0)
        run_mock.assert_called_once_with(
            ["ping", "-n", "3", "127.0.0.1"],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_tool_result_is_dataclass_with_expected_fields(self) -> None:
        field_names = [field.name for field in dataclasses.fields(ToolResult)]

        self.assertEqual(
            field_names,
            ["tool", "query", "success", "data", "error"],
        )


if __name__ == "__main__":
    unittest.main()

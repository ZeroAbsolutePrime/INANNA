from __future__ import annotations

import dataclasses
import unittest

from core.operator import OperatorFaculty, ToolResult


class OperatorFacultyTests(unittest.TestCase):
    def test_unknown_tool_returns_unsuccessful_result(self) -> None:
        result = OperatorFaculty().execute("not_a_tool", {})

        self.assertFalse(result.success)

    def test_empty_query_returns_unsuccessful_result(self) -> None:
        result = OperatorFaculty().execute("web_search", {"query": ""})

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Empty search query.")

    def test_only_permitted_tools_are_available(self) -> None:
        self.assertEqual(OperatorFaculty.PERMITTED_TOOLS, {"web_search"})

    def test_tool_result_is_dataclass_with_expected_fields(self) -> None:
        field_names = [field.name for field in dataclasses.fields(ToolResult)]

        self.assertEqual(
            field_names,
            ["tool", "query", "success", "data", "error"],
        )


if __name__ == "__main__":
    unittest.main()

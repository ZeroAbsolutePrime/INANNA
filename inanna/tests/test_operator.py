from __future__ import annotations

import dataclasses
import unittest
from unittest.mock import MagicMock, Mock, patch

from core.operator import OperatorFaculty, ToolResult


class OperatorFacultyTests(unittest.TestCase):
    def test_operator_loads_tools_from_config(self) -> None:
        operator = OperatorFaculty()

        self.assertEqual(
            operator.PERMITTED_TOOLS,
            {
                "web_search",
                "ping",
                "resolve_host",
                "scan_ports",
                "read_file",
                "list_dir",
                "file_info",
                "search_files",
                "write_file",
                "list_processes",
                "system_info",
                "kill_process",
                "run_command",
                "search_packages",
                "list_packages",
                "install_package",
                "remove_package",
                "launch_app",
                "desktop_open_app",
                "desktop_read_window",
                "desktop_click",
                "desktop_type",
                "desktop_screenshot",
            },
        )
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
        self.assertEqual(
            operator.get_tool_definition("resolve_host"),
            {
                "display_name": "Resolve Host",
                "description": "Resolve a hostname to its IP address and FQDN.",
                "category": "network",
                "requires_approval": True,
                "requires_privilege": "network_tools",
                "parameters": ["host"],
                "enabled": True,
            },
        )
        self.assertEqual(
            operator.get_tool_definition("read_file"),
            {
                "display_name": "Read File",
                "description": "Read the contents of a file. Safe paths may skip proposal approval.",
                "category": "filesystem",
                "requires_approval": True,
                "requires_privilege": "converse",
                "parameters": ["path"],
                "enabled": True,
            },
        )
        self.assertEqual(
            operator.get_tool_definition("list_processes"),
            {
                "display_name": "List Processes",
                "description": "List running processes sorted by memory or CPU.",
                "category": "process",
                "requires_approval": False,
                "requires_privilege": "converse",
                "parameters": ["filter", "sort", "limit"],
                "enabled": True,
            },
        )
        self.assertEqual(
            operator.get_tool_definition("search_packages"),
            {
                "display_name": "Search Packages",
                "description": "Search for available packages to install.",
                "category": "package",
                "requires_approval": False,
                "requires_privilege": "converse",
                "parameters": ["query"],
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

    def test_resolve_host_returns_ip_and_fqdn(self) -> None:
        with patch("core.operator.socket.gethostbyname", return_value="127.0.0.1"), patch(
            "core.operator.socket.getfqdn",
            return_value="localhost",
        ):
            result = OperatorFaculty().execute("resolve_host", {"host": "localhost"})

        self.assertTrue(result.success)
        self.assertEqual(result.data["ip"], "127.0.0.1")
        self.assertEqual(result.data["fqdn"], "localhost")

    def test_resolve_host_empty_host_returns_unsuccessful_result(self) -> None:
        result = OperatorFaculty().execute("resolve_host", {"host": ""})

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Empty host.")

    def test_scan_ports_returns_successful_result(self) -> None:
        fake_socket = MagicMock()
        fake_socket.__enter__.return_value = fake_socket
        fake_socket.__exit__.return_value = False
        with patch("core.operator.socket.create_connection", return_value=fake_socket):
            result = OperatorFaculty().execute(
                "scan_ports",
                {"host": "127.0.0.1", "port_range": "80-80"},
            )

        self.assertTrue(result.success)
        self.assertEqual(result.data["host"], "127.0.0.1")
        self.assertEqual(result.data["port_range"], "80")
        self.assertEqual(result.data["open_ports"], [80])
        self.assertEqual(result.data["scanned"], 1)

    def test_scan_ports_empty_host_returns_unsuccessful_result(self) -> None:
        result = OperatorFaculty().execute("scan_ports", {"host": "", "port_range": "80-80"})

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Empty host.")

    def test_scan_ports_caps_range_to_one_hundred_ports(self) -> None:
        with patch(
            "core.operator.socket.create_connection",
            side_effect=OSError("closed"),
        ) as create_connection:
            result = OperatorFaculty().execute(
                "scan_ports",
                {"host": "127.0.0.1", "port_range": "80-500"},
            )

        self.assertTrue(result.success)
        self.assertEqual(result.data["port_range"], "80-179")
        self.assertEqual(result.data["scanned"], 100)
        self.assertEqual(create_connection.call_count, 100)

    def test_should_skip_proposal_returns_true_for_persistently_trusted_tool(self) -> None:
        operator = OperatorFaculty()

        should_skip = operator.should_skip_proposal("web_search", ["web_search"])

        self.assertTrue(should_skip)

    def test_should_skip_proposal_returns_false_for_untrusted_tool(self) -> None:
        operator = OperatorFaculty()

        should_skip = operator.should_skip_proposal("resolve_host", ["web_search"])

        self.assertFalse(should_skip)

    def test_should_skip_proposal_returns_false_for_unknown_tool(self) -> None:
        operator = OperatorFaculty()

        should_skip = operator.should_skip_proposal("not_a_tool", ["not_a_tool"])

        self.assertFalse(should_skip)

    def test_tool_result_is_dataclass_with_expected_fields(self) -> None:
        field_names = [field.name for field in dataclasses.fields(ToolResult)]

        self.assertEqual(
            field_names,
            ["tool", "query", "success", "data", "error"],
        )


if __name__ == "__main__":
    unittest.main()

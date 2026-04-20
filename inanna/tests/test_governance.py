from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from core.governance import GovernanceLayer, GovernanceResult


class FakeGovernanceEngine:
    def __init__(self, response: str, connected: bool = True) -> None:
        self.response = response
        self._connected = connected

    def _call_openai_compatible(self, messages) -> str:
        del messages
        return self.response


def signal_list(value: str | None = None) -> list[str]:
    if value is None:
        return []
    return [value]


def signal_payload(
    *,
    memory_signal: str | None = None,
    identity_signal: str | None = None,
    sensitive_signal: str | None = None,
    tool_signal: str | None = None,
    analyst_signal: str | None = None,
) -> dict[str, list[str]]:
    return {
        "memory_signals": signal_list(memory_signal),
        "identity_signals": signal_list(identity_signal),
        "sensitive_signals": signal_list(sensitive_signal),
        "tool_signals": signal_list(tool_signal),
        "analyst_signals": signal_list(analyst_signal),
    }


class GovernanceLayerTests(unittest.TestCase):
    def write_config(self, root: Path, payload: dict) -> Path:
        config_path = root / "governance_signals.json"
        config_path.write_text(json.dumps(payload), encoding="utf-8")
        return config_path

    def test_check_returns_governance_result(self) -> None:
        result = GovernanceLayer().check("hello", "crown")

        self.assertIsInstance(result, GovernanceResult)
        self.assertFalse(result.suggests_tool)

    def test_governance_layer_loads_signals_from_config_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            memory_signal = f"memory-{uuid4().hex}"
            tool_signal = f"tool-{uuid4().hex}"
            config_path = self.write_config(
                Path(temp_dir),
                signal_payload(
                    memory_signal=memory_signal,
                    identity_signal=f"identity-{uuid4().hex}",
                    sensitive_signal=f"sensitive-{uuid4().hex}",
                    tool_signal=tool_signal,
                    analyst_signal=f"analyst-{uuid4().hex}",
                ),
            )

            governance = GovernanceLayer(config_path=config_path)

            self.assertEqual(governance.memory_signals, [memory_signal])
            self.assertEqual(governance.tool_signals, [tool_signal])

    def test_missing_config_returns_empty_signals_safely(self) -> None:
        governance = GovernanceLayer(config_path=Path("C:/tmp/does-not-exist.json"))

        self.assertEqual(governance.memory_signals, [])
        self.assertEqual(governance.identity_signals, [])
        self.assertEqual(governance.check("hello there", "crown").decision, "allow")

    def test_signal_matching_works_via_loaded_config(self) -> None:
        with TemporaryDirectory() as temp_dir:
            memory_signal = f"memory-{uuid4().hex}"
            sensitive_signal = f"sensitive-{uuid4().hex}"
            tool_signal = f"tool-{uuid4().hex}"
            config_path = self.write_config(
                Path(temp_dir),
                signal_payload(
                    memory_signal=memory_signal,
                    identity_signal=f"identity-{uuid4().hex}",
                    sensitive_signal=sensitive_signal,
                    tool_signal=tool_signal,
                    analyst_signal=f"analyst-{uuid4().hex}",
                ),
            )
            governance = GovernanceLayer(config_path=config_path)

            self.assertEqual(
                governance.check(f"por favor {memory_signal} esto", "crown").decision,
                "propose",
            )
            self.assertEqual(
                governance.check(f"esta es una {sensitive_signal}", "crown").decision,
                "redirect",
            )
            self.assertTrue(
                governance.check(f"{tool_signal} del clima", "crown").suggests_tool
            )

    def test_model_classification_is_primary_path(self) -> None:
        governance = GovernanceLayer(
            config_path=Path("C:/tmp/does-not-exist.json"),
            engine=FakeGovernanceEngine("MEMORY"),
        )

        result = governance.check("hello there", "crown")

        self.assertEqual(result.decision, "propose")
        self.assertTrue(result.requires_proposal)

    def test_governance_result_exposes_suggests_tool_field(self) -> None:
        result = GovernanceLayer().check("hello", "crown")

        self.assertTrue(hasattr(result, "suggests_tool"))

    def test_tool_signal_sets_suggests_tool_true(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tool_signal = f"tool-{uuid4().hex}"
            config_path = self.write_config(
                Path(temp_dir),
                signal_payload(tool_signal=tool_signal),
            )
            result = GovernanceLayer(config_path=config_path).check(
                f"{tool_signal} del espacio",
                "crown",
            )

            self.assertTrue(result.suggests_tool)
            self.assertEqual(result.proposed_tool, "web_search")
            self.assertTrue(result.tool_query)

    def test_ping_signal_sets_ping_tool(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = self.write_config(
                Path(temp_dir),
                signal_payload(tool_signal="ping "),
            )
            result = GovernanceLayer(config_path=config_path).check(
                "ping 127.0.0.1",
                "crown",
            )

            self.assertTrue(result.suggests_tool)
            self.assertEqual(result.proposed_tool, "ping")
            self.assertEqual(result.tool_query, "127.0.0.1")

    def test_resolve_signal_sets_resolve_host_tool(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = self.write_config(
                Path(temp_dir),
                signal_payload(tool_signal="resolve host"),
            )
            result = GovernanceLayer(config_path=config_path).check(
                "resolve host localhost",
                "crown",
            )

            self.assertTrue(result.suggests_tool)
            self.assertEqual(result.proposed_tool, "resolve_host")
            self.assertEqual(result.tool_query, "localhost")

    def test_scan_signal_sets_scan_ports_tool(self) -> None:
        with TemporaryDirectory() as temp_dir:
            config_path = self.write_config(
                Path(temp_dir),
                signal_payload(tool_signal="scan ports"),
            )
            result = GovernanceLayer(config_path=config_path).check(
                "scan ports localhost 22-80",
                "crown",
            )

            self.assertTrue(result.suggests_tool)
            self.assertEqual(result.proposed_tool, "scan_ports")
            self.assertEqual(result.tool_query, "localhost 22-80")


if __name__ == "__main__":
    unittest.main()

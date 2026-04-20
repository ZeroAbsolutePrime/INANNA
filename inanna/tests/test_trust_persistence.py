from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.governance import GovernanceResult
from core.operator import ToolResult
import ui.server as ui_server


ROLES_PAYLOAD = {
    "roles": {
        "guardian": {
            "description": "Full system access - assigned directly only",
            "privileges": ["all"],
        },
        "operator": {
            "description": "Realm-scoped admin",
            "privileges": [
                "manage_users_in_realm",
                "approve_proposals_in_realm",
                "read_realm_audit_log",
                "invite_users",
            ],
        },
        "user": {
            "description": "Standard interaction",
            "privileges": [
                "converse",
                "approve_own_memory",
                "read_own_log",
                "forget_own_memory",
            ],
        },
    }
}


def write_roles_config(app_root: Path) -> None:
    config_dir = app_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "roles.json").write_text(
        json.dumps(ROLES_PAYLOAD, indent=2),
        encoding="utf-8",
    )


class TrustPersistenceServerTests(unittest.TestCase):
    def test_server_process_command_grants_persistent_trust(self) -> None:
        with TemporaryDirectory() as temp_dir:
            original_app_root = ui_server.APP_ROOT
            try:
                ui_server.APP_ROOT = Path(temp_dir)
                write_roles_config(ui_server.APP_ROOT)
                server = ui_server.InterfaceServer()
                messages: list[dict[str, object]] = []

                async def fake_broadcast(payload: dict[str, object]) -> None:
                    messages.append(payload)

                async def fake_broadcast_state() -> None:
                    return None

                server.broadcast = fake_broadcast  # type: ignore[method-assign]
                server.broadcast_state = fake_broadcast_state  # type: ignore[method-assign]

                asyncio.run(
                    server.process_command(
                        "governance-trust web_search",
                        {"_raw_cmd": "governance-trust web_search"},
                    )
                )

                profile = server.profile_manager.load(server.active_user.user_id)
                self.assertIsNotNone(profile)
                self.assertEqual(profile.persistent_trusted_tools, ["web_search"])
                self.assertEqual(
                    messages[0]["text"],
                    "governance > web_search is now persistently trusted for you.",
                )
            finally:
                ui_server.APP_ROOT = original_app_root

    def test_run_routed_turn_executes_trusted_tool_without_proposal(self) -> None:
        with TemporaryDirectory() as temp_dir:
            original_app_root = ui_server.APP_ROOT
            try:
                ui_server.APP_ROOT = Path(temp_dir)
                write_roles_config(ui_server.APP_ROOT)
                server = ui_server.InterfaceServer()
                server.profile_manager.update_field(
                    server.active_user.user_id,
                    "persistent_trusted_tools",
                    ["web_search"],
                )

                with patch.object(
                    server.classifier,
                    "route",
                    return_value=GovernanceResult(
                        decision="allow",
                        faculty="crown",
                        reason="current information requires web search",
                        suggests_tool=True,
                        proposed_tool="web_search",
                        tool_query="latest weather",
                    ),
                ), patch.object(
                    server.operator,
                    "execute",
                    return_value=ToolResult(
                        tool="web_search",
                        query="latest weather",
                        success=True,
                        data={
                            "abstract": "Current result abstract",
                            "answer": "Current result answer",
                            "related": [],
                        },
                    ),
                ), patch.object(server.engine, "respond", return_value="Summary ready."):
                    outcome = server._run_routed_turn("what is the weather today")

                self.assertNotIn("proposal", outcome)
                self.assertIn("responses", outcome)
                self.assertEqual(outcome["responses"][0]["type"], "operator")
                self.assertIn("search result:", outcome["responses"][0]["text"])
                self.assertEqual(outcome["responses"][-1]["type"], "assistant")
                self.assertTrue(
                    any(
                        event.get("event_type") == "tool_executed_trusted"
                        for event in server.session_audit
                    )
                )
            finally:
                ui_server.APP_ROOT = original_app_root


if __name__ == "__main__":
    unittest.main()

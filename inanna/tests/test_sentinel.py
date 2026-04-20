from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.session import Engine
from main import build_sentinel_system_prompt, run_sentinel_response


def sentinel_faculties_payload() -> dict[str, object]:
    return {
        "faculties": {
            "sentinel": {
                "display_name": "SENTINEL",
                "domain": "security",
                "description": "Cybersecurity analysis",
                "charter_preview": (
                    "I am SENTINEL. I analyze security posture. I reason about "
                    "threats and vulnerabilities."
                ),
                "governance_rules": [
                    "Passive analysis only without explicit Guardian approval",
                    "All offensive actions require Guardian proposal",
                    "Never recommend exploiting a vulnerability without consent",
                ],
                "active": True,
                "built_in": False,
                "color": "danger",
            }
        }
    }


class SentinelResponseTests(unittest.TestCase):
    def make_faculties_path(self, temp_dir: str) -> Path:
        faculties_path = Path(temp_dir) / "faculties.json"
        faculties_path.write_text(
            json.dumps(sentinel_faculties_payload(), indent=2),
            encoding="utf-8",
        )
        return faculties_path

    def test_run_sentinel_response_can_be_called_without_error(self) -> None:
        with TemporaryDirectory() as temp_dir:
            faculties_path = self.make_faculties_path(temp_dir)
            with patch.object(
                Engine,
                "_call_openai_compatible",
                autospec=True,
                return_value="Use defensive controls and preserve evidence.",
            ) as call_mock:
                text = run_sentinel_response(
                    user_input="Check this firewall exposure.",
                    grounding=["user: operates a home lab"],
                    lm_url="http://localhost:1234/v1",
                    model_name="local-model",
                    faculties_path=faculties_path,
                )

        self.assertEqual(text, "Use defensive controls and preserve evidence.")
        self.assertEqual(call_mock.call_count, 1)

    def test_sentinel_system_prompt_contains_governance_rules(self) -> None:
        with TemporaryDirectory() as temp_dir:
            faculties_path = self.make_faculties_path(temp_dir)

            prompt = build_sentinel_system_prompt(
                grounding="From approved memory: the user manages an internal test lab.",
                faculties_path=faculties_path,
            )

        self.assertIn("Governance rules", prompt)
        self.assertIn("All offensive actions require Guardian proposal", prompt)

    def test_sentinel_system_prompt_contains_passive_analysis_only(self) -> None:
        with TemporaryDirectory() as temp_dir:
            faculties_path = self.make_faculties_path(temp_dir)

            prompt = build_sentinel_system_prompt(
                grounding="From approved memory: the user wants defensive guidance only.",
                faculties_path=faculties_path,
            )

        self.assertIn("passive analysis only", prompt.lower())


if __name__ == "__main__":
    unittest.main()

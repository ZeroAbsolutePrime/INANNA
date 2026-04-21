from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
NIXOS_DIR = REPO_ROOT / "nixos"
CONFIGURATION_PATH = NIXOS_DIR / "configuration.nix"
README_PATH = NIXOS_DIR / "README.md"
SERVICE_PATH = NIXOS_DIR / "inanna-nyx.service"
INSTALL_PATH = NIXOS_DIR / "install.sh"
REQUIREMENTS_PATH = REPO_ROOT / "inanna" / "requirements.txt"


class NixOSConfigTests(unittest.TestCase):
    def test_configuration_nix_exists(self) -> None:
        self.assertTrue(CONFIGURATION_PATH.exists())

    def test_nixos_readme_exists(self) -> None:
        self.assertTrue(README_PATH.exists())

    def test_systemd_service_exists(self) -> None:
        self.assertTrue(SERVICE_PATH.exists())

    def test_install_script_exists(self) -> None:
        self.assertTrue(INSTALL_PATH.exists())

    def test_requirements_txt_exists(self) -> None:
        self.assertTrue(REQUIREMENTS_PATH.exists())

    def test_configuration_contains_inanna_service_definition(self) -> None:
        content = CONFIGURATION_PATH.read_text(encoding="utf-8")
        self.assertIn("systemd.services.inanna-nyx", content)

    def test_configuration_contains_port_8080(self) -> None:
        content = CONFIGURATION_PATH.read_text(encoding="utf-8")
        self.assertIn("8080", content)

    def test_configuration_contains_port_8081(self) -> None:
        content = CONFIGURATION_PATH.read_text(encoding="utf-8")
        self.assertIn("8081", content)

    def test_requirements_contains_websockets(self) -> None:
        content = REQUIREMENTS_PATH.read_text(encoding="utf-8")
        self.assertIn("websockets", content)

    def test_service_contains_execstart(self) -> None:
        content = SERVICE_PATH.read_text(encoding="utf-8")
        self.assertIn("ExecStart=", content)


if __name__ == "__main__":
    unittest.main()

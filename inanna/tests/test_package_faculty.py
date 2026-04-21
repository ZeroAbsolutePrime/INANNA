from __future__ import annotations

import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from core.package_faculty import PackageFaculty, PackageRecord, PackageResult


class PackageFacultyTests(unittest.TestCase):
    def make_unknown_faculty(self) -> PackageFaculty:
        with patch.object(PackageFaculty, "_detect_package_manager", return_value="unknown"):
            return PackageFaculty()

    def test_package_faculty_instantiates(self) -> None:
        faculty = self.make_unknown_faculty()
        self.assertIsInstance(faculty, PackageFaculty)

    def test_detect_package_manager_returns_string(self) -> None:
        faculty = self.make_unknown_faculty()
        self.assertIsInstance(faculty.pm, str)

    def test_detect_package_manager_prefers_nix_on_nixos(self) -> None:
        with patch("core.package_faculty.platform.system", return_value="Linux"), patch(
            "core.package_faculty.Path.read_text",
            return_value="NAME=NixOS\nID=nixos\n",
        ):
            faculty = PackageFaculty()

        self.assertEqual("nix", faculty.pm)

    def test_detect_package_manager_uses_apt_on_debian_linux(self) -> None:
        def fake_which(command: str) -> str | None:
            if command in {"apt", "dpkg-query"}:
                return f"/usr/bin/{command}"
            return None

        with patch("core.package_faculty.platform.system", return_value="Linux"), patch(
            "core.package_faculty.Path.read_text",
            side_effect=OSError("missing"),
        ), patch("core.package_faculty.shutil.which", side_effect=fake_which):
            faculty = PackageFaculty()

        self.assertEqual("apt", faculty.pm)

    def test_detect_package_manager_uses_brew_on_macos(self) -> None:
        with patch("core.package_faculty.platform.system", return_value="Darwin"), patch(
            "core.package_faculty.shutil.which",
            side_effect=lambda command: "/opt/homebrew/bin/brew" if command == "brew" else None,
        ):
            faculty = PackageFaculty()

        self.assertEqual("brew", faculty.pm)

    def test_detect_package_manager_uses_winget_on_windows(self) -> None:
        with patch("core.package_faculty.platform.system", return_value="Windows"), patch(
            "core.package_faculty.shutil.which",
            side_effect=lambda command: "C:\\Windows\\System32\\winget.exe" if command == "winget" else None,
        ):
            faculty = PackageFaculty()

        self.assertEqual("winget", faculty.pm)

    def test_search_on_unknown_manager_returns_error(self) -> None:
        result = self.make_unknown_faculty().search("firefox")
        self.assertFalse(result.success)
        self.assertIn("No supported package manager", result.error or "")

    def test_list_installed_on_unknown_manager_returns_error(self) -> None:
        result = self.make_unknown_faculty().list_installed()
        self.assertFalse(result.success)
        self.assertIn("No supported package manager", result.error or "")

    def test_install_on_unknown_manager_returns_error(self) -> None:
        result = self.make_unknown_faculty().install("firefox")
        self.assertFalse(result.success)
        self.assertIn("No supported package manager", result.error or "")

    def test_remove_on_unknown_manager_returns_error(self) -> None:
        result = self.make_unknown_faculty().remove("firefox")
        self.assertFalse(result.success)
        self.assertIn("No supported package manager", result.error or "")

    def test_format_result_for_search_shows_package_name(self) -> None:
        faculty = self.make_unknown_faculty()
        result = PackageResult(
            success=True,
            operation="search",
            query="editor",
            records=[
                PackageRecord(
                    name="micro",
                    version="2.0.0",
                    description="terminal editor",
                    installed=False,
                )
            ],
            package_manager="apt",
        )
        formatted = faculty.format_result(result)
        self.assertIn("pkg [apt] > search: editor", formatted)
        self.assertIn("micro 2.0.0", formatted)

    def test_format_result_for_error_shows_pkg_error(self) -> None:
        faculty = self.make_unknown_faculty()
        result = PackageResult(
            success=False,
            operation="search",
            query="editor",
            error="broken",
            package_manager="unknown",
        )
        self.assertEqual("pkg [unknown] > error: broken", faculty.format_result(result))

    def test_format_result_for_install_includes_package_name(self) -> None:
        faculty = self.make_unknown_faculty()
        result = PackageResult(
            success=True,
            operation="install",
            query="firefox",
            output="Installed successfully.",
            package_manager="winget",
        )
        formatted = faculty.format_result(result)
        self.assertIn("installed: firefox", formatted)

    def test_format_result_for_remove_includes_package_name(self) -> None:
        faculty = self.make_unknown_faculty()
        result = PackageResult(
            success=True,
            operation="remove",
            query="firefox",
            output="Removed successfully.",
            package_manager="brew",
        )
        formatted = faculty.format_result(result)
        self.assertIn("removed: firefox", formatted)

    def test_run_handles_timeout(self) -> None:
        faculty = self.make_unknown_faculty()
        faculty.pm = "apt"
        with patch(
            "core.package_faculty.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["apt-cache"], timeout=60),
        ):
            result = faculty._run(["apt-cache", "search", "firefox"], "search", "firefox")
        self.assertFalse(result.success)
        self.assertIn("timed out", result.error or "")

    def test_run_handles_file_not_found(self) -> None:
        faculty = self.make_unknown_faculty()
        faculty.pm = "apt"
        with patch(
            "core.package_faculty.subprocess.run",
            side_effect=FileNotFoundError(),
        ):
            result = faculty._run(["apt-cache", "search", "firefox"], "search", "firefox")
        self.assertFalse(result.success)
        self.assertIn("not found", result.error or "")

    def test_run_success_returns_output(self) -> None:
        faculty = self.make_unknown_faculty()
        faculty.pm = "apt"
        completed = SimpleNamespace(returncode=0, stdout="firefox - browser\n", stderr="")
        with patch("core.package_faculty.subprocess.run", return_value=completed):
            result = faculty._run(["apt-cache", "search", "firefox"], "search", "firefox")
        self.assertTrue(result.success)
        self.assertIn("firefox", result.output)

    def test_search_dispatches_to_apt_search(self) -> None:
        faculty = self.make_unknown_faculty()
        faculty.pm = "apt"
        expected = PackageResult(True, "search", "editor", package_manager="apt")
        with patch.object(faculty, "_apt_search", return_value=expected) as search_mock:
            result = faculty.search("editor")
        search_mock.assert_called_once_with("editor")
        self.assertIs(result, expected)

    def test_list_installed_dispatches_to_winget_list(self) -> None:
        faculty = self.make_unknown_faculty()
        faculty.pm = "winget"
        expected = PackageResult(True, "list", "python", package_manager="winget")
        with patch.object(faculty, "_winget_list", return_value=expected) as list_mock:
            result = faculty.list_installed("python")
        list_mock.assert_called_once_with("python")
        self.assertIs(result, expected)

    def test_install_uses_brew_install_command(self) -> None:
        faculty = self.make_unknown_faculty()
        faculty.pm = "brew"
        expected = PackageResult(True, "install", "firefox", package_manager="brew")
        with patch.object(faculty, "_run", return_value=expected) as run_mock:
            result = faculty.install("firefox")
        run_mock.assert_called_once_with(
            ["brew", "install", "firefox"],
            "install",
            "firefox",
            timeout=120,
        )
        self.assertIs(result, expected)

    def test_remove_uses_nix_remove_command(self) -> None:
        faculty = self.make_unknown_faculty()
        faculty.pm = "nix"
        expected = PackageResult(True, "remove", "firefox", package_manager="nix")
        with patch.object(faculty, "_run", return_value=expected) as run_mock:
            result = faculty.remove("firefox")
        run_mock.assert_called_once_with(
            ["nix-env", "-e", "firefox"],
            "remove",
            "firefox",
            timeout=120,
        )
        self.assertIs(result, expected)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.desktop_faculty import (
    DesktopFaculty,
    FallbackBackend,
    LINUX_APP_NAME_MAP,
    LinuxAtspiBackend,
    WindowsMCPBackend,
)


class NixOSBackendTests(unittest.TestCase):
    def test_linux_backend_instantiates(self) -> None:
        self.assertIsInstance(LinuxAtspiBackend(), LinuxAtspiBackend)

    def test_linux_backend_name_is_linux_atspi2(self) -> None:
        self.assertEqual("linux-atspi2", LinuxAtspiBackend().name)

    def test_linux_open_app_handles_missing_binary(self) -> None:
        backend = LinuxAtspiBackend()
        with patch("core.desktop_faculty.subprocess.Popen", side_effect=FileNotFoundError("missing")):
            result = backend.open_app("firefox")

        self.assertFalse(result.success)
        self.assertIn("missing", result.error or "")

    def test_linux_type_text_handles_missing_input_tool(self) -> None:
        backend = LinuxAtspiBackend()
        with patch.object(backend, "_detect_display_server", return_value="x11"), patch(
            "core.desktop_faculty.subprocess.run",
            side_effect=FileNotFoundError("xdotool missing"),
        ):
            result = backend.type_text("hello")

        self.assertFalse(result.success)
        self.assertIn("xdotool missing", result.error or "")

    def test_linux_screenshot_handles_missing_scrot(self) -> None:
        backend = LinuxAtspiBackend()
        with patch("core.desktop_faculty.subprocess.run", side_effect=FileNotFoundError("scrot missing")):
            result = backend.screenshot()

        self.assertFalse(result.success)
        self.assertIn("scrot missing", result.error or "")

    def test_linux_read_window_returns_error_when_pyatspi_missing(self) -> None:
        backend = LinuxAtspiBackend()
        with patch.dict("sys.modules", {"pyatspi": None}):
            original_import = __import__

            def fake_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
                if name == "pyatspi":
                    raise ImportError("no pyatspi")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=fake_import):
                result = backend.read_window("thunderbird")

        self.assertFalse(result.success)
        self.assertIn("pyatspi", result.error or "")

    def test_linux_click_returns_error_when_pyatspi_missing(self) -> None:
        backend = LinuxAtspiBackend()
        original_import = __import__

        def fake_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
            if name == "pyatspi":
                raise ImportError("no pyatspi")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            result = backend.click("Send")

        self.assertFalse(result.success)
        self.assertIn("pyatspi", result.error or "")

    def test_detect_display_server_returns_wayland_when_wayland_display_set(self) -> None:
        backend = LinuxAtspiBackend()
        with patch.dict("os.environ", {"WAYLAND_DISPLAY": "wayland-0"}, clear=False):
            self.assertEqual("wayland", backend._detect_display_server())

    def test_detect_display_server_returns_x11_without_wayland(self) -> None:
        backend = LinuxAtspiBackend()
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual("x11", backend._detect_display_server())

    def test_linux_app_name_map_contains_thunderbird(self) -> None:
        self.assertIn("thunderbird", LINUX_APP_NAME_MAP)

    def test_linux_app_name_map_contains_firefox(self) -> None:
        self.assertIn("firefox", LINUX_APP_NAME_MAP)

    def test_linux_app_name_map_signal_points_to_signal_desktop(self) -> None:
        self.assertEqual("signal-desktop", LINUX_APP_NAME_MAP["signal"])

    def test_desktop_faculty_selects_linux_backend_when_platform_system_linux(self) -> None:
        with patch("core.desktop_faculty.platform.system", return_value="Linux"):
            faculty = DesktopFaculty()

        self.assertIsInstance(faculty._backend, LinuxAtspiBackend)

    def test_desktop_faculty_selects_windows_backend_when_platform_system_windows(self) -> None:
        with patch("core.desktop_faculty.platform.system", return_value="Windows"):
            faculty = DesktopFaculty()

        self.assertIsInstance(faculty._backend, WindowsMCPBackend)

    def test_desktop_faculty_selects_fallback_backend_when_platform_unknown(self) -> None:
        with patch("core.desktop_faculty.platform.system", return_value="Plan9"):
            faculty = DesktopFaculty()

        self.assertIsInstance(faculty._backend, FallbackBackend)

    def test_client_nix_exists_and_contains_at_spi2_core(self) -> None:
        path = Path(__file__).resolve().parent.parent.parent / "nixos" / "client.nix"
        text = path.read_text(encoding="utf-8")

        self.assertIn("at-spi2-core", text)

    def test_client_nix_contains_pyatspi(self) -> None:
        path = Path(__file__).resolve().parent.parent.parent / "nixos" / "client.nix"
        text = path.read_text(encoding="utf-8")

        self.assertIn("pyatspi", text)

    def test_client_nix_contains_thunderbird(self) -> None:
        path = Path(__file__).resolve().parent.parent.parent / "nixos" / "client.nix"
        text = path.read_text(encoding="utf-8")

        self.assertIn("thunderbird", text)

    def test_server_nix_exists_and_contains_inanna_service(self) -> None:
        path = Path(__file__).resolve().parent.parent.parent / "nixos" / "server.nix"
        text = path.read_text(encoding="utf-8")

        self.assertIn("inanna-nyx", text)

    def test_nixos_readme_mentions_client_nix(self) -> None:
        path = Path(__file__).resolve().parent.parent.parent / "nixos" / "README.md"
        text = path.read_text(encoding="utf-8")

        self.assertIn("client.nix", text)


if __name__ == "__main__":
    unittest.main()

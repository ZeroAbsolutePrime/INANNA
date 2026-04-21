"""Tests for the Voice Listener — Phase 7.5.
No microphone or model required — tests class structure only.
"""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestVoiceListenerExists(unittest.TestCase):
    def test_voice_init_exists(self) -> None:
        self.assertTrue((Path(__file__).parent.parent / "voice" / "__init__.py").exists())

    def test_voice_listener_exists(self) -> None:
        self.assertTrue((Path(__file__).parent.parent / "voice" / "listener.py").exists())

    def test_voice_readme_exists(self) -> None:
        self.assertTrue((Path(__file__).parent.parent / "voice" / "README.md").exists())


class TestVoiceListenerClass(unittest.TestCase):
    def _get_listener_class(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "voice.listener",
            Path(__file__).parent.parent / "voice" / "listener.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.VoiceListener, mod

    def test_instantiates_with_defaults(self) -> None:
        VoiceListener, _ = self._get_listener_class()
        vl = VoiceListener()
        self.assertEqual(vl.model_size, "base")
        self.assertIsNone(vl.language)
        self.assertEqual(vl.ws_url, "ws://localhost:8081")
        self.assertEqual(vl.device, "cpu")

    def test_custom_model_size(self) -> None:
        VoiceListener, _ = self._get_listener_class()
        vl = VoiceListener(model_size="small", language="es")
        self.assertEqual(vl.model_size, "small")
        self.assertEqual(vl.language, "es")

    def test_sample_rate_constant(self) -> None:
        _, mod = self._get_listener_class()
        self.assertEqual(mod.SAMPLE_RATE, 16000)

    def test_min_speech_seconds(self) -> None:
        _, mod = self._get_listener_class()
        self.assertEqual(mod.MIN_SPEECH_SECONDS, 0.5)

    def test_vad_chunk_size(self) -> None:
        _, mod = self._get_listener_class()
        self.assertEqual(mod.VAD_CHUNK, 512)

    def test_whisper_raises_import_error_when_missing(self) -> None:
        VoiceListener, _ = self._get_listener_class()
        vl = VoiceListener()
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == "faster_whisper":
                raise ImportError("faster_whisper not installed")
            return real_import(name, *args, **kwargs)
        with unittest.mock.patch("builtins.__import__", side_effect=mock_import):
            with self.assertRaises(ImportError):
                vl._load_whisper()

    def test_has_run_method(self) -> None:
        VoiceListener, _ = self._get_listener_class()
        self.assertTrue(hasattr(VoiceListener, "run"))

    def test_has_transcribe_method(self) -> None:
        VoiceListener, _ = self._get_listener_class()
        self.assertTrue(hasattr(VoiceListener, "transcribe"))

    def test_has_collect_speech_method(self) -> None:
        VoiceListener, _ = self._get_listener_class()
        self.assertTrue(hasattr(VoiceListener, "_collect_speech"))

    def test_argparser_accepts_model_flag(self) -> None:
        _, mod = self._get_listener_class()
        import argparse
        # Verify main() uses argparse with --model
        import inspect
        src = inspect.getsource(mod.main)
        self.assertIn("--model", src)
        self.assertIn("--lang", src)
        self.assertIn("--ws", src)
        self.assertIn("--device", src)


if __name__ == "__main__":
    unittest.main()

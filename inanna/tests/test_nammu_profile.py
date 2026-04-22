from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.nammu_profile import (
    OperatorProfile,
    RoutingCorrection,
    build_profile_from_user_profile,
    extract_potential_shorthands,
    load_operator_profile,
    save_operator_profile,
)
from core.profile import UserProfile


class NammuProfileTests(unittest.TestCase):
    def test_operator_profile_instantiates_with_defaults(self) -> None:
        profile = OperatorProfile()
        self.assertEqual("", profile.user_id)
        self.assertEqual({}, profile.known_shorthands)
        self.assertEqual("short", profile.preferred_length)

    def test_to_nammu_context_includes_display_name(self) -> None:
        profile = OperatorProfile(display_name="ZAERA")
        self.assertIn("Operator: ZAERA", profile.to_nammu_context())

    def test_to_nammu_context_includes_shorthands(self) -> None:
        profile = OperatorProfile(known_shorthands={"mtx": "Matxalen"})
        self.assertIn('"mtx"=Matxalen', profile.to_nammu_context())

    def test_to_nammu_context_includes_corrections(self) -> None:
        profile = OperatorProfile(
            routing_corrections=[
                {
                    "timestamp": "2026-04-22T00:00:00+00:00",
                    "original_text": "mtx replied?",
                    "misrouted_to": "none",
                    "correct_intent": "email_search",
                    "correct_params": {"query": "Matxalen"},
                }
            ]
        )
        context = profile.to_nammu_context()
        self.assertIn("Recent corrections:", context)
        self.assertIn('"mtx replied?" -> {"intent":"email_search"', context)

    def test_to_nammu_context_includes_top_domains(self) -> None:
        profile = OperatorProfile(domain_weights={"email": 0.8, "calendar": 0.3})
        self.assertIn("Most used: email, calendar", profile.to_nammu_context())

    def test_record_shorthand_stores_correctly(self) -> None:
        profile = OperatorProfile()
        profile.record_shorthand("mtx", "Matxalen")
        self.assertEqual("Matxalen", profile.known_shorthands["mtx"])

    def test_record_correction_stores_correctly(self) -> None:
        profile = OperatorProfile()
        profile.record_correction("mtx replied?", "none", "email_search", {"query": "Matxalen"})
        self.assertEqual(1, len(profile.routing_corrections))
        self.assertEqual("email_search", profile.routing_corrections[0]["correct_intent"])

    def test_record_correction_keeps_only_last_20(self) -> None:
        profile = OperatorProfile()
        for index in range(25):
            profile.record_correction(f"q{index}", "none", "email_search", {"query": str(index)})
        self.assertEqual(20, len(profile.routing_corrections))
        self.assertEqual("q5", profile.routing_corrections[0]["original_text"])

    def test_record_routing_increases_domain_weight(self) -> None:
        profile = OperatorProfile()
        profile.record_routing("email")
        self.assertGreater(profile.domain_weights["email"], 0.0)

    def test_record_routing_caps_at_one(self) -> None:
        profile = OperatorProfile(domain_weights={"email": 0.99})
        for _ in range(5):
            profile.record_routing("email")
        self.assertEqual(1.0, profile.domain_weights["email"])

    def test_detect_language_hola_returns_es(self) -> None:
        self.assertEqual("es", OperatorProfile().detect_language("hola, tengo correo urgente"))

    def test_detect_language_hello_returns_en(self) -> None:
        self.assertEqual("en", OperatorProfile().detect_language("hello there"))

    def test_detect_language_gracies_returns_ca(self) -> None:
        self.assertEqual("ca", OperatorProfile().detect_language("gràcies, resumeix els correus"))

    def test_detect_language_obrigado_returns_pt(self) -> None:
        self.assertEqual("pt", OperatorProfile().detect_language("obrigado, tenho mensagem hoje"))

    def test_update_language_pattern_records_context(self) -> None:
        profile = OperatorProfile()
        profile.update_language_pattern("hola", "email")
        self.assertIn("email", profile.language_patterns["es"])

    def test_routing_correction_to_example_line_formats_correctly(self) -> None:
        correction = RoutingCorrection(
            original_text="mtx replied?",
            correct_intent="email_search",
            correct_params={"query": "Matxalen"},
        )
        self.assertIn('"mtx replied?" -> {"intent":"email_search"', correction.to_example_line())

    def test_load_operator_profile_returns_empty_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile = load_operator_profile(Path(tmp), "user_1")
        self.assertEqual("user_1", profile.user_id)
        self.assertEqual({}, profile.known_shorthands)

    def test_load_operator_profile_returns_correct_profile_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "operator_profiles" / "user_1.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "user_id": "user_1",
                        "display_name": "ZAERA",
                        "known_shorthands": {"mtx": "Matxalen"},
                    }
                ),
                encoding="utf-8",
            )
            profile = load_operator_profile(root, "user_1")
        self.assertEqual("ZAERA", profile.display_name)
        self.assertEqual("Matxalen", profile.known_shorthands["mtx"])

    def test_save_operator_profile_creates_file_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = OperatorProfile(user_id="user_1", display_name="ZAERA")
            save_operator_profile(root, profile)
            saved = json.loads((root / "operator_profiles" / "user_1.json").read_text(encoding="utf-8"))
        self.assertEqual("ZAERA", saved["display_name"])

    def test_save_operator_profile_creates_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "nested"
            save_operator_profile(root, OperatorProfile(user_id="user_1"))
            self.assertTrue((root / "operator_profiles" / "user_1.json").exists())

    def test_build_profile_from_user_profile_seeds_display_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_profile = UserProfile(user_id="user_1", preferred_name="ZAERA")
            profile = build_profile_from_user_profile(user_profile, Path(tmp))
        self.assertEqual("ZAERA", profile.display_name)

    def test_build_profile_from_user_profile_seeds_preferred_length(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            user_profile = UserProfile(user_id="user_1", preferred_length="short")
            profile = build_profile_from_user_profile(user_profile, Path(tmp))
        self.assertEqual("short", profile.preferred_length)

    def test_extract_potential_shorthands_finds_short_words(self) -> None:
        found = extract_potential_shorthands("mtx replied about act", {})
        self.assertIn("mtx", found)
        self.assertIn("act", found)

    def test_extract_potential_shorthands_excludes_stop_words(self) -> None:
        found = extract_potential_shorthands("can you get it for me", {})
        self.assertEqual([], found)

    def test_extract_potential_shorthands_excludes_known_shorthands(self) -> None:
        found = extract_potential_shorthands("mtx replied", {"mtx": "Matxalen"})
        self.assertNotIn("mtx", found)


if __name__ == "__main__":
    unittest.main()

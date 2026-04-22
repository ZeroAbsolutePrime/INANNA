from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.nammu_intent import NAMMU_MULTILINGUAL_EXAMPLES, NAMMU_UNIVERSAL_PROMPT, _classify_domain_fast
from core.nammu_profile import OperatorProfile
from identity import CURRENT_PHASE


class MultilingualCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config_path = Path(__file__).resolve().parent.parent / "config" / "governance_signals.json"
        cls.governance_signals = json.loads(config_path.read_text(encoding="utf-8"))
        cls.domain_hints = cls.governance_signals["domain_hints"]

    def test_detect_language_correus_returns_ca(self) -> None:
        self.assertEqual("ca", OperatorProfile().detect_language("correus"))

    def test_detect_language_gracies_returns_ca(self) -> None:
        self.assertEqual("ca", OperatorProfile().detect_language("gracies"))

    def test_detect_language_bom_dia_returns_pt(self) -> None:
        self.assertEqual("pt", OperatorProfile().detect_language("bom dia"))

    def test_detect_language_hoje_returns_pt(self) -> None:
        self.assertEqual("pt", OperatorProfile().detect_language("hoje"))

    def test_detect_language_correos_returns_es(self) -> None:
        self.assertEqual("es", OperatorProfile().detect_language("correos"))

    def test_detect_language_eskerrik_asko_returns_eu(self) -> None:
        self.assertEqual("eu", OperatorProfile().detect_language("eskerrik asko"))

    def test_detect_language_english_default_returns_en(self) -> None:
        self.assertEqual("en", OperatorProfile().detect_language("hello there"))

    def test_governance_email_domain_hints_contains_correus(self) -> None:
        self.assertIn("correus", self.domain_hints["email"])

    def test_governance_email_domain_hints_contains_correos(self) -> None:
        self.assertIn("correos", self.domain_hints["email"])

    def test_governance_calendar_domain_hints_contains_que_tinc_avui(self) -> None:
        self.assertIn("que tinc avui", self.domain_hints["calendar"])

    def test_governance_calendar_domain_hints_contains_calendario(self) -> None:
        self.assertIn("calendario", self.domain_hints["calendar"])

    def test_governance_browser_domain_hints_contains_busca_en_internet(self) -> None:
        self.assertIn("busca en internet", self.domain_hints["browser"])

    def test_governance_document_domain_hints_contains_llegir_document(self) -> None:
        self.assertIn("llegir document", self.domain_hints["document"])

    def test_governance_desktop_domain_hints_contains_obre_firefox(self) -> None:
        self.assertIn("obre firefox", self.domain_hints["desktop"])

    def test_classify_domain_fast_returns_email_for_resumen_correos(self) -> None:
        self.assertEqual("email", _classify_domain_fast("resumen correos"))

    def test_classify_domain_fast_returns_calendar_for_que_tinc_avui(self) -> None:
        self.assertEqual("calendar", _classify_domain_fast("que tinc avui"))

    def test_classify_domain_fast_returns_browser_for_busca_en_internet(self) -> None:
        self.assertEqual("browser", _classify_domain_fast("busca en internet nixos"))

    def test_classify_domain_fast_returns_document_for_llegir_document(self) -> None:
        self.assertEqual("document", _classify_domain_fast("llegir document"))

    def test_classify_domain_fast_returns_desktop_for_obre_firefox(self) -> None:
        self.assertEqual("desktop", _classify_domain_fast("obre firefox"))

    def test_multilingual_examples_constant_contains_spanish_example(self) -> None:
        self.assertIn('"urgentes?" (es)', NAMMU_MULTILINGUAL_EXAMPLES)

    def test_multilingual_examples_constant_contains_catalan_example(self) -> None:
        self.assertIn('"que tinc avui?" (ca)', NAMMU_MULTILINGUAL_EXAMPLES)

    def test_multilingual_examples_constant_contains_portuguese_heading(self) -> None:
        self.assertIn("Portuguese", NAMMU_MULTILINGUAL_EXAMPLES)

    def test_universal_prompt_contains_multilingual_examples_block(self) -> None:
        self.assertIn("MULTILINGUAL EXAMPLES", NAMMU_UNIVERSAL_PROMPT)

    def test_universal_prompt_contains_obre_firefox_example(self) -> None:
        self.assertIn('"obre firefox" (ca)', NAMMU_UNIVERSAL_PROMPT)

    def test_universal_prompt_contains_final_return_exactly_instruction(self) -> None:
        self.assertIn("Return exactly this JSON", NAMMU_UNIVERSAL_PROMPT)

    def test_phase_identity_contains_cycle9_phase6(self) -> None:
        self.assertIn("9.6", CURRENT_PHASE)


if __name__ == "__main__":
    unittest.main()

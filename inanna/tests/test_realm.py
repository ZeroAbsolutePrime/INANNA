from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.realm import DEFAULT_REALM, RealmConfig, RealmManager


class RealmTests(unittest.TestCase):
    def test_realm_manager_can_be_instantiated_with_temp_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = RealmManager(Path(temp_dir))

            self.assertIsInstance(manager, RealmManager)
            self.assertTrue(manager.realms_root.exists())

    def test_ensure_default_realm_creates_default_realm_if_absent(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = RealmManager(Path(temp_dir))

            config = manager.ensure_default_realm()

            self.assertEqual(config.name, DEFAULT_REALM)
            self.assertTrue(manager.realm_exists(DEFAULT_REALM))

    def test_create_realm_creates_all_required_subdirectories(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = RealmManager(Path(temp_dir))

            manager.create_realm("work")
            realm_dir = manager.realms_root / "work"

            self.assertTrue((realm_dir / "sessions").exists())
            self.assertTrue((realm_dir / "memory").exists())
            self.assertTrue((realm_dir / "proposals").exists())
            self.assertTrue((realm_dir / "nammu").exists())

    def test_list_realms_returns_correct_realm_names(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = RealmManager(Path(temp_dir))
            manager.create_realm("work")
            manager.create_realm("research")

            self.assertEqual(manager.list_realms(), ["research", "work"])

    def test_realm_exists_returns_true_false_correctly(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = RealmManager(Path(temp_dir))
            manager.create_realm("work")

            self.assertTrue(manager.realm_exists("work"))
            self.assertFalse(manager.realm_exists("missing"))

    def test_load_realm_returns_realm_config_with_correct_fields(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = RealmManager(Path(temp_dir))
            manager.create_realm(
                "work",
                purpose="Work-related conversations and analysis.",
                governance_context="Standard governance applies.",
            )

            loaded = manager.load_realm("work")

            self.assertIsInstance(loaded, RealmConfig)
            assert loaded is not None
            self.assertEqual(loaded.name, "work")
            self.assertEqual(loaded.purpose, "Work-related conversations and analysis.")
            self.assertEqual(loaded.governance_context, "Standard governance applies.")

    def test_realm_data_dirs_returns_all_four_keys(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = RealmManager(Path(temp_dir))

            dirs = manager.realm_data_dirs("work")

            self.assertEqual(set(dirs.keys()), {"sessions", "memory", "proposals", "nammu"})

    def test_update_realm_governance_context_persists_new_value(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = RealmManager(Path(temp_dir))
            manager.create_realm(
                "work",
                purpose="Work-related conversations and analysis.",
                governance_context="Initial context.",
            )

            updated = manager.update_realm_governance_context(
                "work",
                "Focus on work memory boundaries.",
            )
            loaded = manager.load_realm("work")

            self.assertTrue(updated)
            assert loaded is not None
            self.assertEqual(loaded.governance_context, "Focus on work memory boundaries.")


if __name__ == "__main__":
    unittest.main()

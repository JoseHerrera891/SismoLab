import os
from pathlib import Path
import tempfile
import unittest

from core.event import Event
from sismolab_controller import SismoLabController


FIXTURES = Path(__file__).parent / "fixtures"


class FixtureScenarioTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()
        os.chdir(self.temp_dir.name)
        self.controller = SismoLabController()

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    def _load_scenario(self, filename):
        data = self.controller.persistence.load_from_json(
            str(FIXTURES / filename)
        )
        self.controller.restore_scenario_state(data)

    def test_insertion_load_covers_thresholds_and_rejects_duplicate_ids(self):
        data = self.controller.persistence.load_from_json(
            str(FIXTURES / "load_insertions.json")
        )
        self.controller.replace_events(data["events"])

        self.assertEqual(len(self.controller.events), 6)
        self.assertEqual(
            [self.controller.event_manager.get_event(event_id).priority
             for event_id in range(1001, 1007)],
            [3, 3, 2, 3, 1, 3],
        )
        self.assertTrue(self.controller.verify_structure()["valid"])

        duplicate_data = self.controller.persistence.load_from_json(
            str(FIXTURES / "load_duplicate_ids_invalid.json")
        )
        with self.assertRaises(ValueError):
            self.controller.replace_events(duplicate_data["events"])
        self.assertEqual(len(self.controller.events), 6)
        self.assertTrue(self.controller.verify_structure()["valid"])

    def test_normal_topology_load_supports_archive_and_undo(self):
        self._load_scenario("scenario_normal_topology.json")
        self.assertTrue(self.controller.verify_structure()["valid"])

        candidate = self.controller.preview_archive_candidate()
        self.assertEqual(candidate["count"], 7)
        archived = self.controller.archive_eligible_branch()
        self.assertEqual(archived["count"], 7)
        self.assertEqual(len(self.controller.event_manager.archived_events), 7)

        self.assertTrue(self.controller.undo())
        self.assertEqual(len(self.controller.event_manager.archived_events), 0)
        self.assertEqual(len(self.controller.events), 7)
        self.assertTrue(self.controller.verify_structure()["valid"])

    def test_stress_topology_load_and_recovery(self):
        self._load_scenario("scenario_stress_topology.json")

        audit = self.controller.verify_structure()
        self.assertTrue(audit["valid"])
        self.assertTrue(audit["expected_imbalances"])
        self.assertTrue(
            any("balance factor -5" in item for item in audit["expected_imbalances"])
        )

        self.assertGreater(self.controller.recover_stress_mode(), 0)
        self.assertFalse(self.controller.stress_manager.is_stress_mode)
        self.assertTrue(self.controller.verify_structure()["valid"])

    def test_invalid_topology_is_rejected_without_replacing_state(self):
        event = Event(
            2001,
            3.0,
            50.0,
            100.0,
            100.0,
            self.controller.simulation_clock,
            "KEEP",
        )
        self.controller.add_event(event)
        previous_root = self.controller.tree.root

        data = self.controller.persistence.load_from_json(
            str(FIXTURES / "scenario_invalid_topology.json")
        )
        with self.assertRaises(ValueError):
            self.controller.restore_scenario_state(data)

        self.assertIs(self.controller.tree.root, previous_root)
        self.assertEqual([item.id for item in self.controller.events], [2001])

    def test_report_burst_is_processed_in_fifo_order(self):
        self._load_scenario("report_burst.json")
        self.assertEqual(len(self.controller.report_queue.to_list()), 5)

        results = [
            self.controller.process_next_event_report()
            for _ in range(5)
        ]

        self.assertEqual(results, ["created"] * 5)
        self.assertEqual(self.controller.process_next_event_report(), "empty")
        self.assertEqual(
            [event.id for event in self.controller.events],
            [1901, 1902, 1903, 1904, 1905],
        )
        self.assertTrue(self.controller.verify_structure()["valid"])

    def test_mixed_priority_branch_is_not_archive_eligible(self):
        self._load_scenario("archive_mixed_priority.json")
        self.assertTrue(self.controller.verify_structure()["valid"])
        self.assertIsNone(self.controller.preview_archive_candidate())

    def test_each_rotation_fixture_triggers_its_named_rotation(self):
        for rotation in ("ll", "rr", "lr", "rl"):
            with self.subTest(rotation=rotation):
                controller = SismoLabController()
                data = controller.persistence.load_from_json(
                    str(FIXTURES / "rotations" / f"{rotation}.json")
                )
                controller.replace_events(data["events"])

                self.assertGreater(
                    getattr(controller.tree, f"{rotation}_rotations"), 0
                )
                self.assertTrue(controller.verify_structure()["valid"])


if __name__ == "__main__":
    unittest.main()

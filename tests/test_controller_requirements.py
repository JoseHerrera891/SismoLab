import copy
import os
import tempfile
import unittest
from datetime import timedelta

from core.event import Event
from sismolab_controller import SismoLabController


class ControllerRequirementTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()
        os.chdir(self.temp_dir.name)
        self.controller = SismoLabController()

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    def _add_low_priority_events(self, count, timestamp=None):
        timestamp = timestamp or self.controller.simulation_clock
        for event_id in range(1, count + 1):
            event = Event(
                event_id,
                3.0,
                50.0,
                float(event_id),
                10.0,
                timestamp,
                f"ST-{event_id}",
            )
            self.assertTrue(self.controller.add_event(event))

    @staticmethod
    def _topology_signature(tree):
        if tree.root is None:
            return None
        result = {}
        stack = [tree.root]
        while stack:
            node = stack.pop()
            event_id = node.getValue().id
            left = node.getLeftChild()
            right = node.getRightChild()
            result[event_id] = (
                left.getValue().id if left else None,
                right.getValue().id if right else None,
                node.getHeight(),
            )
            if left:
                stack.append(left)
            if right:
                stack.append(right)
        return tree.root.getValue().id, result

    def test_structure_audit_detects_cycles_without_looping(self):
        self._add_low_priority_events(3)
        root = self.controller.tree.root
        original_left = root.getLeftChild()
        root.setLeftChild(root)

        result = self.controller.verify_structure()

        root.setLeftChild(original_left)
        self.assertFalse(result["valid"])
        self.assertTrue(any("cycle" in error for error in result["errors"]))
        self.assertLess(result["nodes_examined"], 3)

    def test_queries_and_dashboard_metrics_report_expected_counts(self):
        self._add_low_priority_events(4)

        top_pending = self.controller.query_top_pending(2)
        magnitude = self.controller.query_magnitude_range(2.5, 3.5)
        shallow = self.controller.query_shallow_events_by_date(
            700,
            self.controller.simulation_clock - timedelta(days=1),
            self.controller.simulation_clock,
        )
        associations = self.controller.query_associations(1)
        costly = self.controller.query_costly_access_events()
        metrics = self.controller.get_dashboard_metrics()

        self.assertEqual(len(top_pending["events"]), 2)
        self.assertEqual(top_pending["nodes_examined"], 2)
        self.assertEqual(len(magnitude["events"]), 4)
        self.assertEqual(magnitude["nodes_examined"], 4)
        self.assertEqual(len(shallow["events"]), 4)
        self.assertEqual(shallow["nodes_examined"], 4)
        self.assertEqual(associations["nodes_examined"], 4)
        self.assertEqual(costly["nodes_examined"], 4)
        self.assertEqual(len(metrics["traversals"]["level_order"]), 4)
        self.assertEqual(metrics["priority_counts"][1], 4)

    def test_costly_access_query_uses_strict_node_depth_limit(self):
        self.controller.start_stress_mode()
        self._add_low_priority_events(3)
        high_priority = Event(
            4,
            6.0,
            50.0,
            4.0,
            10.0,
            self.controller.simulation_clock,
            "ST-4",
        )
        self.assertTrue(self.controller.add_event(high_priority))
        self.controller.set_costly_access_limit(1)

        result = self.controller.query_costly_access_events()

        self.assertEqual(
            [entry["event"].id for entry in result["events"]], [4]
        )
        self.assertEqual(result["events"][0]["depth"], 3)
        self.assertEqual(result["events"][0]["comparisons"], 4)
        self.assertEqual(result["nodes_examined"], 4)

    def test_invalid_correction_does_not_change_event_or_undo_history(self):
        self._add_low_priority_events(3)
        event = self.controller.event_manager.get_event(1)
        original_magnitude = event.magnitude
        original_key = event.key
        original_undo_size = self.controller.undo_stack.size()

        with self.assertRaises(ValueError):
            self.controller.update_event(1, {"revision": 50})

        self.assertEqual(event.magnitude, original_magnitude)
        self.assertEqual(event.key, original_key)
        self.assertEqual(self.controller.undo_stack.size(), original_undo_size)
        self.assertTrue(self.controller.verify_structure()["valid"])

    def test_stress_recovery_and_undo_restore_exact_topology(self):
        self.controller.start_stress_mode()
        self._add_low_priority_events(8)
        stress_audit = self.controller.verify_structure()
        self.assertTrue(stress_audit["valid"])
        self.assertTrue(stress_audit["expected_imbalances"])
        unbalanced_topology = self._topology_signature(self.controller.tree)

        rotations = self.controller.recover_stress_mode()

        self.assertGreater(rotations, 0)
        self.assertFalse(self.controller.stress_manager.is_stress_mode)
        self.assertTrue(self.controller.verify_structure()["valid"])
        self.assertTrue(self.controller.undo())
        self.assertTrue(self.controller.stress_manager.is_stress_mode)
        self.assertEqual(
            self._topology_signature(self.controller.tree), unbalanced_topology
        )

    def test_archive_is_one_undoable_action_and_restores_counters(self):
        old_time = self.controller.simulation_clock - timedelta(hours=100)
        self._add_low_priority_events(7, old_time)
        original_topology = self._topology_signature(self.controller.tree)

        archived = self.controller.archive_eligible_branch()

        self.assertEqual(archived["count"], 7)
        self.assertEqual(len(self.controller.event_manager.archived_events), 7)
        self.assertEqual(self.controller.operation_counters["mass_archives"], 1)
        self.assertTrue(self.controller.undo())
        self.assertEqual(len(self.controller.event_manager.archived_events), 0)
        self.assertEqual(
            self._topology_signature(self.controller.tree), original_topology
        )
        self.assertEqual(self.controller.operation_counters["mass_archives"], 0)

    def test_archive_requires_strict_age_and_rejects_mixed_priority_subtree(self):
        clock = self.controller.simulation_clock
        self.assertTrue(
            self.controller.add_event(
                Event(1, 3.0, 50.0, 1.0, 1.0, clock - timedelta(hours=72), "ST-1")
            )
        )
        self.assertIsNone(self.controller.preview_archive_candidate())

        self.assertTrue(
            self.controller.add_event(
                Event(2, 6.0, 50.0, 2.0, 2.0, clock - timedelta(hours=100), "ST-2")
            )
        )
        self.assertIsNone(self.controller.preview_archive_candidate())

    def test_normal_scenario_roundtrip_restores_settings_and_topology(self):
        self._add_low_priority_events(8)
        self.controller.set_association_limits(36, 25)
        self.controller.set_costly_access_limit(5)
        self.controller.set_archive_age_threshold(96)
        self.controller.advance_simulation_clock(2)
        original_topology = self._topology_signature(self.controller.tree)
        path = os.path.join(self.temp_dir.name, "normal-scenario.json")
        self.controller.persistence.save_scenario(
            self.controller, path, version_name="normal-version"
        )

        restored = SismoLabController()
        restored.restore_scenario_state(
            restored.persistence.load_from_json(path)
        )

        self.assertEqual(
            self._topology_signature(restored.tree), original_topology
        )
        self.assertEqual(restored.replica_manager.W_hours, 36)
        self.assertEqual(restored.replica_manager.R_km, 25)
        self.assertEqual(restored.costly_access_limit, 5)
        self.assertEqual(restored.archive_age_threshold_hours, 96)
        self.assertEqual(
            restored.simulation_clock, self.controller.simulation_clock
        )
        self.assertTrue(restored.verify_structure()["valid"])

    def test_scenario_roundtrip_and_invalid_topology_preserve_current_state(self):
        self.controller.start_stress_mode()
        self._add_low_priority_events(5)
        self.assertTrue(
            self.controller.update_event(1, {"magnitude": 3.5})
        )
        path = os.path.join(self.temp_dir.name, "scenario.json")
        self.controller.persistence.save_scenario(
            self.controller, path, version_name="test-version"
        )
        loaded = self.controller.persistence.load_from_json(path)

        restored = SismoLabController()
        restored.restore_scenario_state(loaded)

        self.assertTrue(restored.stress_manager.is_stress_mode)
        self.assertEqual(
            self._topology_signature(restored.tree),
            self._topology_signature(self.controller.tree),
        )
        self.assertEqual(
            restored.operation_counters["corrections_accepted"], 1
        )
        previous_root = restored.tree.root
        invalid_data = copy.deepcopy(loaded)
        invalid_data["tree"]["nodes"][0]["balance_factor"] += 1
        with self.assertRaises(ValueError):
            restored.restore_scenario_state(invalid_data)
        self.assertIs(restored.tree.root, previous_root)
        self.assertEqual(len(restored.events), 5)

    def test_processing_fifo_report_can_be_undone_with_queue_position(self):
        report = {
            "event_id": 20,
            "revision": 1,
            "magnitude": 3.2,
            "depth": 40.0,
            "x": 20.0,
            "y": 20.0,
            "timestamp": self.controller.simulation_clock.isoformat(),
            "station": "ST-20",
        }
        self.controller.enqueue_event_report(report)

        self.assertEqual(self.controller.process_next_event_report(), "created")
        self.assertIsNotNone(self.controller.event_manager.get_event(20))
        self.assertTrue(self.controller.undo())
        self.assertIsNone(self.controller.event_manager.get_event(20))
        self.assertEqual(len(self.controller.report_queue.to_list()), 1)


if __name__ == "__main__":
    unittest.main()

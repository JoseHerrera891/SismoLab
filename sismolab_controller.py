from copy import deepcopy
import math
from pathlib import Path

from core.AVL_tree import AVLtree
from core.event_manager import EventManager
from core.queues_stacks import UndoStack, ReportQueue
from core.stress_manager import StressManager
from services.associations import ReplicaManager
from services.map_manager import MapManager
from services.persistence import Auditor, PersistenceManager
from core.event import Event


class SismoLabController:
    def __init__(self):
        self.tree = AVLtree()
        self.event_manager = EventManager(self.tree)
        self.stress_manager = StressManager(self.tree)

        self.undo_stack = UndoStack()
        self.report_queue = ReportQueue()

        self.map_manager = MapManager()
        zones_file = Path(__file__).resolve().parent / "test_zones.json"
        self.map_manager.load_zones(zones_file)
        self.replica_manager = ReplicaManager()
        self.auditor = Auditor()
        self.persistence = PersistenceManager(self.auditor)

    @property
    def events(self):
        return list(self.event_manager.active_events.values())

    def generate_event_id(self) -> int:
        """Return the next ID after all active or permanently deleted events."""
        occupied_ids = (
            set(self.event_manager.active_events)
            | self.event_manager.deleted_ids
        )
        next_id = max(occupied_ids, default=0) + 1
        if next_id > 999999:
            raise ValueError("No more event IDs are available.")
        return next_id

    def replace_events(self, events: list[Event]) -> None:
        """Replace the current scenario with events loaded from a data source."""
        new_tree = AVLtree()
        new_event_manager = EventManager(new_tree)
        seen_ids = set()

        for event in events:
            if not isinstance(event, Event):
                raise TypeError("All loaded items must be Event instances.")
            if event.id in seen_ids:
                raise ValueError(f"Duplicate event ID: {event.display_id}")
            seen_ids.add(event.id)
            new_event_manager.add_event(event)

        self.tree = new_tree
        self.event_manager = new_event_manager
        self.stress_manager = StressManager(new_tree)
        self.undo_stack.clear()
        self.auditor.log_event(
            "REPLACE_SCENARIO",
            f"Loaded scenario with {len(seen_ids)} events",
        )

    def add_event(self, event: Event) -> bool:
        if (
            event.id in self.event_manager.active_events
            or event.id in self.event_manager.deleted_ids
        ):
            return False

        self.undo_stack.push(deepcopy(self.events))
        auto_balance = not self.stress_manager.is_stress_mode
        added = self.event_manager.add_event(
            event,
            auto_balance=auto_balance,
        )

        if added:
            self.auditor.log_event("ADD_EVENT", f"Added event {event.display_id}")

        return added

    def register_event_report(self, event: Event) -> str:
        """Register an event or add a reporting station to an existing event."""
        existing = self.event_manager.get_event(event.id)
        if existing is not None:
            if not event.station or event.station in existing.accepted_stations:
                return "duplicate"
            self.undo_stack.push(deepcopy(self.events))
            existing.accepted_stations.add(event.station)
            self.auditor.log_event(
                "ADD_EVENT_REPORT",
                f"Station {event.station} reported {existing.display_id}",
            )
            return "station_added"

        if not self.add_event(event):
            return "id_unavailable"
        return "created"

    def update_event(self, event_id: int, new_data: dict) -> bool:
        if self.event_manager.get_event(event_id) is None:
            return False

        self.undo_stack.push(deepcopy(self.events))
        auto_balance = not self.stress_manager.is_stress_mode
        updated = self.event_manager.update_event(
            event_id,
            new_data,
            auto_balance=auto_balance,
        )

        if updated:
            self.auditor.log_event(
                "UPDATE_EVENT", f"Updated event SIS-{event_id:06d}"
            )

        return updated

    def get_event_search_details(self, event_id: int) -> dict | None:
        """Return an event and AVL search metrics, or None when it is absent."""
        event = self.event_manager.get_event(event_id)
        if event is None:
            return None

        node = self.tree.root
        comparisons = 0
        while node is not None:
            comparisons += 1
            if event.key == node.key:
                break
            if event.key < node.key:
                node = node.getLeftChild()
            else:
                node = node.getRightChild()

        if node is None:
            raise RuntimeError(
                f"Active event SIS-{event_id:06d} is missing from the AVL tree."
            )

        expected_comparisons = math.ceil(
            math.log2(len(self.event_manager.active_events) + 1)
        )
        return {
            "event": event,
            "depth": comparisons,
            "comparisons": comparisons,
            "access_costly": comparisons > expected_comparisons,
            "cost_threshold": expected_comparisons,
        }

    def mark_event_as_reviewed(self, event_id: int) -> bool:
        event = self.event_manager.get_event(event_id)
        if event is None or event.status == "REVIEWED":
            return False

        self.undo_stack.push(deepcopy(self.events))
        reviewed = self.event_manager.mark_as_reviewed(event_id)
        if reviewed:
            self.auditor.log_event(
                "MARK_REVIEWED",
                f"Marked event SIS-{event_id:06d} as reviewed",
            )
        return reviewed

    def delete_event(self, event_id: int) -> bool:
        if self.event_manager.get_event(event_id) is None:
            return False

        self.undo_stack.push(deepcopy(self.events))
        auto_balance = not self.stress_manager.is_stress_mode
        deleted = self.event_manager.delete_event(
            event_id,
            auto_balance=auto_balance,
        )

        if deleted:
            self.auditor.log_event(
                "DELETE_EVENT", f"Deleted event SIS-{event_id:06d}"
            )

        return deleted

    def undo(self) -> bool:
        if self.undo_stack.is_empty():
            return False

        events_to_restore = self.undo_stack.pop()
        current_ids = set(self.event_manager.active_events)
        restored_ids = {event.id for event in events_to_restore}
        deleted_ids = set(self.event_manager.deleted_ids)
        deleted_ids.update(current_ids - restored_ids)
        stress_mode = self.stress_manager.is_stress_mode

        new_tree = AVLtree()
        new_event_manager = EventManager(new_tree)
        for event in events_to_restore:
            new_event_manager.add_event(event)
        new_event_manager.deleted_ids = deleted_ids

        self.tree = new_tree
        self.event_manager = new_event_manager
        self.stress_manager = StressManager(new_tree)
        if stress_mode:
            self.stress_manager.enable_stress_mode()
        self.auditor.log_event("UNDO", "Restored the previous event state")
        return True
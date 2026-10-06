from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path

from core.AVL_tree import AVLnode, AVLtree
from core.bst_tree import BinarySearchTree
from core.event_manager import EventManager
from core.queues_stacks import UndoStack, ReportQueue
from core.stress_manager import StressManager
from services.associations import ReplicaManager
from services.map_manager import MapManager, Zone
from services.persistence import Auditor, PersistenceManager
from core.event import Event


class SismoLabController:
    def __init__(self):
        self.tree = AVLtree()
        self.costly_access_limit = 3
        self.archive_age_threshold_hours = 72.0
        self.simulation_clock = datetime.now(timezone.utc)
        self.operation_counters = {
            "corrections_accepted": 0,
            "reports_discarded": 0,
            "conflicts": 0,
            "mass_archives": 0,
            "events_archived": 0,
        }
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
            | set(self.event_manager.archived_events)
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

        self._push_full_undo_state()
        self.tree = new_tree
        self.event_manager = new_event_manager
        self.stress_manager = StressManager(new_tree)
        self.report_queue.restore([])
        self.operation_counters = {
            "corrections_accepted": 0,
            "reports_discarded": 0,
            "conflicts": 0,
            "mass_archives": 0,
            "events_archived": 0,
        }
        self.auditor.log_event(
            "REPLACE_SCENARIO",
            f"Loaded scenario with {len(seen_ids)} events",
        )

    def restore_scenario_state(self, data: dict) -> None:
        """Validate a complete saved scenario before replacing current state."""
        config = data.get("system_config")
        tree_data = data.get("tree")
        metrics = data.get("metrics")
        if not all(isinstance(value, dict) for value in (config, tree_data, metrics)):
            raise ValueError("Scenario configuration, tree, or metrics are invalid.")

        active = self._events_by_id(data.get("active_events"), "active_events")
        archived = self._events_by_id(
            data.get("archived_events"), "archived_events"
        )
        deleted_ids = data.get("deleted_ids")
        if not isinstance(deleted_ids, list) or any(
            isinstance(event_id, bool)
            or not isinstance(event_id, int)
            or not 1 <= event_id <= 999999
            for event_id in deleted_ids
        ):
            raise ValueError("Deleted IDs must be valid numeric event IDs.")
        deleted_id_set = set(deleted_ids)
        if (
            len(deleted_id_set) != len(deleted_ids)
            or set(active) & set(archived)
            or (set(active) | set(archived)) & deleted_id_set
        ):
            raise ValueError("Active, archived, and deleted event IDs must be unique.")

        clock_text = config.get("simulation_clock")
        if not isinstance(clock_text, str):
            raise ValueError("Simulation clock must be an ISO 8601 timestamp.")
        try:
            simulation_clock = datetime.fromisoformat(clock_text)
        except ValueError as error:
            raise ValueError("Simulation clock must be an ISO 8601 timestamp.") from error
        if simulation_clock.tzinfo is None:
            raise ValueError("Simulation clock must include a UTC offset.")
        simulation_clock = simulation_clock.astimezone(timezone.utc)
        if any(
            event.timestamp > simulation_clock
            for event in list(active.values()) + list(archived.values())
        ):
            raise ValueError("Scenario contains an event later than its simulation clock.")

        W_hours = self._positive_finite_config(config, "W_hours")
        R_km = self._positive_finite_config(config, "R_km")
        threshold = self._positive_finite_config(config, "T_hours")
        costly_limit = config.get("L")
        if (
            isinstance(costly_limit, bool)
            or not isinstance(costly_limit, int)
            or costly_limit < 0
        ):
            raise ValueError("Costly-access limit L must be a non-negative integer.")
        stress_mode = config.get("stress_mode")
        if not isinstance(stress_mode, bool):
            raise ValueError("Stress mode must be a boolean.")
        counters_data = data.get("operation_counters", {})
        if not isinstance(counters_data, dict):
            raise ValueError("Operation counters must be an object.")
        counter_names = (
            "corrections_accepted",
            "reports_discarded",
            "conflicts",
            "mass_archives",
            "events_archived",
        )
        operation_counters = {}
        for counter_name in counter_names:
            counter = counters_data.get(counter_name, 0)
            if (
                isinstance(counter, bool)
                or not isinstance(counter, int)
                or counter < 0
            ):
                raise ValueError(
                    f"Operation counter '{counter_name}' must be a "
                    "non-negative integer."
                )
            operation_counters[counter_name] = counter

        report_data = data.get("report_queue")
        if not isinstance(report_data, list):
            raise ValueError("Report queue must be a list.")
        reports = []
        for report in report_data:
            parsed = self._event_from_report(report)
            if not parsed.station:
                raise ValueError("Queued reports must identify their station.")
            if parsed.timestamp > simulation_clock:
                raise ValueError("Queued report time is later than the simulation clock.")
            reports.append(
                {
                    "event_id": parsed.id,
                    "magnitude": parsed.magnitude,
                    "depth": parsed.depth,
                    "x": parsed.x,
                    "y": parsed.y,
                    "timestamp": parsed.timestamp.isoformat(),
                    "station": parsed.station,
                    "is_populated": parsed.is_populated,
                    "revision": parsed.revision,
                }
            )

        new_tree = self._tree_from_topology(
            tree_data, active, stress_mode, metrics
        )
        zones_data = data.get("zones")
        if not isinstance(zones_data, list):
            raise ValueError("Scenario zones must be a list.")
        new_map_manager = MapManager()
        for index, zone_data in enumerate(zones_data):
            if not isinstance(zone_data, dict):
                raise ValueError(f"Zone {index} must be an object.")
            numeric_fields = ("x_min", "x_max", "y_min", "y_max")
            coordinates = {}
            for field in numeric_fields:
                value = zone_data.get(field)
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or not 0 <= value <= 1000
                ):
                    raise ValueError(f"Zone {index} has an invalid {field}.")
                coordinates[field] = float(value)
            if (
                coordinates["x_min"] > coordinates["x_max"]
                or coordinates["y_min"] > coordinates["y_max"]
            ):
                raise ValueError(f"Zone {index} has reversed bounds.")
            name = zone_data.get("name")
            populated = zone_data.get("is_populated")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Zone {index} must have a name.")
            if not isinstance(populated, bool):
                raise ValueError(f"Zone {index} has an invalid population flag.")
            new_map_manager.add_zone(
                Zone(name.strip(), **coordinates, is_populated=populated)
            )

        new_replica_manager = ReplicaManager(W_hours, R_km)
        self._push_full_undo_state()
        self.tree = new_tree
        self.event_manager = EventManager(new_tree)
        self.event_manager.active_events = active
        self.event_manager.archived_events = archived
        self.event_manager.deleted_ids = deleted_id_set
        self.stress_manager = StressManager(new_tree)
        if stress_mode:
            self.stress_manager.enable_stress_mode()
        self.report_queue.restore(reports)
        self.replica_manager = new_replica_manager
        self.map_manager = new_map_manager
        self.costly_access_limit = costly_limit
        self.archive_age_threshold_hours = threshold
        self.simulation_clock = simulation_clock
        self.operation_counters = operation_counters
        self.auditor.log_event(
            "RESTORE_SCENARIO",
            f"Restored {len(active)} active, {len(archived)} archived, "
            f"and {len(deleted_id_set)} retired events",
        )

    @staticmethod
    def _events_by_id(events, field: str) -> dict[int, Event]:
        if not isinstance(events, list) or any(
            not isinstance(event, Event) for event in events
        ):
            raise ValueError(f"Scenario field '{field}' must contain events.")
        result = {event.id: event for event in events}
        if len(result) != len(events):
            raise ValueError(f"Scenario field '{field}' has duplicate IDs.")
        return result

    @staticmethod
    def _positive_finite_config(config: dict, field: str) -> float:
        value = config.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
        ):
            raise ValueError(f"Scenario setting {field} must be positive and finite.")
        return float(value)

    @staticmethod
    def _tree_from_topology(
        tree_data: dict,
        active_events: dict[int, Event],
        stress_mode: bool,
        metrics: dict,
    ) -> AVLtree:
        root_id = tree_data.get("root_id")
        node_data = tree_data.get("nodes")
        if not isinstance(node_data, list):
            raise ValueError("Tree nodes must be a list.")
        if (root_id is None) != (len(node_data) == 0):
            raise ValueError("Tree root and node list are inconsistent.")
        node_records = {}
        for record in node_data:
            if not isinstance(record, dict):
                raise ValueError("Each saved tree node must be an object.")
            event_id = record.get("id")
            height = record.get("height")
            if (
                isinstance(event_id, bool)
                or not isinstance(event_id, int)
                or event_id not in active_events
            ):
                raise ValueError("Tree node references an unknown active event.")
            if event_id in node_records:
                raise ValueError("Tree contains a duplicate event node.")
            if isinstance(height, bool) or not isinstance(height, int) or height < 0:
                raise ValueError("Tree node height must be a non-negative integer.")
            node_records[event_id] = record
        if set(node_records) != set(active_events):
            raise ValueError("Every active event must appear exactly once in the tree.")

        nodes = {event_id: AVLnode(event) for event_id, event in active_events.items()}
        parent_ids = {}
        for event_id, record in node_records.items():
            node = nodes[event_id]
            for side, setter in (
                ("left", node.setLeftChild),
                ("right", node.setRightChild),
            ):
                child_id = record.get(side)
                if child_id is None:
                    continue
                if (
                    isinstance(child_id, bool)
                    or not isinstance(child_id, int)
                    or child_id not in nodes
                ):
                    raise ValueError(f"Tree node {event_id} has an invalid {side} link.")
                if child_id in parent_ids:
                    raise ValueError("A tree node cannot have multiple parents.")
                parent_ids[child_id] = event_id
                setter(nodes[child_id])
                nodes[child_id].setFather(node)
            node.setHeight(record["height"])

        if root_id is not None and (
            isinstance(root_id, bool)
            or not isinstance(root_id, int)
            or root_id not in nodes
            or root_id in parent_ids
        ):
            raise ValueError("Saved tree root is invalid.")
        if set(parent_ids) != set(nodes) - ({root_id} if root_id is not None else set()):
            raise ValueError("Saved tree has detached nodes or an invalid root.")

        tree = AVLtree()
        tree.root = nodes.get(root_id)
        if tree.root is not None:
            tree.root.setFather(None)
        visited = set()
        postorder = []
        stack = [(root_id, None, None, False)] if root_id is not None else []
        while stack:
            event_id, lower, upper, expanded = stack.pop()
            node = nodes[event_id]
            if expanded:
                postorder.append(event_id)
                continue
            if event_id in visited:
                raise ValueError("Saved tree contains a cycle.")
            visited.add(event_id)
            if lower is not None and not lower < node.key:
                raise ValueError("Saved tree violates global BST ordering.")
            if upper is not None and not node.key < upper:
                raise ValueError("Saved tree violates global BST ordering.")
            record = node_records[event_id]
            stack.append((event_id, lower, upper, True))
            if record.get("right") is not None:
                stack.append((record["right"], node.key, upper, False))
            if record.get("left") is not None:
                stack.append((record["left"], lower, node.key, False))
        if visited != set(nodes):
            raise ValueError("Saved tree contains nodes unreachable from its root.")

        heights = {}
        for event_id in postorder:
            record = node_records[event_id]
            left_id, right_id = record.get("left"), record.get("right")
            left_height = heights.get(left_id, -1)
            right_height = heights.get(right_id, -1)
            actual_height = 1 + max(left_height, right_height)
            actual_balance = left_height - right_height
            if record["height"] != actual_height:
                raise ValueError(f"Saved height is incorrect for event {event_id}.")
            if record.get("balance_factor") != actual_balance:
                raise ValueError(
                    f"Saved balance factor is incorrect for event {event_id}."
                )
            if not stress_mode and abs(actual_balance) > 1:
                raise ValueError("Unbalanced topology requires stress mode.")
            heights[event_id] = actual_height

        rotation_fields = ("ll_rotations", "rr_rotations", "lr_rotations", "rl_rotations")
        rotation_counts = {}
        for field in rotation_fields:
            count = metrics.get(field)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError(f"Rotation metric {field} must be non-negative.")
            rotation_counts[field] = count
        for field, count in rotation_counts.items():
            setattr(tree, field, count)
        return tree

    def add_event(self, event: Event) -> bool:
        if event.timestamp > self.simulation_clock:
            raise ValueError("Event time cannot be later than the simulation clock.")
        if (
            event.id in self.event_manager.active_events
            or event.id in self.event_manager.deleted_ids
        ):
            return False

        self._push_full_undo_state()
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
            self._push_full_undo_state()
            existing.accepted_stations.add(event.station)
            self.auditor.log_event(
                "ADD_EVENT_REPORT",
                f"Station {event.station} reported {existing.display_id}",
            )
            return "station_added"

        if not self.add_event(event):
            return "id_unavailable"
        return "created"

    def enqueue_event_report(self, report_data: dict) -> None:
        """Validate and append one station report to the FIFO queue."""
        event = self._event_from_report(report_data)
        if not event.station:
            raise ValueError("A queued report must include a reporting station.")
        if event.timestamp > self.simulation_clock:
            raise ValueError("Report time cannot be later than the simulation clock.")

        self._push_full_undo_state()
        self.report_queue.enqueue(
            {
                "event_id": event.id,
                "magnitude": event.magnitude,
                "depth": event.depth,
                "x": event.x,
                "y": event.y,
                "timestamp": event.timestamp.isoformat(),
                "station": event.station,
                "is_populated": event.is_populated,
                "revision": event.revision,
            }
        )
        self.auditor.log_event(
            "QUEUE_EVENT_REPORT",
            f"Queued revision {event.revision} of {event.display_id}",
        )

    def process_next_event_report(self) -> str:
        """Process one queued report and return its outcome classification."""
        if self.report_queue.is_empty():
            return "empty"

        report = self.report_queue.to_list()[0]
        incoming = self._event_from_report(report)
        if not incoming.station:
            raise ValueError("A queued report must include a reporting station.")

        self._push_full_undo_state()
        self.report_queue.dequeue()
        existing = self.event_manager.get_event(incoming.id)

        if existing is None:
            archived = self.event_manager.archived_events.get(incoming.id)
            if incoming.id in self.event_manager.deleted_ids:
                result = "id_unavailable"
            elif archived is not None:
                if incoming.revision < archived.revision:
                    result = "stale"
                elif incoming.revision == archived.revision:
                    if not self._same_reported_event(archived, incoming):
                        result = "conflict"
                    elif incoming.station in archived.accepted_stations:
                        result = "duplicate"
                    else:
                        archived.accepted_stations.add(incoming.station)
                        result = "confirmed_archived"
                else:
                    self._apply_report_revision(
                        archived, incoming, in_active_tree=False
                    )
                    del self.event_manager.archived_events[incoming.id]
                    self.event_manager.active_events[incoming.id] = archived
                    self.tree.insert(
                        archived,
                        auto_balance=not self.stress_manager.is_stress_mode,
                    )
                    result = "reactivated"
            else:
                if not self.event_manager.add_event(
                    incoming,
                    auto_balance=not self.stress_manager.is_stress_mode,
                ):
                    result = "id_unavailable"
                else:
                    result = "created"
        elif incoming.revision < existing.revision:
            result = "stale"
        elif incoming.revision == existing.revision:
            if not self._same_reported_event(existing, incoming):
                result = "conflict"
            elif incoming.station in existing.accepted_stations:
                result = "duplicate"
            else:
                existing.accepted_stations.add(incoming.station)
                result = "confirmed"
        else:
            self._apply_report_revision(existing, incoming)
            result = "updated"

        self.auditor.log_event(
            "PROCESS_EVENT_REPORT",
            f"Processed revision {incoming.revision} of "
            f"{incoming.display_id}: {result}",
        )
        if result in ("updated", "reactivated"):
            self.operation_counters["corrections_accepted"] += 1
        elif result in ("stale", "id_unavailable"):
            self.operation_counters["reports_discarded"] += 1
        elif result == "conflict":
            self.operation_counters["conflicts"] += 1
        return result

    def _push_full_undo_state(self) -> None:
        self.undo_stack.push(self._capture_state())

    def _capture_state(self) -> dict:
        return deepcopy(
            {
                "tree": self.tree,
                "active_events": self.event_manager.active_events,
                "archived_events": self.event_manager.archived_events,
                "deleted_ids": self.event_manager.deleted_ids,
                "reports": self.report_queue.to_list(),
                "stress_mode": self.stress_manager.is_stress_mode,
                "costly_access_limit": self.costly_access_limit,
                "archive_age_threshold_hours": self.archive_age_threshold_hours,
                "simulation_clock": self.simulation_clock,
                "replica_manager": self.replica_manager,
                "map_manager": self.map_manager,
                "operation_counters": self.operation_counters,
            }
        )

    def _restore_captured_state(self, state: dict) -> None:
        self.tree = state["tree"]
        self.event_manager = EventManager(self.tree)
        self.event_manager.active_events = state["active_events"]
        self.event_manager.archived_events = state["archived_events"]
        self.event_manager.deleted_ids = state["deleted_ids"]
        self.stress_manager = StressManager(self.tree)
        self.costly_access_limit = state["costly_access_limit"]
        self.archive_age_threshold_hours = state[
            "archive_age_threshold_hours"
        ]
        self.simulation_clock = state["simulation_clock"]
        self.replica_manager = state["replica_manager"]
        self.map_manager = state["map_manager"]
        self.operation_counters = state["operation_counters"]
        if state["stress_mode"]:
            self.stress_manager.enable_stress_mode()
        self.report_queue.restore(state["reports"])

    def _apply_report_revision(
        self,
        existing: Event,
        incoming: Event,
        in_active_tree: bool = True,
    ) -> None:
        old_key = existing.key
        if in_active_tree and old_key != incoming.key:
            self.tree.delete(
                old_key,
                auto_balance=not self.stress_manager.is_stress_mode,
            )

        existing.magnitude = incoming.magnitude
        existing.depth = incoming.depth
        existing.x = incoming.x
        existing.y = incoming.y
        existing.timestamp = incoming.timestamp
        existing.station = incoming.station
        existing.is_populated = incoming.is_populated
        existing.priority = incoming.priority
        existing.revision = incoming.revision
        existing.status = "PENDING"
        existing.accepted_stations.add(incoming.station)
        if in_active_tree and old_key != existing.key:
            self.tree.insert(
                existing,
                auto_balance=not self.stress_manager.is_stress_mode,
            )

    def set_archive_age_threshold(self, hours: float) -> None:
        if isinstance(hours, bool) or not isinstance(hours, (int, float)):
            raise ValueError("Archive age threshold T must be a positive number.")
        if not math.isfinite(hours) or hours <= 0:
            raise ValueError("Archive age threshold T must be a positive number.")
        self._push_full_undo_state()
        self.archive_age_threshold_hours = float(hours)
        self.auditor.log_event(
            "SET_ARCHIVE_THRESHOLD",
            f"Set archive threshold to {self.archive_age_threshold_hours:g} hours",
        )

    def advance_simulation_clock(self, hours: float) -> datetime:
        if isinstance(hours, bool) or not isinstance(hours, (int, float)):
            raise ValueError("Clock advance must be a positive number of hours.")
        if not math.isfinite(hours) or hours <= 0:
            raise ValueError("Clock advance must be a positive number of hours.")
        self._push_full_undo_state()
        self.simulation_clock += timedelta(hours=float(hours))
        self.auditor.log_event(
            "ADVANCE_SIMULATION_CLOCK",
            f"Advanced simulation clock by {hours:g} hours",
        )
        return self.simulation_clock

    def preview_archive_candidate(self) -> dict | None:
        """Select the largest eligible active subtree using its initial topology."""
        if self.tree.root is None:
            return None

        best_candidate = None
        stack = [(self.tree.root, 0, False)]
        subtree_eligible = {}
        subtree_count = {}
        while stack:
            node, depth, visited = stack.pop()
            if node is None:
                continue
            if not visited:
                stack.append((node, depth, True))
                stack.append((node.getRightChild(), depth + 1, False))
                stack.append((node.getLeftChild(), depth + 1, False))
                continue

            event = node.getValue()
            event_age = (self.simulation_clock - event.timestamp).total_seconds() / 3600
            eligible = (
                event.priority == 1
                and event_age > self.archive_age_threshold_hours
            )
            subtree_count[node] = (
                subtree_count.get(node.getLeftChild(), 0)
                + subtree_count.get(node.getRightChild(), 0)
                + 1
            )
            subtree_eligible[node] = (
                eligible
                and subtree_eligible.get(node.getLeftChild(), True)
                and subtree_eligible.get(node.getRightChild(), True)
            )
            if subtree_eligible[node]:
                rank = (subtree_count[node], depth, event.id)
                if best_candidate is None or rank > best_candidate[0]:
                    best_candidate = (rank, node, depth)

        if best_candidate is None:
            return None
        _, root, depth = best_candidate
        selected_events = []
        nodes = [root]
        while nodes:
            node = nodes.pop()
            selected_events.append(node.getValue())
            if node.getLeftChild() is not None:
                nodes.append(node.getLeftChild())
            if node.getRightChild() is not None:
                nodes.append(node.getRightChild())
        return {
            "root_event": root.getValue(),
            "depth": depth,
            "events": selected_events,
            "count": len(selected_events),
            "threshold_hours": self.archive_age_threshold_hours,
        }

    def archive_eligible_branch(self) -> dict | None:
        candidate = self.preview_archive_candidate()
        if candidate is None:
            return None

        self._push_full_undo_state()
        auto_balance = not self.stress_manager.is_stress_mode
        archived_ids = {event.id for event in candidate["events"]}
        for event_id in archived_ids:
            event = self.event_manager.active_events.pop(event_id)
            self.tree.delete(event.key, auto_balance=auto_balance)
            self.event_manager.archived_events[event_id] = event

        result = {
            "root_event": candidate["root_event"],
            "depth": candidate["depth"],
            "events": candidate["events"],
            "count": candidate["count"],
        }
        self.operation_counters["mass_archives"] += 1
        self.operation_counters["events_archived"] += result["count"]
        self.auditor.log_event(
            "ARCHIVE_BRANCH",
            f"Archived {result['count']} events rooted at "
            f"{result['root_event'].display_id}",
        )
        return result

    @staticmethod
    def _event_from_report(report: dict) -> Event:
        if not isinstance(report, dict):
            raise TypeError("A queued report must be a dictionary.")

        revision = report.get("revision", 1)
        if (
            isinstance(revision, bool)
            or not isinstance(revision, int)
            or revision < 1
        ):
            raise ValueError("Report revision must be a positive integer.")
        station = report.get("station", "")
        if not isinstance(station, str):
            raise ValueError("Reporting station must be text.")

        return Event(
            event_id=report.get("event_id", report.get("id")),
            magnitude=report["magnitude"],
            depth=report.get("depth", report.get("z")),
            x=report["x"],
            y=report["y"],
            timestamp=report["timestamp"],
            station=station.strip(),
            is_populated=report.get(
                "is_populated",
                report.get("is_in_populated_zone", False),
            ),
            revision=revision,
        )

    @staticmethod
    def _same_reported_event(existing: Event, incoming: Event) -> bool:
        return (
            existing.magnitude == incoming.magnitude
            and existing.depth == incoming.depth
            and existing.x == incoming.x
            and existing.y == incoming.y
            and existing.timestamp == incoming.timestamp
            and existing.is_populated == incoming.is_populated
        )

    def update_event(self, event_id: int, new_data: dict) -> bool:
        if self.event_manager.get_event(event_id) is None:
            return False

        snapshot = self._capture_state()
        self.undo_stack.push(snapshot)
        auto_balance = not self.stress_manager.is_stress_mode
        try:
            updated = self.event_manager.update_event(
                event_id,
                new_data,
                auto_balance=auto_balance,
            )
        except Exception:
            self.undo_stack.pop()
            self._restore_captured_state(snapshot)
            raise

        if updated:
            self.operation_counters["corrections_accepted"] += 1
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

        depth = comparisons - 1
        return {
            "event": event,
            "depth": depth,
            "comparisons": comparisons,
            "access_costly": event.priority == 3 and depth > self.costly_access_limit,
            "cost_threshold": self.costly_access_limit,
        }

    def set_costly_access_limit(self, limit: int) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError("Costly-access limit L must be a non-negative integer.")
        if limit == self.costly_access_limit:
            return
        self._push_full_undo_state()
        self.costly_access_limit = limit

    def set_association_limits(self, time_window_hours: float, distance_km: float) -> None:
        if (
            isinstance(time_window_hours, bool)
            or isinstance(distance_km, bool)
            or not isinstance(time_window_hours, (int, float))
            or not isinstance(distance_km, (int, float))
            or not math.isfinite(time_window_hours)
            or not math.isfinite(distance_km)
            or time_window_hours <= 0
            or distance_km <= 0
        ):
            raise ValueError(
                "Association limits W and R must be positive finite numbers."
            )
        if (
            time_window_hours == self.replica_manager.W_hours
            and distance_km == self.replica_manager.R_km
        ):
            return
        self._push_full_undo_state()
        self.replica_manager.configure(time_window_hours, distance_km)
        self.auditor.log_event(
            "SET_ASSOCIATION_LIMITS",
            f"Set W={self.replica_manager.W_hours:g}, "
            f"R={self.replica_manager.R_km:g}",
        )

    def start_stress_mode(self) -> None:
        if self.stress_manager.is_stress_mode:
            return
        self._push_full_undo_state()
        self.stress_manager.enable_stress_mode()
        self.auditor.log_event("START_STRESS_MODE", "Deferred AVL rotations")

    def recover_stress_mode(self) -> int:
        if not self.stress_manager.is_stress_mode:
            return 0
        self._push_full_undo_state()
        try:
            rotations = self.stress_manager.recover_avl_balance()
            audit = self.verify_structure()
            if not audit["valid"]:
                raise RuntimeError(
                    "AVL recovery failed structural audit: "
                    + "; ".join(audit["errors"])
                )
        except Exception:
            snapshot = self.undo_stack.pop()
            self._restore_captured_state(snapshot)
            raise
        self.auditor.log_event(
            "RECOVER_STRESS_MODE",
            f"Restored AVL balance with {rotations} rotations",
        )
        return rotations

    def verify_structure(self) -> dict:
        errors = []
        expected_imbalances = []
        seen_ids = set()
        visited_nodes = set()
        active = self.event_manager.active_events
        stack = [(self.tree.root, None, None, None, 0)]
        while stack:
            node, parent, lower, upper, depth = stack.pop()
            if node is None:
                continue
            if node in visited_nodes:
                errors.append("AVL contains a cycle or a node with multiple parents.")
                continue
            visited_nodes.add(node)
            event = node.getValue()
            if node.getFather() is not parent:
                errors.append(f"{event.display_id}: invalid parent link.")
            if lower is not None and not lower < node.key:
                errors.append(f"{event.display_id}: violates global BST lower bound.")
            if upper is not None and not node.key < upper:
                errors.append(f"{event.display_id}: violates global BST upper bound.")
            if event.id in seen_ids:
                errors.append(f"{event.display_id}: duplicate ID in active tree.")
            seen_ids.add(event.id)
            if active.get(event.id) is not event:
                errors.append(f"{event.display_id}: active catalog/tree mismatch.")
            if event.priority != event.calculate_priority():
                errors.append(f"{event.display_id}: stored priority is stale.")
            stack.append((node.getRightChild(), node, node.key, upper, depth + 1))
            stack.append((node.getLeftChild(), node, lower, node.key, depth + 1))

        calculated_heights = {}
        height_seen = set()
        height_stack = (
            [(self.tree.root, False)] if self.tree.root is not None else []
        )
        while height_stack:
            node, expanded = height_stack.pop()
            if not expanded:
                if node in height_seen:
                    continue
                height_seen.add(node)
                height_stack.append((node, True))
                if (
                    node.getRightChild() is not None
                    and node.getRightChild() not in height_seen
                ):
                    height_stack.append((node.getRightChild(), False))
                if (
                    node.getLeftChild() is not None
                    and node.getLeftChild() not in height_seen
                ):
                    height_stack.append((node.getLeftChild(), False))
                continue
            left_height = calculated_heights.get(node.getLeftChild(), -1)
            right_height = calculated_heights.get(node.getRightChild(), -1)
            expected_height = 1 + max(left_height, right_height)
            calculated_heights[node] = expected_height
            if node.getHeight() != expected_height:
                errors.append(
                    f"{node.getValue().display_id}: stored height "
                    f"{node.getHeight()} should be {expected_height}."
                )
            if (
                abs(left_height - right_height) > 1
            ):
                imbalance = (
                    f"{node.getValue().display_id}: balance factor "
                    f"{left_height - right_height} "
                    f"(left height {left_height}, right height {right_height})."
                )
                if self.stress_manager.is_stress_mode:
                    expected_imbalances.append(imbalance)
                else:
                    errors.append(imbalance)

        if seen_ids != set(active):
            errors.append("Active catalog contains events missing from the AVL.")
        archived_ids = set(self.event_manager.archived_events)
        if archived_ids & seen_ids or archived_ids & self.event_manager.deleted_ids:
            errors.append("Active, archived, and deleted event IDs overlap.")
        if set(active) & self.event_manager.deleted_ids:
            errors.append("An active event ID is also marked deleted.")

        all_events = list(active.values()) + list(
            self.event_manager.archived_events.values()
        )
        for event in all_events:
            candidates = self.replica_manager.get_candidates(event, all_events)
            selected = self.replica_manager.select_main_reference(event, candidates)
            if selected is not None and selected not in candidates:
                errors.append(
                    f"{event.display_id}: selected replica reference is invalid."
                )
        return {
            "valid": not errors,
            "errors": errors,
            "expected_imbalances": expected_imbalances,
            "stress_mode": self.stress_manager.is_stress_mode,
            "nodes_examined": len(visited_nodes),
            "active_events": len(active),
            "archived_events": len(archived_ids),
        }

    def query_top_pending(self, count: int) -> dict:
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValueError("Query count k must be a positive integer.")
        result = []
        examined = 0
        stack = []
        node = self.tree.root
        while (node is not None or stack) and len(result) < count:
            while node is not None:
                stack.append(node)
                node = node.getRightChild()
            node = stack.pop()
            examined += 1
            if node.getValue().status == "PENDING":
                result.append(node.getValue())
            node = node.getLeftChild()
        return {"events": result, "nodes_examined": examined}

    def query_magnitude_range(self, minimum: float, maximum: float) -> dict:
        if (
            isinstance(minimum, bool)
            or isinstance(maximum, bool)
            or not isinstance(minimum, (int, float))
            or not isinstance(maximum, (int, float))
            or not math.isfinite(minimum)
            or not math.isfinite(maximum)
            or minimum > maximum
        ):
            raise ValueError("Magnitude interval must be finite and ordered.")
        events = []
        examined = 0
        stack = [self.tree.root] if self.tree.root is not None else []
        while stack:
            node = stack.pop()
            examined += 1
            event = node.getValue()
            if minimum <= event.magnitude <= maximum:
                events.append(event)
            if node.getLeftChild() is not None:
                stack.append(node.getLeftChild())
            if node.getRightChild() is not None:
                stack.append(node.getRightChild())
        events.sort(key=lambda event: event.key)
        return {"events": events, "nodes_examined": examined}

    def query_shallow_events_by_date(
        self, maximum_depth: float, start: datetime, end: datetime
    ) -> dict:
        if (
            isinstance(maximum_depth, bool)
            or not isinstance(maximum_depth, (int, float))
            or not math.isfinite(maximum_depth)
            or maximum_depth < 0
        ):
            raise ValueError("Maximum hypocenter depth must be non-negative.")
        start_time = self._normalize_datetime(start)
        end_time = self._normalize_datetime(end)
        if start_time > end_time:
            raise ValueError("Date interval start must not be after its end.")
        events = []
        examined = 0
        stack = [self.tree.root] if self.tree.root is not None else []
        while stack:
            node = stack.pop()
            examined += 1
            event = node.getValue()
            if (
                event.depth <= maximum_depth
                and start_time <= event.timestamp <= end_time
            ):
                events.append(event)
            if node.getLeftChild() is not None:
                stack.append(node.getLeftChild())
            if node.getRightChild() is not None:
                stack.append(node.getRightChild())
        events.sort(key=lambda event: (event.timestamp, event.id))
        return {"events": events, "nodes_examined": examined}

    def query_associations(self, event_id: int) -> dict | None:
        active_events, nodes_examined = self._events_in_tree()
        all_events = active_events + list(
            self.event_manager.archived_events.values()
        )
        target = next((event for event in all_events if event.id == event_id), None)
        if target is None:
            return None
        candidates = self.replica_manager.get_candidates(target, all_events)
        selected = self.replica_manager.select_main_reference(target, candidates)
        archived_ids = set(self.event_manager.archived_events)
        references = []
        for event in all_events:
            if event.id == target.id:
                continue
            event_candidates = self.replica_manager.get_candidates(event, all_events)
            if (
                self.replica_manager.select_main_reference(event, event_candidates)
                is target
            ):
                references.append(event)
        return {
            "event": target,
            "candidates": candidates,
            "event_is_archived": target.id in archived_ids,
            "main_reference": selected,
            "main_reference_is_archived": (
                selected is not None and selected.id in archived_ids
            ),
            "referenced_by": references,
            "referenced_by_archived": {
                event.id: event.id in archived_ids for event in references
            },
            "candidate_archived": {
                event.id: event.id in archived_ids for event in candidates
            },
            "nodes_examined": nodes_examined,
        }

    def _events_in_tree(self) -> tuple[list[Event], int]:
        events = []
        examined = 0
        stack = [self.tree.root] if self.tree.root is not None else []
        while stack:
            node = stack.pop()
            examined += 1
            events.append(node.getValue())
            if node.getRightChild() is not None:
                stack.append(node.getRightChild())
            if node.getLeftChild() is not None:
                stack.append(node.getLeftChild())
        return events, examined

    def query_costly_access_events(self) -> dict:
        events = []
        examined = 0
        stack = (
            [(self.tree.root, 0)] if self.tree.root is not None else []
        )
        while stack:
            node, depth = stack.pop()
            examined += 1
            event = node.getValue()
            if event.priority == 3 and depth > self.costly_access_limit:
                events.append(
                    {
                        "event": event,
                        "depth": depth,
                        "comparisons": depth + 1,
                        "limit": self.costly_access_limit,
                    }
                )
            if node.getRightChild() is not None:
                stack.append((node.getRightChild(), depth + 1))
            if node.getLeftChild() is not None:
                stack.append((node.getLeftChild(), depth + 1))
        return {"events": events, "nodes_examined": examined}

    def get_dashboard_metrics(self) -> dict:
        """Return live structural, workload, priority, and rotation indicators."""
        preorder = []
        inorder = []
        postorder = []
        level_order = []
        leaves = 0

        if self.tree.root is not None:
            stack = [(self.tree.root, False)]
            while stack:
                node, expanded = stack.pop()
                if expanded:
                    postorder.append(node.getValue())
                    continue
                preorder.append(node.getValue())
                if node.getLeftChild() is None and node.getRightChild() is None:
                    leaves += 1
                stack.append((node, True))
                if node.getRightChild() is not None:
                    stack.append((node.getRightChild(), False))
                if node.getLeftChild() is not None:
                    stack.append((node.getLeftChild(), False))

            stack = []
            node = self.tree.root
            while node is not None or stack:
                while node is not None:
                    stack.append(node)
                    node = node.getLeftChild()
                node = stack.pop()
                inorder.append(node.getValue())
                node = node.getRightChild()

            queue = [self.tree.root]
            queue_index = 0
            while queue_index < len(queue):
                node = queue[queue_index]
                queue_index += 1
                level_order.append(node.getValue())
                if node.getLeftChild() is not None:
                    queue.append(node.getLeftChild())
                if node.getRightChild() is not None:
                    queue.append(node.getRightChild())

        active_events = list(self.event_manager.active_events.values())
        costly_access = self.query_costly_access_events()["events"]
        rotation_cases = {
            "LL": self.tree.ll_rotations,
            "RR": self.tree.rr_rotations,
            "LR": self.tree.lr_rotations,
            "RL": self.tree.rl_rotations,
        }
        return {
            "active_events": len(active_events),
            "archived_events": len(self.event_manager.archived_events),
            "height": self.tree.root.getHeight() if self.tree.root else -1,
            "leaves": leaves,
            "priority_counts": {
                priority: sum(
                    event.priority == priority for event in active_events
                )
                for priority in (1, 2, 3)
            },
            "pending_events": sum(
                event.status == "PENDING" for event in active_events
            ),
            "costly_access_events": len(costly_access),
            "rotation_cases": rotation_cases,
            "simple_left_rotations": (
                rotation_cases["RR"] + rotation_cases["RL"]
            ),
            "simple_right_rotations": (
                rotation_cases["LL"] + rotation_cases["LR"]
            ),
            "operation_counters": self.operation_counters.copy(),
            "traversals": {
                "inorder": inorder,
                "preorder": preorder,
                "postorder": postorder,
                "level_order": level_order,
            },
        }

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError("Query date bounds must be datetime values.")
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def build_comparison_tree(self) -> BinarySearchTree:
        """Build an unbalanced BST from the active events in arrival order."""
        return BinarySearchTree(self.events)

    def mark_event_as_reviewed(self, event_id: int) -> bool:
        event = self.event_manager.get_event(event_id)
        if event is None or event.status == "REVIEWED":
            return False

        self._push_full_undo_state()
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

        self._push_full_undo_state()
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

        previous_state = self.undo_stack.pop()
        if "tree" not in previous_state:
            raise RuntimeError("Undo snapshot is incomplete; state was not changed.")

        self._restore_captured_state(previous_state)
        self.auditor.log_event("UNDO", "Restored the previous event state")
        return True
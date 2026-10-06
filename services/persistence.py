# services/persistence.py
from datetime import datetime
import json
import os
import tempfile

from core.event import Event


# handles file operations and directory management
class Archiver:

    @staticmethod
    def ensure_directory_exists(filepath: str) -> None:
        # create the parent directory when it does not exist
        dirname = os.path.dirname(filepath)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)

    @staticmethod
    def file_exists(filepath: str) -> bool:
        # check whether the given path exists
        return os.path.exists(filepath)


# handles system operation logging and audit trails
class Auditor:

    def __init__(self, log_filepath: str = "logs/system_audit.log"):
        # prepare the audit log location
        self.log_filepath = log_filepath
        Archiver.ensure_directory_exists(self.log_filepath)

    def log_event(self, action: str, details: str) -> None:
        # append an action and timestamp to the audit file
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] ACTION: {action} | DETAILS: {details}\n"

        try:
            with open(self.log_filepath, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write audit log: {e}")


# manages scenario import and export in JSON format
class PersistenceManager:

    def __init__(self, auditor: Auditor = None):
        # use the supplied auditor or create a default one
        self.auditor = auditor or Auditor()

    @staticmethod
    def _event_to_dict(event: Event) -> dict:
        # convert an event into its JSON-compatible representation
        return {
            "id": event.id,
            "magnitude": event.magnitude,
            "depth": event.depth,
            "x": event.x,
            "y": event.y,
            "timestamp": event.timestamp.isoformat(timespec="seconds"),
            "station": event.station,
            "accepted_stations": sorted(event.accepted_stations),
            "revision": event.revision,
            "is_populated": event.is_populated,
            "priority": event.priority,
            "status": event.status,
        }

    def save_scenario(self, controller, filepath: str, version_name: str = "") -> None:
        # save the complete state and tree topology atomically
        nodes = []
        stack = [controller.tree.root] if controller.tree.root is not None else []
        while stack:
            node = stack.pop()
            event = node.getValue()
            left = node.getLeftChild()
            right = node.getRightChild()
            nodes.append(
                {
                    "id": event.id,
                    "left": left.getValue().id if left is not None else None,
                    "right": right.getValue().id if right is not None else None,
                    "height": node.getHeight(),
                    "balance_factor": controller.tree._get_balance_factor(node),
                }
            )
            if right is not None:
                stack.append(right)
            if left is not None:
                stack.append(left)

        zones = [
            {
                "name": zone.name,
                "x_min": zone.x_min,
                "x_max": zone.x_max,
                "y_min": zone.y_min,
                "y_max": zone.y_max,
                "is_populated": zone.is_populated,
            }
            for zone in controller.map_manager.zones
        ]
        data = {
            "format": "SismoLabScenario",
            "format_version": 2,
            "version_name": version_name,
            "system_config": {
                "W_hours": controller.replica_manager.W_hours,
                "R_km": controller.replica_manager.R_km,
                "L": controller.costly_access_limit,
                "T_hours": controller.archive_age_threshold_hours,
                "simulation_clock": controller.simulation_clock.isoformat(),
                "stress_mode": controller.stress_manager.is_stress_mode,
            },
            "active_events": [
                self._event_to_dict(event) for event in controller.events
            ],
            "archived_events": [
                self._event_to_dict(event)
                for event in controller.event_manager.archived_events.values()
            ],
            "deleted_ids": sorted(controller.event_manager.deleted_ids),
            "report_queue": controller.report_queue.to_list(),
            "operation_counters": controller.operation_counters.copy(),
            "zones": zones,
            "tree": {
                "root_id": (
                    controller.tree.root.getValue().id
                    if controller.tree.root is not None
                    else None
                ),
                "nodes": nodes,
            },
            "metrics": {
                "ll_rotations": controller.tree.ll_rotations,
                "rr_rotations": controller.tree.rr_rotations,
                "lr_rotations": controller.tree.lr_rotations,
                "rl_rotations": controller.tree.rl_rotations,
            },
        }

        directory = os.path.dirname(os.path.abspath(filepath))
        os.makedirs(directory, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=directory,
                prefix=".sismolab-",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = temporary_file.name
                json.dump(data, temporary_file, indent=4, ensure_ascii=False)
                temporary_file.write("\n")
            os.replace(temporary_path, filepath)
        except Exception:
            if temporary_path and os.path.exists(temporary_path):
                os.remove(temporary_path)
            raise

        self.auditor.log_event(
            "SAVE_SCENARIO",
            f"Saved scenario '{version_name}' to {filepath}",
        )

    @staticmethod
    def _require_list(data: dict, field: str) -> list:
        # validate that a scenario field contains a list
        value = data.get(field)
        if not isinstance(value, list):
            raise ValueError(f"Scenario field '{field}' must be a list.")
        return value

    def load_from_json(self, filepath: str) -> dict:
        # load JSON data and convert event records into Event objects
        if not Archiver.file_exists(filepath):
            self.auditor.log_event(
                "LOAD_ERROR", f"File not found at {filepath}"
            )
            raise FileNotFoundError(f"The file {filepath} does not exist.")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            if data.get("format") == "SismoLabScenario":
                if data.get("format_version") != 2:
                    raise ValueError("Unsupported SismoLab scenario version.")
                data["active_events"] = [
                    self._event_from_dict(event)
                    for event in self._require_list(data, "active_events")
                ]
                data["archived_events"] = [
                    self._event_from_dict(event)
                    for event in self._require_list(data, "archived_events")
                ]
            else:
                raw_events = data.get("events", [])
                data["events"] = [
                    self._event_from_dict(event) for event in raw_events
                ]

        elif isinstance(data, list):
            data = [self._event_from_dict(event) for event in data]

        self.auditor.log_event(
            "LOAD_JSON",
            f"Successfully loaded data from {filepath}",
        )
        return data

    @staticmethod
    def _event_from_dict(payload: dict) -> Event:
        # build an Event from current or legacy JSON field names
        revision = payload.get("revision", 1)
        if (
            isinstance(revision, bool)
            or not isinstance(revision, int)
            or revision < 1
        ):
            raise ValueError("Event revision must be a positive integer.")
        station = payload.get("station", "")
        if not isinstance(station, str):
            raise ValueError("Event station must be text.")
        event = Event(
            event_id=payload["id"],
            magnitude=payload["magnitude"],
            depth=payload["depth"] if "depth" in payload else payload["z"],
            x=payload["x"],
            y=payload["y"],
            timestamp=payload["timestamp"],
            station=station,
            is_populated=payload.get(
                "is_in_populated_zone", payload.get("is_populated", False)
            ),
            revision=revision,
        )
        stored_priority = payload.get("priority")
        if stored_priority is not None and stored_priority != event.priority:
            raise ValueError(
                f"Stored priority does not match event {event.display_id} data."
            )
        status = payload.get("status", "PENDING")
        if status not in ("PENDING", "REVIEWED"):
            raise ValueError(f"Event {event.display_id} has an invalid status.")
        event.status = status
        accepted_stations = payload.get("accepted_stations")
        if accepted_stations is not None:
            if not isinstance(accepted_stations, list) or not all(
                isinstance(station, str) for station in accepted_stations
            ):
                raise ValueError("accepted_stations must be a list of station names.")
            if len(set(accepted_stations)) != len(accepted_stations):
                raise ValueError("accepted_stations cannot contain duplicates.")
            event.accepted_stations.update(accepted_stations)
        return event
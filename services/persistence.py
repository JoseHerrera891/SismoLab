# services/persistence.py
from datetime import datetime
import json
import os

from core.event import Event


class Archiver:
    """
    Handles file system operations, path validations, and directory management.
    """

    @staticmethod
    def ensure_directory_exists(filepath: str) -> None:
        """
        Ensures that the directory for a given filepath exists.
        Creates it if it does not exist.
        """
        dirname = os.path.dirname(filepath)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)

    @staticmethod
    def file_exists(filepath: str) -> bool:
        """
        Checks if a file exists at the specified path.
        """
        return os.path.exists(filepath)


class Auditor:
    """
    Handles system operation logging and audit trails for seismic events.
    """

    def __init__(self, log_filepath: str = "logs/system_audit.log"):
        self.log_filepath = log_filepath
        Archiver.ensure_directory_exists(self.log_filepath)

    def log_event(self, action: str, details: str) -> None:
        """
        Logs a system action with an ISO timestamp into the audit file.
        """
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] ACTION: {action} | DETAILS: {details}\n"

        try:
            with open(self.log_filepath, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Failed to write audit log: {e}")


class PersistenceManager:
    """
    Handles system state export and import operations in JSON format.
    Integrated with Archiver and Auditor services.
    """

    def __init__(self, auditor: Auditor = None):
        self.auditor = auditor or Auditor()

    def export_to_json(
        self, events: list, map_manager, replica_manager, filepath: str
    ) -> bool:
        """
        Exports the list of seismic events, zone classifications,
        and replica associations to a structured JSON file.
        """
        try:
            events_data = []

            for event in events:
                # 1. Determine if the epicenter lies within a populated zone
                is_populated = map_manager.is_in_populated_zone(
                    event.x, event.y
                )

                # 2. Retrieve candidate reference events and select the main reference
                candidates = replica_manager.get_candidates(event, events)
                main_ref = replica_manager.select_main_reference(
                    event, candidates
                )

                # 3. Format event information into a dictionary
                event_dict = {
                    "id": event.id,
                    "x": event.x,
                    "y": event.y,
                    "z": event.depth,
                    "magnitude": event.magnitude,
                    "timestamp": (
                        event.timestamp.isoformat()
                        if isinstance(event.timestamp, datetime)
                        else str(event.timestamp)
                    ),
                    "station": event.station,
                    "is_in_populated_zone": is_populated,
                    "main_reference_id": main_ref.id if main_ref else None,
                    "candidate_ids": [c.id for c in candidates],
                }

                events_data.append(event_dict)

            # Main JSON payload structure
            data_to_save = {
                "system_config": {
                    "W_hours": replica_manager.W_hours,
                    "R_km": replica_manager.R_km,
                },
                "events_count": len(events_data),
                "events": events_data,
            }

            # Ensure directory exists using Archiver
            Archiver.ensure_directory_exists(filepath)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)

            # Audit log entry
            self.auditor.log_event(
                "EXPORT_JSON",
                f"Successfully exported {len(events_data)} events to {filepath}",
            )
            return True

        except Exception as e:
            self.auditor.log_event(
                "EXPORT_ERROR", f"Failed to export JSON to {filepath}: {e}"
            )
            print(f"Error exporting to JSON: {e}")
            return False

    def load_from_json(self, filepath: str) -> dict:
        """
        Reads a JSON file and converts event dictionaries into structured Event objects.
        """
        if not Archiver.file_exists(filepath):
            self.auditor.log_event(
                "LOAD_ERROR", f"File not found at {filepath}"
            )
            raise FileNotFoundError(f"The file {filepath} does not exist.")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            raw_events = data.get("events", [])
            data["events"] = [self._event_from_dict(event) for event in raw_events]

        elif isinstance(data, list):
            data = [self._event_from_dict(event) for event in data]

        self.auditor.log_event(
            "LOAD_JSON",
            f"Successfully loaded data from {filepath}",
        )
        return data

    @staticmethod
    def _event_from_dict(payload: dict) -> Event:
        """Build the core event model from current and legacy JSON field names."""
        return Event(
            event_id=payload["id"],
            magnitude=payload["magnitude"],
            depth=payload["depth"] if "depth" in payload else payload["z"],
            x=payload["x"],
            y=payload["y"],
            timestamp=payload["timestamp"],
            station=payload.get("station", ""),
            is_populated=payload.get(
                "is_in_populated_zone", payload.get("is_populated", False)
            ),
            revision=payload.get("revision", 1),
        )
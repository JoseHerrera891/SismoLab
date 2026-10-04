# services/persistence.py
from datetime import datetime
import json
import os


class PersistenceManager:
    """
    Handles system state export and import operations in JSON format.
    """

    @staticmethod
    def export_to_json(
        events: list, map_manager, replica_manager, filepath: str
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
                    "z": event.z,
                    "magnitude": event.magnitude,
                    "timestamp": (
                        event.timestamp.isoformat()
                        if isinstance(event.timestamp, datetime)
                        else str(event.timestamp)
                    ),
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

            # Ensure the target directory exists before writing
            dirname = os.path.dirname(filepath)
            if dirname and not os.path.exists(dirname):
                os.makedirs(dirname)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False

    @staticmethod
    def load_from_json(filepath: str) -> dict:
        """
        Reads and returns raw dictionary data from a JSON file.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"The file {filepath} does not exist.")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data
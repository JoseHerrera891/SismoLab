# services/map_manager.py

import json
import math


class Zone:

    """Represents a rectangular zone on the 1000x1000 km plane."""
    def __init__(self, name: str, x_min: float, x_max: float, y_min: float, y_max: float, is_populated: bool):
        self.name = name
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.is_populated = is_populated

    def contains(self, x: float, y: float) -> bool:
        """
        Checks whether the coordinates (x, y) fall inside the zone or on its boundary.
        """
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max


class MapManager:

    """Manages the geographic plane and evaluates whether an epicenter lies in a populated zone."""
    def __init__(self):
        self.width = 1000.0
        self.height = 1000.0
        self.zones: list[Zone] = []

    def add_zone(self, zone: Zone):
        """Adds a fixed zone to the map."""
        self.zones.append(zone)

    def load_zones(self, filepath: str) -> None:
        """Load rectangular zone definitions from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as zones_file:
            data = json.load(zones_file)

        if not isinstance(data, dict) or not isinstance(data.get("zones"), list):
            raise ValueError("Zones JSON must contain a 'zones' list.")

        loaded_zones = []
        for index, zone_data in enumerate(data["zones"]):
            if not isinstance(zone_data, dict):
                raise ValueError(f"Zone at index {index} must be an object.")

            name = zone_data.get("name")
            is_populated = zone_data.get("is_populated")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Zone at index {index} must have a name.")
            if not isinstance(is_populated, bool):
                raise ValueError(
                    f"Zone '{name}' must define is_populated as a boolean."
                )

            bounds = {}
            for field in ("x_min", "x_max", "y_min", "y_max"):
                value = zone_data.get(field)
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or not 0 <= value <= 1000
                ):
                    raise ValueError(
                        f"Zone '{name}' has an invalid {field}; "
                        "bounds must be between 0 and 1000 km."
                    )
                bounds[field] = float(value)

            if bounds["x_min"] > bounds["x_max"]:
                raise ValueError(f"Zone '{name}' has x_min greater than x_max.")
            if bounds["y_min"] > bounds["y_max"]:
                raise ValueError(f"Zone '{name}' has y_min greater than y_max.")

            loaded_zones.append(
                Zone(name.strip(), **bounds, is_populated=is_populated)
            )

        self.zones = loaded_zones

    def is_in_populated_zone(self, x: float, y: float) -> bool:
        """
        Section 3 rule:
        An epicenter belongs to a zone when it is inside or on its boundary.
        If it falls on the edge of two zones, it is classified as populated when at least
        one of the zones is marked as populated.
        """
        in_populated = False

        for zone in self.zones:
            if zone.contains(x, y):
                if zone.is_populated:
                    in_populated = True  # Priority: touching a populated zone makes it populated

        return in_populated
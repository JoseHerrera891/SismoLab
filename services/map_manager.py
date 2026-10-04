# services/map_manager.py

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
"""
Model representing a seismic event and priority calculation logic.
"""

from datetime import datetime

class Event:
    def __init__(self, event_id: int, magnitude: float, depth: float, x: float, y: float, timestamp: str, station: str, is_populated: bool = False, revision: int = 1):
        
        self._validate_inputs(event_id, magnitude, depth, x, y)
        
        self.id = event_id  # Integer (1 to 999999)
        self.magnitude = round(float(magnitude), 1)
        self.depth = round(float(depth), 1)
        self.x = round(float(x), 1)
        self.y = round(float(y), 1)
        self.timestamp = timestamp  # ISO 8601 string
        self.station = station
        self.is_populated = is_populated
        self.revision = revision
        self.status = "PENDING"  # "PENDING" or "REVIEWED"
        self.accepted_stations = {station}
        
        # Derived fields
        self.priority = self.calculate_priority()
        
    def _validate_inputs(self, event_id, magnitude, depth, x, y):
        if not (1 <= event_id <= 999999):
            raise ValueError("ID must be between 1 and 999999.")
        if not (-2.0 <= magnitude <= 10.0):
            raise ValueError("Magnitude must be between -2.0 and 10.0.")
        if not (0.0 <= depth <= 700.0):
            raise ValueError("Depth must be between 0.0 and 700.0 km.")
        if not (0.0 <= x <= 1000.0 and 0.0 <= y <= 1000.0):
            raise ValueError("Coordinates (x, y) must be within 0.0 and 1000.0 km.")

    def calculate_priority(self) -> int:
        """Calculates priority according to Section 4 rules."""
        if self.magnitude >= 6.0 or (self.magnitude >= 4.5 and self.depth <= 30.0 and self.is_populated):
            return 3
        elif self.magnitude >= 4.5:
            return 2
        return 1

    @property
    def key(self) -> tuple:
        """Returns key K = (P, M, I) for AVL comparison."""
        return (self.priority, self.magnitude, self.id)
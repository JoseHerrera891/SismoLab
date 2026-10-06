from datetime import datetime, timezone


# model for the seismic event and priority (value of the node)
class Event:
    def __init__(self, event_id: int, magnitude: float, depth: float,
                 x: float, y: float, timestamp, station: str = "",
                 is_populated: bool = False, revision: int = 1):

        self._id = self._normalize_event_id(event_id)
        self.magnitude = round(float(magnitude), 1)
        self.depth = round(float(depth), 1)
        self.x = round(float(x), 1)
        self.y = round(float(y), 1)
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        if not isinstance(timestamp, datetime):
            raise TypeError("Timestamp must be a datetime or an ISO 8601 string.")
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        self.timestamp = timestamp.astimezone(timezone.utc)
        self.station = station
        self.is_populated = is_populated
        self.revision = int(revision)

        self._validate_inputs(
            self.id, self.magnitude, self.depth, self.x, self.y
        )

        # Status can be 'PENDING' or 'REVIEWED'
        self.status = "PENDING"

        # Set of stations that have reported this accepted event
        self.accepted_stations = {station} if station else set()

        self.priority = self.calculate_priority()

    @staticmethod
    def _normalize_event_id(event_id) -> int:
        """Accept numeric IDs and formatted SIS IDs, plus legacy EVT IDs."""
        if isinstance(event_id, bool):
            raise ValueError("Event ID must be an integer between 1 and 999999.")

        if isinstance(event_id, str):
            event_id = event_id.strip()
            prefix = event_id[:4].upper()
            if prefix in ("SIS-", "EVT-"):
                event_id = event_id[4:]
            if not event_id.isdigit():
                raise ValueError("Event ID must be numeric or use SIS-000001 format.")
            event_id = int(event_id)
        elif not isinstance(event_id, int):
            raise ValueError("Event ID must be an integer between 1 and 999999.")

        return event_id

    @property
    def id(self) -> int:
        """Numeric, read-only identifier used for event comparisons."""
        return self._id

    @property
    def display_id(self) -> str:
        """Zero-padded identifier for display, e.g. ``SIS-000010``."""
        return f"SIS-{self.id:06d}"

    @staticmethod
    def _validate_inputs(event_id: int, magnitude: float, depth: float,
                         x: float, y: float):
        """Validates input ranges as specified in Section 3."""
        if not (1 <= event_id <= 999999):
            raise ValueError("Event ID must be an integer between 1 and 999999.")
        if not (-2.0 <= magnitude <= 10.0):
            raise ValueError("Magnitude M must be between -2.0 and 10.0.")
        if not (0.0 <= depth <= 700.0):
            raise ValueError("Depth H must be between 0.0 and 700.0 km.")
        if not (0.0 <= x <= 1000.0 and 0.0 <= y <= 1000.0):
            raise ValueError("Epicenter coordinates (x, y) must be between 0.0 and 1000.0 km.")

    def calculate_priority(self) -> int:
        """
        Calculates event priority based on Section 4 rules:
        Priority 3 (High): M >= 6.0 OR (M >= 4.5 AND H <= 30.0 AND in populated zone)
        Priority 2 (Medium): M >= 4.5 (not meeting Priority 3)
        Priority 1 (Low): Otherwise
        """
        if self.magnitude >= 6.0 or (self.magnitude >= 4.5 and self.depth <= 30.0 and self.is_populated):
            return 3
        elif self.magnitude >= 4.5:
            return 2
        return 1

    @property
    def key(self) -> tuple:
        return (self.priority, self.magnitude, self.id)

    @property
    def z(self) -> float:
        """Compatibility alias for views and JSON using the name ``z``."""
        return self.depth

    def __repr__(self):
        return f"Event({self.display_id}, Key={self.key}, Status={self.status})"

    def __str__(self):
        return self.display_id
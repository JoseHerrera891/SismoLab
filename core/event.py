# model for the sismic event and priority (the node)

class Event:
    def __init__(self, event_id: int, magnitude: float, depth: float, 
                 x: float, y: float, timestamp: str, station: str, 
                 is_populated: bool = False, revision: int = 1):
        
        # first of all, we confirm the values before putting them.
        self._validate_inputs(event_id, magnitude, depth, x, y)
        
        # atributes based on what we think the node need to have.
        self.id = int(event_id)
        self.magnitude = round(float(magnitude), 1)
        self.depth = round(float(depth), 1)
        self.x = round(float(x), 1)
        self.y = round(float(y), 1)
        self.timestamp = timestamp  # Format ISO 8601, each node has the time is was created
        self.station = station
        self.is_populated = is_populated
        self.revision = int(revision)
        
        # Status can be 'PENDING' or 'REVIEWED'
        self.status = "PENDING"
        
        # Set of stations that have reported this accepted event
        self.accepted_stations = {station}
        
        # we set the priority based on the condition (section 4)
        self.priority = self.calculate_priority()

    def _validate_inputs(self, event_id: int, magnitude: float, depth: float, x: float, y: float):
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

    # here we create the lexicographic key 
    @property
    def key(self) -> tuple:
        
        return (self.priority, self.magnitude, self.id)
    # and return the basic info about the event
    def __repr__(self):
        return f"Event(SIS-{self.id:06d}, Key={self.key}, Status={self.status})"
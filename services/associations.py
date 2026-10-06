# services/associations.py
import math
from datetime import datetime


class ReplicaManager:
    """
    Manages the association rules between events and their possible aftershocks
    (Section 7 of the PDF).
    """

    def __init__(self, W_hours: float = 48.0, R_km: float = 40.0):
        self.W_hours = W_hours  # Maximum time window in hours (Section 7)
        self.R_km = R_km  # Maximum Euclidean distance in km (Section 7)

    def calculate_distance(
        self, x1: float, y1: float, x2: float, y2: float
    ) -> float:
        """
        Calculates the Euclidean distance on the 1000x1000 km plane between two epicenters.
        """
        return math.hypot(x2 - x1, y2 - y1)
        #return math.sqrt((x2 - x1) * 2 + (y2 - y1) * 2)

    def get_candidates(self, event_b, all_events: list) -> list:
        """
        Finds all event A records that satisfy the requirements to be considered
        a reference candidate for event B (Section 7 of the PDF).
        """
        candidates = []

        for event_a in all_events:
            # 1. An event is never evaluated against itself.
            if event_a.id == event_b.id:
                continue

            # 2. Magnitude: A must be strictly larger than B (M_A > M_B).
            if event_a.magnitude <= event_b.magnitude:
                continue

            # 3. Timing: A must have occurred strictly before B.
            time_diff_seconds = (
                event_b.timestamp - event_a.timestamp
            ).total_seconds()
            if time_diff_seconds <= 0:
                continue

            # 4. Time window: the difference must not exceed W hours.
            time_diff_hours = time_diff_seconds / 3600.0
            if time_diff_hours > self.W_hours:
                continue

            # 5. Distance: the epicentral distance must not exceed R km.
            dist = self.calculate_distance(
                event_a.x, event_a.y, event_b.x, event_b.y
            )
            if dist > self.R_km:
                continue

            # If it passes every filter, it is a valid candidate.
            candidates.append(event_a)

        return candidates

    def select_main_reference(self, event_b, candidates: list):
        """
        Deterministic selection rule (Section 7 of the PDF):
        When several candidates are available, the main reference is chosen in a fixed order:
        1. The candidate with the greatest magnitude.
        2. If magnitudes tie, the one closest to B.
        3. If distances tie, the one with the lowest numeric ID.
        """
        if not candidates:
            return None  # If there are no candidates, the event remains unassociated.

        best_candidate = None
        best_magnitude = -1.0
        best_distance = float("inf")
        best_id = float("inf")

        for cand in candidates:
            dist = self.calculate_distance(
                cand.x, cand.y, event_b.x, event_b.y
            )

            # Deterministic comparison rule:
            # - Higher magnitude wins
            # - If tied, shorter distance wins
            # - If still tied, lower ID wins
            if cand.magnitude > best_magnitude:
                best_candidate = cand
                best_magnitude = cand.magnitude
                best_distance = dist
                best_id = cand.id
            elif cand.magnitude == best_magnitude:
                if dist < best_distance:
                    best_candidate = cand
                    best_distance = dist
                    best_id = cand.id
                elif dist == best_distance:
                    if cand.id < best_id:
                        best_candidate = cand
                        best_id = cand.id

        return best_candidate
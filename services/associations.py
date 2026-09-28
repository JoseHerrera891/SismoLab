# services/associations.py
import math
from datetime import datetime


class ReplicaManager:
    """
    Gestiona las reglas de asociación entre eventos y posibles réplicas (Sección 7 del PDF).
    """

    def _init_(self, W_hours: float = 48.0, R_km: float = 40.0):
        self.W_hours = W_hours  # Ventana de tiempo máxima en horas (Sección 7)
        self.R_km = R_km  # Distancia euclidiana máxima en km (Sección 7)

    def calculate_distance(
        self, x1: float, y1: float, x2: float, y2: float
    ) -> float:
        """
        Calcula la distancia euclidiana en el plano 1000x1000 km entre dos epicentros.
        """
        return math.sqrt((x2 - x1) * 2 + (y2 - y1) * 2)

    def get_candidates(self, event_b, all_events: list) -> list:
        """
        Encuentra todos los eventos A que cumplen los requisitos para ser
        candidatos a referencia del evento B (Sección 7 del PDF).
        """
        candidates = []

        for event_a in all_events:
            # 1. Un evento no se evalúa consigo mismo
            if event_a.id == event_b.id:
                continue

            # 2. Magnitud: A debe ser ESTRICTAMENTE MAYOR que B (M_A > M_B)
            if event_a.magnitude <= event_b.magnitude:
                continue

            # 3. Ocurrencia: A debió ocurrir ESTRICTAMENTE ANTES que B
            time_diff_seconds = (
                event_b.timestamp - event_a.timestamp
            ).total_seconds()
            if time_diff_seconds <= 0:
                continue

            # 4. Ventana de tiempo: La diferencia no debe superar las W horas
            time_diff_hours = time_diff_seconds / 3600.0
            if time_diff_hours > self.W_hours:
                continue

            # 5. Distancia: La distancia entre epicentros no debe superar los R km
            dist = self.calculate_distance(
                event_a.x, event_a.y, event_b.x, event_b.y
            )
            if dist > self.R_km:
                continue

            # Si superó todos los filtros, es un candidato válido
            candidates.append(event_a)

        return candidates

    def select_main_reference(self, event_b, candidates: list):
        """
        Criterio determinista (Sección 7 del PDF):
        Si hay varios candidatos, selecciona la referencia principal de forma fija:
        1. El candidato con la MAYOR magnitud.
        2. En caso de empate en magnitud, el más CERCANO en distancia a B.
        3. En caso de empate en distancia, el con menor ID numérico.
        """
        if not candidates:
            return None  # Si no hay candidatos, queda sin asociación

        best_candidate = None
        best_magnitude = -1.0
        best_distance = float("inf")
        best_id = float("inf")

        for cand in candidates:
            dist = self.calculate_distance(
                cand.x, cand.y, event_b.x, event_b.y
            )

            # Criterio de comparación determinista:
            # - Mayor magnitud gana
            # - Si empatan en magnitud, menor distancia gana
            # - Si empatan en distancia, menor ID gana
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
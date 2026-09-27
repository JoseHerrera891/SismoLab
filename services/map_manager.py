# services/map_manager.py

class Zone:

    """Representa una zona rectangular en el plano 1000x1000 km."""
    def __init__(self, name: str, x_min: float, x_max: float, y_min: float, y_max: float, is_populated: bool):
        self.name = name
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.is_populated = is_populated

    def contains(self, x: float, y: float) -> bool:
        """
        Verifica si las coordenadas (x, y) están dentro o sobre el borde de la zona.
        """
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max


class MapManager:

    """Administra el plano geográfico y evalúa si un epicentro está en Zona Poblada."""
    def __init__(self):
        self.width = 1000.0
        self.height = 1000.0
        self.zones: list[Zone] = []

    def add_zone(self, zone: Zone):
        """Añade una zona fija al mapa."""
        self.zones.append(zone)

    def is_in_populated_zone(self, x: float, y: float) -> bool:
        """
        Regla Sección 3:
        Un epicentro pertenece a una zona cuando está dentro o sobre su borde.
        Si está en el borde de dos zonas, se clasifica como poblada si AL MENOS
        una de las dos está definida como poblada.
        """
        in_populated = False
        
        for zone in self.zones:
            if zone.contains(x, y):
                if zone.is_populated:
                    in_populated = True  # Prioridad: si toca una zona poblada, ya es poblada

        return in_populated
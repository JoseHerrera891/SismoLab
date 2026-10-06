# gui/map_viewer.py
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import Qt, QRectF


class MapViewer(QWidget):
    """
    2D Map Visualization component for rendering seismic events,
    epicenters, and populated zones within a 1000x1000 km grid.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.events = []
        self.populated_zones = []

    def set_data(self, events: list, populated_zones: list):
        """
        Updates the events and zones data, triggering a canvas repaint.
        """
        self.events = events
        self.populated_zones = populated_zones
        self.update()  # Triggers paintEvent

    def paintEvent(self, event):
        """
        Custom paint event to draw grid, zones, and seismic epicenters.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), QColor("#f3f4f6"))

        # Map bounds scale (1000x1000 km mapped to widget dimensions)
        width = self.width()
        height = self.height()

        # 1. Draw Grid Lines
        painter.setPen(QPen(QColor("#333333"), 1, Qt.PenStyle.DashLine))
        for i in range(1, 10):
            x = (width / 10) * i
            y = (height / 10) * i
            painter.drawLine(int(x), 0, int(x), height)
            painter.drawLine(0, int(y), width, int(y))

        # 2. Draw zones, using different colors for populated and unpopulated areas.
        for zone in self.populated_zones:
            # Scale coordinates from km to pixels
            px = (zone.x_min / 1000.0) * width
            py = (zone.y_min / 1000.0) * height
            zone_width = ((zone.x_max - zone.x_min) / 1000.0) * width
            zone_height = ((zone.y_max - zone.y_min) / 1000.0) * height

            if zone.is_populated:
                zone_color = QColor("#ff9900")
            else:
                zone_color = QColor("#607d8b")
            painter.setPen(QPen(zone_color, 1))
            fill_color = QColor(zone_color)
            fill_color.setAlpha(40)
            painter.setBrush(QBrush(fill_color))
            painter.drawRect(QRectF(px, py, zone_width, zone_height))
            painter.setPen(QPen(zone_color, 1))
            painter.drawText(int(px + 4), int(py + 16), zone.name)

        # 3. Draw Seismic Events (Epicenters)
        priority_colors = {
            1: "#4da6ff",
            2: "#ffd24d",
            3: "#ff4d4d",
        }
        base_radius = 6
        priority_radius_adjustments = {
            1: -2,
            2: 0,
            3: 3,
        }

        for ev in self.events:
            px = (ev.x / 1000.0) * width
            py = (ev.y / 1000.0) * height

            color = QColor(priority_colors[ev.priority])
            outline_width = 4 if ev.priority == 3 else 2
            painter.setPen(QPen(color, outline_width))
            fill_color = QColor(color)
            fill_color.setAlpha(100)
            painter.setBrush(QBrush(fill_color))

            radius = base_radius + priority_radius_adjustments[ev.priority]
            painter.drawEllipse(QRectF(px - radius, py - radius, radius * 2, radius * 2))
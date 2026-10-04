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
        super()._init_(parent)
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

        # Draw Background
        painter.fillRect(self.rect(), QColor("#1e1e1e"))

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

        # 2. Draw Populated Zones
        painter.setPen(QPen(QColor("#ff9900"), 1))
        painter.setBrush(QBrush(QColor(255, 153, 0, 40)))  # Semi-transparent orange

        for zone in self.populated_zones:
            # Scale coordinates from km to pixels
            px = (zone.x / 1000.0) * width
            py = (zone.y / 1000.0) * height
            pr = (zone.radius / 1000.0) * width

            painter.drawEllipse(QRectF(px - pr, py - pr, pr * 2, pr * 2))

        # 3. Draw Seismic Events (Epicenters)
        painter.setPen(QPen(QColor("#ffffff"), 1))

        for ev in self.events:
            px = (ev.x / 1000.0) * width
            py = (ev.y / 1000.0) * height

            # Color based on magnitude
            if ev.magnitude >= 5.0:
                painter.setBrush(QBrush(QColor("#ff4d4d")))  # Red for high mag
            else:
                painter.setBrush(QBrush(QColor("#4da6ff")))  # Blue for low mag

            radius = max(3, int(ev.magnitude * 2))
            painter.drawEllipse(QRectF(px - radius, py - radius, radius * 2, radius * 2))
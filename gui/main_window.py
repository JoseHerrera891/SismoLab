# gui/main_window.py
import sys
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from services.map_manager import MapManager
from services.associations import ReplicaManager
from services.persistence import PersistenceManager, Auditor


class MainWindow(QMainWindow):
    """
    Main Application Window for the Seismic Monitoring System.
    Handles UI components and connects backend services with the view.
    """

    def _init_(self):
        super()._init_()
        self.setWindowTitle("Seismic Monitoring System")
        self.resize(1000, 700)

        # Initialize backend service instances
        self.auditor = Auditor()
        self.map_manager = MapManager()
        self.replica_manager = ReplicaManager(W_hours=48.0, R_km=40.0)
        self.persistence = PersistenceManager(auditor=self.auditor)

        # In-memory storage for seismic events
        self.events = []

        # Setup Graphical User Interface components
        self._init_ui()

    def _init_ui(self):
        """
        Initializes layouts, controls, and visual elements of the window.
        """
        # Central widget container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout structure (vertical)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Header Title
        title_label = QLabel("Seismic Event Dashboard")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; margin: 10px;"
        )
        main_layout.addWidget(title_label)

        # Top Control Panel (Buttons)
        button_layout = QHBoxLayout()

        self.btn_export = QPushButton("Export to JSON")
        self.btn_export.clicked.connect(self._handle_export)

        self.btn_load = QPushButton("Load JSON")
        self.btn_load.clicked.connect(self._handle_load)

        button_layout.addWidget(self.btn_export)
        button_layout.addWidget(self.btn_load)

        main_layout.addLayout(button_layout)

        # Events Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "X (km)",
                "Y (km)",
                "Z (km)",
                "Magnitude",
                "Populated Zone",
                "Main Ref ID",
            ]
        )
        main_layout.addWidget(self.table)

    def _handle_export(self):
        """
        Triggers the export functionality to save events into a JSON file.
        """
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "JSON Files (*.json)"
        )
        if filepath:
            success = self.persistence.export_to_json(
                self.events, self.map_manager, self.replica_manager, filepath
            )
            if success:
                QMessageBox.information(
                    self, "Success", "Data exported successfully!"
                )
            else:
                QMessageBox.critical(
                    self, "Error", "Failed to export seismic data."
                )

    def _handle_load(self):
        """
        Triggers loading data from an existing JSON file.
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "JSON Files (*.json)"
        )
        if filepath:
            try:
                data = self.persistence.load_from_json(filepath)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Loaded {data.get('events_count', 0)} events successfully!",
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to load file: {e}"
                )
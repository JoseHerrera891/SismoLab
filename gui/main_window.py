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
    QSplitter,
)
from PyQt6.QtCore import Qt

from services.map_manager import MapManager
from services.associations import ReplicaManager
from services.persistence import PersistenceManager, Auditor
from gui.map_viewer import MapViewer
from gui.tree_viewer import TreeViewer


class MainWindow(QMainWindow):
    """
    Main Application Window for the Seismic Monitoring System.
    Integrates 2D map canvas, replica tree, data table, and export/load actions.
    """

    def _init_(self):
        super()._init_()
        self.setWindowTitle("Seismic Monitoring System")
        self.resize(1200, 800)

        # Initialize backend services
        self.auditor = Auditor()
        self.map_manager = MapManager()
        self.replica_manager = ReplicaManager(W_hours=48.0, R_km=40.0)
        self.persistence = PersistenceManager(auditor=self.auditor)

        # In-memory storage for seismic events
        self.events = []

        # Setup GUI layout
        self._init_ui()

    def _init_ui(self):
        """
        Initializes UI layout, controls, map canvas, and replica tree.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Header Title
        title_label = QLabel("Seismic Event Dashboard")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; margin: 10px;"
        )
        main_layout.addWidget(title_label)

        # Control Panel (Buttons)
        button_layout = QHBoxLayout()

        self.btn_export = QPushButton("Export to JSON")
        self.btn_export.clicked.connect(self._handle_export)

        self.btn_load = QPushButton("Load JSON")
        self.btn_load.clicked.connect(self._handle_load)

        button_layout.addWidget(self.btn_export)
        button_layout.addWidget(self.btn_load)

        main_layout.addLayout(button_layout)

        # Splitter to separate visual components (Map + Tree) and Table
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Map Canvas & Tree Viewer
        visual_panel = QWidget()
        visual_layout = QVBoxLayout()
        visual_panel.setLayout(visual_layout)

        self.map_viewer = MapViewer()
        self.tree_viewer = TreeViewer()

        visual_layout.addWidget(self.map_viewer)
        visual_layout.addWidget(self.tree_viewer)

        # Right panel: Data Table
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

        content_splitter.addWidget(visual_panel)
        content_splitter.addWidget(self.table)
        content_splitter.setSizes([600, 600])

        main_layout.addWidget(content_splitter)

    def _handle_export(self):
        """
        Triggers exporting events into a JSON file using PersistenceManager.
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
        Triggers loading events from a JSON file and refreshes views.
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
                # Refresh map canvas and tree view
                self.map_viewer.set_data(
                    self.events, self.map_manager.zones
                )
                self.tree_viewer.populate_tree(
                    self.events, self.replica_manager
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to load file: {e}"
                )
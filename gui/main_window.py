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

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seismic Monitoring System")
        self.resize(1100, 700)

        # Initialize backend services
        self.auditor = Auditor()
        self.map_manager = MapManager()
        self.replica_manager = ReplicaManager(W_hours=48.0, R_km=40.0)
        self.persistence = PersistenceManager(auditor=self.auditor)

        self.events = []
        self._init_ui()

    def _init_ui(self):
        """
        Initializes UI controls, buttons, map canvas, and table.
        """
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Header Title
        title_label = QLabel("Seismic Monitoring Dashboard")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 5px;")
        main_layout.addWidget(title_label)

        # Top Control Buttons Panel
        button_layout = QHBoxLayout()

        self.btn_load = QPushButton("📁 Load JSON")
        self.btn_load.setStyleSheet("font-size: 14px; padding: 8px;")
        self.btn_load.clicked.connect(self._handle_load)

        self.btn_export = QPushButton("💾 Export to JSON")
        self.btn_export.setStyleSheet("font-size: 14px; padding: 8px;")
        self.btn_export.clicked.connect(self._handle_export)

        button_layout.addWidget(self.btn_load)
        button_layout.addWidget(self.btn_export)
        main_layout.addLayout(button_layout)

        # Splitter to hold visual components and table side-by-side
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel (Map + Tree Viewer)
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        self.map_viewer = MapViewer()
        self.tree_viewer = TreeViewer()

        left_layout.addWidget(self.map_viewer)
        left_layout.addWidget(self.tree_viewer)

        # Right Panel (Events Table)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "X (km)", "Y (km)", "Z (km)", "Magnitude", "Timestamp"]
        )

        splitter.addWidget(left_widget)
        splitter.addWidget(self.table)
        splitter.setSizes([550, 550])

        main_layout.addWidget(splitter)

    def _handle_export(self):
        """
        Exports current events data to JSON file.
        """
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save JSON File", "", "JSON Files (*.json)"
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
        Loads JSON data and updates map_viewer, tree_viewer, and table.
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open JSON File", "", "JSON Files (*.json)"
        )
        if filepath:
            try:
                # 1. Cargar datos
                data = self.persistence.load_from_json(filepath)
                if isinstance(data, dict):
                    self.events = data.get("events", [])
                else:
                    self.events = data

                # 2. Refrescar Mapa y Árbol
                self.map_viewer.set_data(self.events, self.map_manager.zones)
                self.tree_viewer.populate_tree(self.events, self.replica_manager)

                # 3. Refrescar Tabla de Eventos
                self.table.setRowCount(len(self.events))
                for row, ev in enumerate(self.events):
                    # Soporta tanto objetos Event como diccionarios del JSON
                    if isinstance(ev, dict):
                        self.table.setItem(row, 0, QTableWidgetItem(str(ev.get("id", ""))))
                        self.table.setItem(row, 1, QTableWidgetItem(str(ev.get("x", ""))))
                        self.table.setItem(row, 2, QTableWidgetItem(str(ev.get("y", ""))))
                        self.table.setItem(row, 3, QTableWidgetItem(str(ev.get("z", ""))))
                        self.table.setItem(row, 4, QTableWidgetItem(str(ev.get("magnitude", ""))))
                        self.table.setItem(row, 5, QTableWidgetItem(str(ev.get("timestamp", ""))))
                    else:
                        self.table.setItem(row, 0, QTableWidgetItem(str(ev.id)))
                        self.table.setItem(row, 1, QTableWidgetItem(str(ev.x)))
                        self.table.setItem(row, 2, QTableWidgetItem(str(ev.y)))
                        self.table.setItem(row, 3, QTableWidgetItem(str(ev.z)))
                        self.table.setItem(row, 4, QTableWidgetItem(str(ev.magnitude)))
                        self.table.setItem(row, 5, QTableWidgetItem(str(ev.timestamp)))

                QMessageBox.information(
                    self, "Success", f"Loaded {len(self.events)} events successfully!"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {e}")
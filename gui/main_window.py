# gui/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLineEdit,
    QDoubleSpinBox,
    QPushButton,
    QLabel,
    QTextEdit,
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
    """Main dashboard for the seismic monitoring system."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seismic Monitoring Dashboard")
        self.resize(1450, 850)

        self.auditor = Auditor()
        self.map_manager = MapManager()
        self.replica_manager = ReplicaManager(W_hours=48.0, R_km=40.0)
        self.persistence = PersistenceManager(auditor=self.auditor)
        self.events = []

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        title_label = QLabel("Seismic Monitoring Dashboard")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 5px;")
        main_layout.addWidget(title_label)

        file_actions = QHBoxLayout()
        self.btn_load = QPushButton("Load JSON")
        self.btn_load.clicked.connect(self._handle_load)
        self.btn_export = QPushButton("Export to JSON")
        self.btn_export.clicked.connect(self._handle_export)
        file_actions.addWidget(self.btn_load)
        file_actions.addWidget(self.btn_export)
        file_actions.addStretch()
        main_layout.addLayout(file_actions)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        visualization_panel = QWidget()
        visualization_layout = QVBoxLayout(visualization_panel)
        self.map_viewer = MapViewer()
        self.tree_viewer = TreeViewer()
        visualization_layout.addWidget(self.map_viewer)
        visualization_layout.addWidget(self.tree_viewer)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "X (km)", "Y (km)", "Z (km)", "Magnitude", "Timestamp"]
        )

        controls_panel = QWidget()
        self.controls_layout = QVBoxLayout(controls_panel)
        self.setup_event_form()
        self.setup_actions_panel()
        self.setup_audit_panel()
        self.controls_layout.addStretch()

        splitter.addWidget(visualization_panel)
        splitter.addWidget(self.table)
        splitter.addWidget(controls_panel)
        splitter.setSizes([470, 470, 380])
        main_layout.addWidget(splitter)

    def setup_event_form(self):
        group = QGroupBox("Event Management")
        layout = QVBoxLayout(group)

        layout.addWidget(QLabel("Event ID:"))
        self.txt_id = QLineEdit()
        self.txt_id.setPlaceholderText("Example: EVT-102")
        layout.addWidget(self.txt_id)

        self.spn_x = self._make_spin_box(0, 1000, "Coordinate X (km):")
        layout.addWidget(self.spn_x)
        self.spn_y = self._make_spin_box(0, 1000, "Coordinate Y (km):")
        layout.addWidget(self.spn_y)
        self.spn_z = self._make_spin_box(0, 700, "Depth Z (km):")
        layout.addWidget(self.spn_z)
        self.spn_mag = self._make_spin_box(0, 10, "Magnitude (Mw):", 0.1)
        layout.addWidget(self.spn_mag)

        form_actions = QHBoxLayout()
        self.btn_insert = QPushButton("Add Event")
        self.btn_update = QPushButton("Update Event")
        form_actions.addWidget(self.btn_insert)
        form_actions.addWidget(self.btn_update)
        layout.addLayout(form_actions)
        self.controls_layout.addWidget(group)

    @staticmethod
    def _make_spin_box(minimum, maximum, label, step=1.0):
        field = QDoubleSpinBox()
        field.setRange(minimum, maximum)
        field.setSingleStep(step)
        field.setPrefix(f"{label} ")
        return field

    def setup_actions_panel(self):
        group = QGroupBox("System Operations")
        layout = QVBoxLayout(group)

        self.btn_delete = QPushButton("Delete Selected Event")
        self.btn_undo = QPushButton("Undo Last Action")
        self.btn_stress = QPushButton("Start Stress Simulation")
        self.btn_stress.setStyleSheet(
            "background-color: #d9534f; color: white; font-weight: bold;"
        )

        layout.addWidget(self.btn_delete)
        layout.addWidget(self.btn_undo)
        layout.addWidget(self.btn_stress)
        self.controls_layout.addWidget(group)

    def setup_audit_panel(self):
        group = QGroupBox("Audit Log and Metrics")
        layout = QVBoxLayout(group)

        self.txt_audit_log = QTextEdit()
        self.txt_audit_log.setReadOnly(True)
        self.txt_audit_log.setPlaceholderText("Waiting for system events...")
        self.txt_audit_log.setMinimumHeight(110)
        layout.addWidget(self.txt_audit_log)
        self.controls_layout.addWidget(group)

    def log_message(self, message: str):
        self.txt_audit_log.append(f"> {message}")

    def _handle_export(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save JSON File", "", "JSON Files (*.json)"
        )
        if not filepath:
            return

        success = self.persistence.export_to_json(
            self.events, self.map_manager, self.replica_manager, filepath
        )
        if success:
            self.log_message(f"Exported {len(self.events)} events to {filepath}")
            QMessageBox.information(self, "Success", "Data exported successfully!")
        else:
            QMessageBox.critical(self, "Error", "Failed to export seismic data.")

    def _handle_load(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open JSON File", "", "JSON Files (*.json)"
        )
        if not filepath:
            return

        try:
            data = self.persistence.load_from_json(filepath)
            self.events = data.get("events", []) if isinstance(data, dict) else data
            self._refresh_event_views()
            self.log_message(f"Loaded {len(self.events)} events from {filepath}")
            QMessageBox.information(
                self, "Success", f"Loaded {len(self.events)} events successfully!"
            )
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Failed to load file: {error}")

    def _refresh_event_views(self):
        self.map_viewer.set_data(self.events, self.map_manager.zones)
        self.tree_viewer.populate_tree(self.events, self.replica_manager)
        self.table.setRowCount(len(self.events))

        for row, event in enumerate(self.events):
            values = (
                event.id,
                event.x,
                event.y,
                event.z,
                event.magnitude,
                event.timestamp,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
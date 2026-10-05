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
    QAbstractItemView,
)
from PyQt6.QtCore import Qt
from datetime import datetime

from core.event import Event
from gui.map_viewer import MapViewer
from gui.tree_viewer import TreeViewer
from sismolab_controller import SismoLabController


class MainWindow(QMainWindow):
    """Main dashboard for the seismic monitoring system."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Seismic Monitoring Dashboard")
        self.resize(1450, 850)

        self.controller = SismoLabController()
        self.map_manager = self.controller.map_manager
        self.replica_manager = self.controller.replica_manager
        self.persistence = self.controller.persistence

        self._init_ui()

    @property
    def events(self):
        return self.controller.events

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
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.itemSelectionChanged.connect(
            self._load_selected_event_into_form
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
        self.txt_id.setPlaceholderText("Example: SIS-000010")
        layout.addWidget(self.txt_id)

        layout.addWidget(QLabel("Reporting station:"))
        self.txt_station = QLineEdit()
        self.txt_station.setPlaceholderText("Station name or code")
        layout.addWidget(self.txt_station)

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
        self.btn_insert.clicked.connect(self._handle_insert)
        self.btn_update.clicked.connect(self._handle_update)
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
        self.btn_delete.clicked.connect(self._handle_delete)
        self.btn_undo = QPushButton("Undo Last Action")
        self.btn_undo.clicked.connect(self._handle_undo)
        self.btn_stress = QPushButton("Start Stress Simulation")
        self.btn_stress.clicked.connect(self._handle_stress)
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
            events = data.get("events", []) if isinstance(data, dict) else data
            self.controller.replace_events(events)
            self._refresh_event_views()
            self.log_message(f"Loaded {len(self.events)} events from {filepath}")
            QMessageBox.information(
                self, "Success", f"Loaded {len(self.events)} events successfully!"
            )
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Failed to load file: {error}")

    def _handle_insert(self):
        try:
            station = self.txt_station.text().strip()
            if not station:
                raise ValueError("Enter the reporting station.")

            event = Event(
                event_id=self.txt_id.text(),
                magnitude=self.spn_mag.value(),
                depth=self.spn_z.value(),
                x=self.spn_x.value(),
                y=self.spn_y.value(),
                timestamp=datetime.now(),
                station=station,
                is_populated=self.map_manager.is_in_populated_zone(
                    self.spn_x.value(), self.spn_y.value()
                ),
            )
            result = self.controller.register_event_report(event)

            if result == "created":
                self.log_message(f"Added {event.display_id} from station {station}")
            elif result == "station_added":
                self.log_message(
                    f"Added station {station} to report for {event.display_id}"
                )
            elif result == "duplicate":
                QMessageBox.warning(
                    self,
                    "Duplicate report",
                    f"Station {station} has already reported {event.display_id}.",
                )
                return
            else:
                QMessageBox.warning(
                    self,
                    "Unavailable ID",
                    f"{event.display_id} is already reserved and cannot be reused.",
                )
                return

            self._refresh_event_views()
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Invalid event", str(error))

    def _selected_event_id(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self, "No event selected", "Select an event in the table first."
            )
            return None

        id_item = self.table.item(selected_rows[0].row(), 0)
        return id_item.data(Qt.ItemDataRole.UserRole)

    def _load_selected_event_into_form(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        event_id = self.table.item(selected_rows[0].row(), 0).data(
            Qt.ItemDataRole.UserRole
        )
        event = self.controller.event_manager.get_event(event_id)
        if event is None:
            return

        self.txt_id.setText(event.display_id)
        self.spn_x.setValue(event.x)
        self.spn_y.setValue(event.y)
        self.spn_z.setValue(event.depth)
        self.spn_mag.setValue(event.magnitude)
        self.txt_station.setText(event.station)

    def _handle_update(self):
        event_id = self._selected_event_id()
        if event_id is None:
            return

        new_data = {
            "x": self.spn_x.value(),
            "y": self.spn_y.value(),
            "depth": self.spn_z.value(),
            "magnitude": self.spn_mag.value(),
            "is_populated": self.map_manager.is_in_populated_zone(
                self.spn_x.value(), self.spn_y.value()
            ),
        }
        if self.controller.update_event(event_id, new_data):
            self.log_message(f"Updated SIS-{event_id:06d}")
            self._refresh_event_views()
        else:
            QMessageBox.warning(self, "Event not found", "The selected event no longer exists.")

    def _handle_delete(self):
        event_id = self._selected_event_id()
        if event_id is None:
            return

        if self.controller.delete_event(event_id):
            self.log_message(f"Deleted SIS-{event_id:06d}")
            self._refresh_event_views()
        else:
            QMessageBox.warning(self, "Event not found", "The selected event no longer exists.")

    def _handle_stress(self):
        if not self.controller.stress_manager.is_stress_mode:
            self.controller.stress_manager.enable_stress_mode()
            self.btn_stress.setText("Finish Stress Simulation")
            self.log_message("Stress simulation started; automatic rotations paused.")
            return

        rotations = self.controller.stress_manager.recover_avl_balance()
        self.btn_stress.setText("Start Stress Simulation")
        self.log_message(f"Stress simulation finished; performed {rotations} rotations.")
        self._refresh_event_views()

    def _handle_undo(self):
        if not self.controller.undo():
            QMessageBox.information(
                self, "Nothing to undo", "There are no event changes to undo."
            )
            return

        self.log_message("Undid the last event change.")
        self._refresh_event_views()

    def _refresh_event_views(self):
        events = self.events
        self.map_viewer.set_data(events, self.map_manager.zones)
        self.tree_viewer.populate_tree(events, self.replica_manager)
        self.table.setRowCount(len(events))
        if hasattr(self, "btn_stress"):
            self.btn_stress.setText(
                "Finish Stress Simulation"
                if self.controller.stress_manager.is_stress_mode
                else "Start Stress Simulation"
            )

        for row, event in enumerate(events):
            values = (
                event.display_id,
                event.x,
                event.y,
                event.depth,
                event.magnitude,
                event.timestamp,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, event.id)
                self.table.setItem(row, column, item)
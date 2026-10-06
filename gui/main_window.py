# main window to access all the features of the program
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
    QScrollArea,
    QGridLayout,
    QSpinBox,
    QDateTimeEdit,
    QInputDialog,
)
from PyQt6.QtCore import Qt, QDateTime
from core.event import Event
from gui.map_viewer import MapViewer
from gui.tree_viewer import TreeViewer
from sismolab_controller import SismoLabController


class MainWindow(QMainWindow):
    #main dashboard fot the seismic monitoring system
    #set window size
    def __init__(self):
        #initialize main window
        super().__init__()
        #set title and size
        self.setWindowTitle("Seismic Monitoring Dashboard")
        self.resize(1450, 20)

        #create controller and managers
        self.controller = SismoLabController()
        self.map_manager = self.controller.map_manager
        self.replica_manager = self.controller.replica_manager
        self.persistence = self.controller.persistence

        #load interface and refresh data
        self._init_ui()
        self._refresh_event_views()

    @property
    def events(self):
        #return active event list
        return self.controller.events

    def _init_ui(self):
        #initialize main dashboard layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        title_label = QLabel("Seismic Monitoring Dashboard")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 5px;")
        main_layout.addWidget(title_label)
        #initiation of main buttons
        file_actions = QHBoxLayout()
        self.btn_load = QPushButton("Load JSON / Restore Version")
        self.btn_load.clicked.connect(self._handle_load)
        self.btn_export = QPushButton("Export to JSON")
        self.btn_export.clicked.connect(self._handle_export)
        self.btn_save_version = QPushButton("Save named version")
        self.btn_save_version.clicked.connect(self._handle_save_version)
        file_actions.addWidget(self.btn_load)
        file_actions.addWidget(self.btn_export)
        file_actions.addWidget(self.btn_save_version)
        file_actions.addStretch()
        main_layout.addLayout(file_actions)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        #initiation of the trees and map
        visualization_panel = QWidget()
        visualization_layout = QVBoxLayout(visualization_panel)
        self.map_viewer = MapViewer()
        self.tree_viewer = TreeViewer()
        visualization_layout.addWidget(self.map_viewer)
        visualization_layout.addWidget(self.tree_viewer)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [#labels for the table of events
                "ID",
                "X (km)",
                "Y (km)",
                "Z (km)",
                "Magnitude",
                "Timestamp",
                "Costly access",
            ]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )#when selected from table, data will be tranfered to the spaces (to edit acction)
        self.table.itemSelectionChanged.connect(
            self._load_selected_event_into_form
        )
        #set panels to input (event management, avl and bst trees, arrhive, report queue)
        controls_panel = QWidget()
        self.controls_layout = QVBoxLayout(controls_panel)
        self.setup_event_form()
        self.setup_association_settings()
        self.setup_clock_archive_panel()
        self.setup_report_queue_panel()
        self.setup_actions_panel()
        self.setup_query_audit_panel()
        self.setup_audit_panel()
        self.controls_layout.addStretch()
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setWidget(controls_panel)

        splitter.addWidget(visualization_panel)
        splitter.addWidget(self.table)
        splitter.addWidget(controls_scroll)
        splitter.setSizes([470, 470, 380])
        main_layout.addWidget(splitter)

    def setup_event_form(self):
        #event management section
        group = QGroupBox("Event Management")
        layout = QVBoxLayout(group)
        #set and label inputs for event management
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

    def setup_association_settings(self):
        #association settings section
        group = QGroupBox("Replica Association Settings")
        layout = QVBoxLayout(group)
        #system setting for W and R (hours and distance between events to determinate if replica or not)
        self.spn_association_hours = self._make_spin_box(
            0, 100000, "W: Time window (hours)", 1
        )
        self.spn_association_hours.setValue(48)#default
        layout.addWidget(self.spn_association_hours)

        self.spn_association_distance = self._make_spin_box(
            0, 100000, "R: Maximum distance (km)", 1
        )
        self.spn_association_distance.setValue(40)#default
        layout.addWidget(self.spn_association_distance)

        self.btn_apply_association_settings = QPushButton(
            "Apply Association Settings" #button to apply settings
        )
        self.btn_apply_association_settings.clicked.connect(
            self._handle_apply_association_settings
        )
        layout.addWidget(self.btn_apply_association_settings)
        self.controls_layout.addWidget(group)

    def setup_report_queue_panel(self):
        #report queue section
        group = QGroupBox("Station Report FIFO")
        layout = QVBoxLayout(group)
        fields = QGridLayout()
        #set and input labels for queue 
        self.spn_report_id = QSpinBox()
        self.spn_report_id.setRange(1, 999999)
        self.spn_report_revision = QSpinBox()
        self.spn_report_revision.setRange(1, 999999)
        self.txt_report_station = QLineEdit()
        self.txt_report_station.setPlaceholderText("Station name...")
        self.dt_report_timestamp = QDateTimeEdit()
        self.dt_report_timestamp.setDateTime(
            QDateTime.fromSecsSinceEpoch(
                int(self.controller.simulation_clock.timestamp()),
                Qt.TimeSpec.UTC,
            )
        )
        if hasattr(self, "dt_query_end"):
            clock_seconds = int(self.controller.simulation_clock.timestamp())
            self.dt_query_end.setDateTime(
                QDateTime.fromSecsSinceEpoch(clock_seconds, Qt.TimeSpec.UTC)
            )
        self.dt_report_timestamp.setCalendarPopup(True)
        self.dt_report_timestamp.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.spn_report_magnitude = self._make_spin_box(-2, 10, "Mw", 0.1)
        self.spn_report_depth = self._make_spin_box(0, 700, "Depth (km)")
        self.spn_report_x = self._make_spin_box(0, 1000, "X (km)")
        self.spn_report_y = self._make_spin_box(0, 1000, "Y (km)")

        fields.addWidget(QLabel("Event ID"), 0, 0)
        fields.addWidget(self.spn_report_id, 0, 1)
        fields.addWidget(QLabel("Revision"), 1, 0)
        fields.addWidget(self.spn_report_revision, 1, 1)
        fields.addWidget(QLabel("Station"), 2, 0)
        fields.addWidget(self.txt_report_station, 2, 1)
        fields.addWidget(QLabel("Event time"), 3, 0)
        fields.addWidget(self.dt_report_timestamp, 3, 1)
        fields.addWidget(self.spn_report_magnitude, 4, 0, 1, 2)
        fields.addWidget(self.spn_report_depth, 5, 0, 1, 2)
        fields.addWidget(self.spn_report_x, 6, 0, 1, 2)
        fields.addWidget(self.spn_report_y, 7, 0, 1, 2)
        layout.addLayout(fields)
        #lable to see the report queue
        self.report_queue_table = QTableWidget()
        self.report_queue_table.setColumnCount(3)
        self.report_queue_table.setHorizontalHeaderLabels(
            ["Event ID", "Revision", "Station"]
        )
        self.report_queue_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.report_queue_table.setMaximumHeight(105)
        layout.addWidget(self.report_queue_table)
        #buttons for process the queue
        actions = QHBoxLayout()
        self.btn_enqueue_report = QPushButton("Queue Report")
        self.btn_enqueue_report.clicked.connect(self._handle_enqueue_report)
        self.btn_process_report = QPushButton("Process Next")
        self.btn_process_report.clicked.connect(self._handle_process_report)
        actions.addWidget(self.btn_enqueue_report)
        actions.addWidget(self.btn_process_report)
        layout.addLayout(actions)
        self.controls_layout.addWidget(group)

    def setup_clock_archive_panel(self):
        #simulation clock and archive section
        group = QGroupBox("Simulation Clock and Archive")
        layout = QVBoxLayout(group)
        self.lbl_simulation_clock = QLabel()
        layout.addWidget(self.lbl_simulation_clock)
        #set label inputs for simulation clock
        clock_controls = QHBoxLayout()
        self.spn_clock_advance = self._make_spin_box(
            0.1, 100000, "Advance (hours)", 1
        )
        self.spn_clock_advance.setValue(24)
        self.btn_advance_clock = QPushButton("Advance clock")#simulate pass of time
        self.btn_advance_clock.clicked.connect(self._handle_advance_clock)
        clock_controls.addWidget(self.spn_clock_advance)
        clock_controls.addWidget(self.btn_advance_clock)
        layout.addLayout(clock_controls)

        threshold_controls = QHBoxLayout()
        self.spn_archive_threshold = self._make_spin_box(
            0.1, 100000, "T (hours)", 1 #how many units to add in series (if 500 then N + 500)
        )
        self.spn_archive_threshold.setValue(
            self.controller.archive_age_threshold_hours
        )
        self.btn_apply_archive_threshold = QPushButton("Apply T")
        self.btn_apply_archive_threshold.clicked.connect(
            self._handle_apply_archive_threshold
        )
        threshold_controls.addWidget(self.spn_archive_threshold)
        threshold_controls.addWidget(self.btn_apply_archive_threshold)
        layout.addLayout(threshold_controls)
        #archive set and buttons
        archive_actions = QHBoxLayout()
        self.btn_archive_branch = QPushButton("Archive eligible branch")
        self.btn_archive_branch.clicked.connect(self._handle_archive_branch)
        self.btn_show_history = QPushButton("View history")
        self.btn_show_history.clicked.connect(self._handle_show_history)
        archive_actions.addWidget(self.btn_archive_branch)
        archive_actions.addWidget(self.btn_show_history)
        layout.addLayout(archive_actions)
        self.controls_layout.addWidget(group)

    @staticmethod
    def _make_spin_box(minimum, maximum, label, step=1.0):
        #create numeric field for settings
        field = QDoubleSpinBox()
        field.setRange(minimum, maximum)
        field.setSingleStep(step)
        field.setPrefix(f"{label} ")
        return field

    def setup_actions_panel(self):
        #general operations section
        group = QGroupBox("System Operations")
        layout = QVBoxLayout(group)

        search_layout = QHBoxLayout()
        self.txt_search_id = QLineEdit()
        self.txt_search_id.setPlaceholderText("Numeric event ID")
        self.btn_search = QPushButton("Search")
        self.btn_search.clicked.connect(self._handle_search)
        self.txt_search_id.returnPressed.connect(self._handle_search)
        search_layout.addWidget(self.txt_search_id)
        search_layout.addWidget(self.btn_search)

        self.btn_delete = QPushButton("Delete Selected Event")
        self.btn_delete.clicked.connect(self._handle_delete)
        self.btn_review = QPushButton("Mark as Reviewed")
        self.btn_review.clicked.connect(self._handle_mark_reviewed)
        self.btn_undo = QPushButton("Undo Last Action")
        self.btn_undo.clicked.connect(self._handle_undo)
        self.btn_stress = QPushButton("Start Stress Simulation")
        self.btn_stress.clicked.connect(self._handle_stress)
        self.btn_stress.setStyleSheet(
            "background-color: #d9534f; color: white; font-weight: bold;"
        )
        self.lbl_stress_mode = QLabel()
        costly_access_layout = QHBoxLayout()
        costly_access_layout.addWidget(QLabel("Costly-access limit L:"))
        self.spn_costly_access_limit = QSpinBox()
        self.spn_costly_access_limit.setRange(0, 999999)
        self.spn_costly_access_limit.setValue(
            self.controller.costly_access_limit
        )
        costly_access_layout.addWidget(self.spn_costly_access_limit)
        self.btn_apply_costly_access_limit = QPushButton("Apply L")
        self.btn_apply_costly_access_limit.clicked.connect(
            self._handle_apply_costly_access_limit
        )

        layout.addLayout(search_layout)
        layout.addWidget(self.btn_review)
        layout.addWidget(self.btn_delete)
        layout.addWidget(self.btn_undo)
        layout.addWidget(self.btn_stress)
        layout.addWidget(self.lbl_stress_mode)
        layout.addLayout(costly_access_layout)
        layout.addWidget(self.btn_apply_costly_access_limit)
        self.controls_layout.addWidget(group)

    def setup_query_audit_panel(self):
        #query and audit section
        group = QGroupBox("Queries and Structural Audit")
        layout = QVBoxLayout(group)

        self.btn_verify_structure = QPushButton("Verify AVL structure")
        self.btn_verify_structure.clicked.connect(self._handle_verify_structure)
        layout.addWidget(self.btn_verify_structure)

        self.spn_query_count = QSpinBox()
        self.spn_query_count.setRange(1, 100000)
        self.spn_query_count.setValue(10)
        self.btn_query_top = QPushButton("Top pending events")
        self.btn_query_top.clicked.connect(self._handle_query_top_pending)
        top_query = QHBoxLayout()
        top_query.addWidget(QLabel("Count k:"))
        top_query.addWidget(self.spn_query_count)
        top_query.addWidget(self.btn_query_top)
        layout.addLayout(top_query)

        magnitude_query = QHBoxLayout()
        self.spn_query_min_magnitude = self._make_spin_box(
            -2, 10, "Minimum Mw", 0.1
        )
        self.spn_query_max_magnitude = self._make_spin_box(
            -2, 10, "Maximum Mw", 0.1
        )
        self.spn_query_max_magnitude.setValue(10)
        btn_magnitude_query = QPushButton("Query magnitude range")
        btn_magnitude_query.clicked.connect(self._handle_query_magnitude_range)
        magnitude_query.addWidget(self.spn_query_min_magnitude)
        magnitude_query.addWidget(self.spn_query_max_magnitude)
        magnitude_query.addWidget(btn_magnitude_query)
        layout.addLayout(magnitude_query)

        self.spn_query_max_depth = self._make_spin_box(
            0, 700, "Maximum depth (km)"
        )
        clock = self.controller.simulation_clock
        self.dt_query_start = QDateTimeEdit(
            QDateTime.fromSecsSinceEpoch(
                int(clock.timestamp()) - 30 * 24 * 60 * 60,
                Qt.TimeSpec.UTC,
            )
        )
        self.dt_query_end = QDateTimeEdit(
            QDateTime.fromSecsSinceEpoch(
                int(clock.timestamp()),
                Qt.TimeSpec.UTC,
            )
        )
        for date_field in (self.dt_query_start, self.dt_query_end):
            date_field.setCalendarPopup(True)
            date_field.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        btn_shallow_query = QPushButton("Query shallow events by date")
        btn_shallow_query.clicked.connect(self._handle_query_shallow_events)
        layout.addWidget(self.spn_query_max_depth)
        layout.addWidget(QLabel("Date range (UTC):"))
        layout.addWidget(self.dt_query_start)
        layout.addWidget(self.dt_query_end)
        layout.addWidget(btn_shallow_query)

        query_actions = QHBoxLayout()
        btn_associations = QPushButton("Query associations for searched ID")
        btn_associations.clicked.connect(self._handle_query_associations)
        btn_costly = QPushButton("List costly-access events")
        btn_costly.clicked.connect(self._handle_query_costly_access)
        query_actions.addWidget(btn_associations)
        query_actions.addWidget(btn_costly)
        layout.addLayout(query_actions)
        self.controls_layout.addWidget(group)

    def setup_audit_panel(self):
        #audit log and metrics section
        group = QGroupBox("Audit Log and Metrics")
        layout = QVBoxLayout(group)

        self.lbl_structure_status = QLabel("Structure audit has not been run.")
        layout.addWidget(self.lbl_structure_status)
        self.lbl_system_metrics = QLabel()
        self.lbl_system_metrics.setWordWrap(True)
        layout.addWidget(self.lbl_system_metrics)
        self.btn_show_traversals = QPushButton("View tree traversals")
        self.btn_show_traversals.clicked.connect(self._handle_show_traversals)
        layout.addWidget(self.btn_show_traversals)
        self.txt_audit_log = QTextEdit()
        self.txt_audit_log.setReadOnly(True)
        self.txt_audit_log.setPlaceholderText("Waiting for system events...")
        self.txt_audit_log.setMinimumHeight(110)
        layout.addWidget(self.txt_audit_log)
        self.controls_layout.addWidget(group)

    def log_message(self, message: str):
        #add message to audit log
        self.txt_audit_log.append(f"> {message}")

    @staticmethod
    def _format_query_events(events):
        #format event list for query display
        return "\n".join(
            (
                f"{event.display_id} | M{event.magnitude:.1f} | "
                f"Depth {event.depth:g} km | P{event.priority} | "
                f"{event.status} | {event.timestamp.isoformat(timespec='seconds')}"
            )
            for event in events
        ) or "No matching events."

    def _show_query_result(self, title, result, events_key="events"):
        #show query result
        events = result[events_key]
        message = (
            self._format_query_events(events)
            + f"\n\nAVL nodes examined: {result['nodes_examined']}"
        )
        QMessageBox.information(self, title, message)

    def _handle_verify_structure(self):
        #verify the AVL structure and update status
        result = self.controller.verify_structure()
        status = (
            "Structure valid"
            if result["valid"]
            else f"Structure invalid ({len(result['errors'])} issue(s))"
        )
        if result["valid"] and result["expected_imbalances"]:
            status = (
                "Structure valid in stress mode; "
                f"{len(result['expected_imbalances'])} expected imbalance(s)"
            )
        self.lbl_structure_status.setText(
            f"{status} | Nodes examined: {result['nodes_examined']}"
        )
        self.log_message(
            f"AVL audit: {status.lower()}; "
            f"{result['nodes_examined']} nodes examined."
        )
        details = [
            f"Active events: {result['active_events']}",
            f"Archived events: {result['archived_events']}",
            f"Nodes examined: {result['nodes_examined']}",
        ]
        if result["errors"]:
            details.extend(("", *result["errors"]))
            QMessageBox.warning(self, "AVL audit", "\n".join(details))
        else:
            if result["expected_imbalances"]:
                details.extend(
                    (
                        "",
                        "Expected stress-mode imbalances:",
                        *result["expected_imbalances"],
                    )
                )
            else:
                details.append("No structural or catalog inconsistencies found.")
            QMessageBox.information(self, "AVL audit", "\n".join(details))

    def _handle_show_traversals(self):
        #show tree traversal results
        metrics = self.controller.get_dashboard_metrics()
        traversal_text = []
        for traversal_name, events in metrics["traversals"].items():
            traversal_text.append(
                f"{traversal_name.replace('_', ' ').title()}: "
                + (", ".join(event.display_id for event in events) or "empty")
            )
        QMessageBox.information(
            self, "AVL traversals", "\n\n".join(traversal_text)
        )

    def _handle_query_top_pending(self):
        #query the highest-priority pending events
        try:
            result = self.controller.query_top_pending(
                self.spn_query_count.value()
            )
            self._show_query_result("Top pending events", result)
        except (TypeError, ValueError, RuntimeError) as error:
            #show query error
            QMessageBox.warning(self, "Query failed", str(error))

    def _handle_query_magnitude_range(self):
        #query events by magnitude range
        try:
            result = self.controller.query_magnitude_range(
                self.spn_query_min_magnitude.value(),
                self.spn_query_max_magnitude.value(),
            )
            self._show_query_result("Events by magnitude", result)
        except (TypeError, ValueError, RuntimeError) as error:
            #show query error
            QMessageBox.warning(self, "Query failed", str(error))

    def _handle_query_shallow_events(self):
        #query shallow events within a date range
        try:
            result = self.controller.query_shallow_events_by_date(
                self.spn_query_max_depth.value(),
                self.dt_query_start.dateTime().toPyDateTime(),
                self.dt_query_end.dateTime().toPyDateTime(),
            )
            self._show_query_result("Shallow events by date", result)
        except (TypeError, ValueError, RuntimeError) as error:
            #show query error
            QMessageBox.warning(self, "Query failed", str(error))

    def _handle_query_associations(self):
        #query associations for a selected event
        raw_event_id = self.txt_search_id.text().strip()
        if not raw_event_id.isdigit():
            QMessageBox.warning(
                self, "Invalid ID", "Enter a numeric ID in the Search field."
            )
            return

        result = self.controller.query_associations(int(raw_event_id))
        if result is None:
            QMessageBox.information(
                self, "Associations", f"No event with ID {raw_event_id}."
            )
            return

        event = result["event"]
        candidates = result["candidates"]
        main_reference = result["main_reference"]
        referenced_by = result["referenced_by"]
        message = [
            f"Event: {event.display_id} "
            f"({'archived' if result['event_is_archived'] else 'active'})",
            "Candidate references: "
            + (
                ", ".join(
                    f"{item.display_id} "
                    f"({'archived' if result['candidate_archived'][item.id] else 'active'})"
                    for item in candidates
                )
                or "None"
            ),
            "Selected main reference: "
            + (
                f"{main_reference.display_id} "
                f"({'archived' if result['main_reference_is_archived'] else 'active'})"
                if main_reference
                else "None"
            ),
            "Events referencing this event: "
            + (
                ", ".join(
                    f"{item.display_id} "
                    f"({'archived' if result['referenced_by_archived'][item.id] else 'active'})"
                    for item in referenced_by
                )
                or "None"
            ),
            f"Active AVL nodes examined: {result['nodes_examined']}",
        ]
        QMessageBox.information(self, "Replica associations", "\n".join(message))

    def _handle_query_costly_access(self):
        #show costly-access events
        result = self.controller.query_costly_access_events()
        entries = [
            f"{item['event'].display_id} | depth {item['depth']} | "
            f"{item['comparisons']} comparisons | L={item['limit']}"
            for item in result["events"]
        ]
        message = "\n".join(entries) or "No costly-access events found."
        message += f"\n\nAVL nodes examined: {result['nodes_examined']}"
        QMessageBox.information(self, "Costly-access events", message)

    def _handle_export(self):
        #export current scenario to JSON
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save JSON File", "", "JSON Files (*.json)"
        )
        if not filepath:
            return

        try:
            self.persistence.save_scenario(self.controller, filepath)
            self.log_message(f"Exported {len(self.events)} events to {filepath}")
            QMessageBox.information(self, "Success", "Data exported successfully!")
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "Error", f"Failed to save scenario: {error}")

    def _handle_save_version(self):
        #save the current scenario with a version name
        version_name, accepted = QInputDialog.getText(
            self, "Save named version", "Version name:"
        )
        version_name = version_name.strip()
        if not accepted:
            return
        if not version_name:
            QMessageBox.warning(self, "Invalid name", "Enter a version name.")
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save named version",
            f"{version_name}.json",
            "JSON Files (*.json)",
        )
        if not filepath:
            return
        try:
            self.persistence.save_scenario(
                self.controller, filepath, version_name=version_name
            )
            self.log_message(f"Saved version '{version_name}'")
            QMessageBox.information(
                self,
                "Version saved",
                f"Version '{version_name}' was saved to:\n{filepath}",
            )
        except (OSError, TypeError, ValueError) as error:
            QMessageBox.critical(self, "Version save failed", str(error))

    def _handle_load(self):
        #load a saved scenario from JSON
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open JSON File", "", "JSON Files (*.json)"
        )
        if not filepath:
            return

        try:
            data = self.persistence.load_from_json(filepath)
            version_name = ""
            if isinstance(data, dict) and data.get("format") == "SismoLabScenario":
                version_name = data.get("version_name", "")
                self.controller.restore_scenario_state(data)
            else:
                events = data.get("events", []) if isinstance(data, dict) else data
                self.controller.replace_events(events)
            self._sync_controller_settings()
            self._refresh_event_views()
            version_message = (
                f" version '{version_name}'" if version_name else ""
            )
            self.log_message(
                f"Loaded{version_message}: {len(self.events)} active events "
                f"from {filepath}"
            )
            QMessageBox.information(
                self,
                "Scenario restored" if version_name else "Success",
                f"Loaded {len(self.events)} active events successfully."
                + (f"\nVersion: {version_name}" if version_name else ""),
            )
        except Exception as error:
            QMessageBox.critical(self, "Error", f"Failed to load file: {error}")

    def _handle_insert(self):
        #insert a new event from the form
        try:
            station = self.txt_station.text().strip()
            if not station:
                raise ValueError("Enter the reporting station.")

            event = Event(
                event_id=self.controller.generate_event_id(),
                magnitude=self.spn_mag.value(),
                depth=self.spn_z.value(),
                x=self.spn_x.value(),
                y=self.spn_y.value(),
                timestamp=self.controller.simulation_clock,
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
        #get the currently selected event id
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self, "No event selected", "Select an event in the table first."
            )
            return None

        id_item = self.table.item(selected_rows[0].row(), 0)
        return id_item.data(Qt.ItemDataRole.UserRole)

    def _handle_search(self):
        #search an event by id and show details
        raw_event_id = self.txt_search_id.text().strip()
        if not raw_event_id.isdigit():
            QMessageBox.warning(
                self, "Invalid ID", "Enter a numeric event ID."
            )
            return

        details = self.controller.get_event_search_details(int(raw_event_id))
        if details is None:
            QMessageBox.information(
                self, "Event not found", f"No event with ID {raw_event_id}."
            )
            return

        event = details["event"]
        access_label = (
            "Yes"
            if details["access_costly"]
            else "No"
        )
        QMessageBox.information(
            self,
            f"Event {event.display_id}",
            "\n".join(
                (
                    f"Magnitude: {event.magnitude}",
                    f"Depth: {event.depth} km",
                    f"Coordinates: ({event.x}, {event.y}) km",
                    f"Station: {event.station}",
                    f"Priority: {event.priority}",
                    f"Status: {event.status}",
                    f"Revision: {event.revision}",
                    f"AVL depth: {details['depth']}",
                    f"Search comparisons: {details['comparisons']}",
                    f"Costly access: {access_label} "
                    f"(L: {details['cost_threshold']})",
                )
            ),
        )

    def _handle_apply_costly_access_limit(self):
        #apply the costly-access threshold limit
        try:
            self.controller.set_costly_access_limit(
                self.spn_costly_access_limit.value()
            )
            self._refresh_event_views()
            self.log_message(
                f"Costly-access limit set to L={self.controller.costly_access_limit}"
            )
        except ValueError as error:
            QMessageBox.warning(self, "Invalid limit", str(error))

    def _handle_advance_clock(self):
        #advance the simulation clock
        try:
            clock = self.controller.advance_simulation_clock(
                self.spn_clock_advance.value()
            )
            self._refresh_event_views()
            self.log_message(f"Simulation clock advanced to {clock.isoformat()}")
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Invalid clock advance", str(error))

    def _handle_apply_archive_threshold(self):
        #apply the archive age threshold
        try:
            self.controller.set_archive_age_threshold(
                self.spn_archive_threshold.value()
            )
            self.log_message(
                "Archive threshold set to "
                f"T={self.controller.archive_age_threshold_hours:g} hours"
            )
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Invalid archive threshold", str(error))

    def _handle_archive_branch(self):
        #preview and archive eligible low-priority branches
        candidate = self.controller.preview_archive_candidate()
        if candidate is None:
            QMessageBox.information(
                self,
                "No eligible branch",
                "No subtree contains only low-priority events older than T.",
            )
            return

        event_ids = ", ".join(
            sorted(event.display_id for event in candidate["events"])
        )
        explanation = (
            f"Selected root: {candidate['root_event'].display_id}\n"
            f"Depth: {candidate['depth']}\n"
            f"Events: {candidate['count']}\n"
            f"Rule: every event has priority 1 and age > "
            f"{candidate['threshold_hours']:g} hours.\n\n"
            f"Archive: {event_ids}?"
        )
        answer = QMessageBox.question(
            self,
            "Confirm branch archive",
            explanation,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        result = self.controller.archive_eligible_branch()
        if result is None:
            QMessageBox.warning(
                self,
                "Archive cancelled",
                "The eligible branch changed before it could be archived.",
            )
            return
        self._refresh_event_views()
        self.log_message(
            f"Archived {result['count']} events rooted at "
            f"{result['root_event'].display_id}"
        )

    def _handle_show_history(self):
        #show archived event history
        archived_events = sorted(
            self.controller.event_manager.archived_events.values(),
            key=lambda event: event.id,
        )
        if not archived_events:
            QMessageBox.information(
                self, "Event history", "The archive is empty."
            )
            return
        rows = [
            (
                f"{event.display_id} | P{event.priority} | "
                f"M{event.magnitude:.1f} | Revision {event.revision} | "
                f"{event.timestamp.isoformat()}"
            )
            for event in archived_events
        ]
        QMessageBox.information(
            self, "Archived event history", "\n".join(rows)
        )

    def _sync_controller_settings(self):
        self.map_manager = self.controller.map_manager
        self.replica_manager = self.controller.replica_manager
        self.spn_costly_access_limit.setValue(
            self.controller.costly_access_limit
        )
        self.spn_archive_threshold.setValue(
            self.controller.archive_age_threshold_hours
        )
        self.spn_association_hours.setValue(
            self.controller.replica_manager.W_hours
        )
        self.spn_association_distance.setValue(
            self.controller.replica_manager.R_km
        )
        self.dt_report_timestamp.setDateTime(
            QDateTime.fromSecsSinceEpoch(
                int(self.controller.simulation_clock.timestamp()),
                Qt.TimeSpec.UTC,
            )
        )

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

    def _handle_mark_reviewed(self):
        event_id = self._selected_event_id()
        if event_id is None:
            return

        if self.controller.mark_event_as_reviewed(event_id):
            self.log_message(f"Marked SIS-{event_id:06d} as reviewed")
            self._refresh_event_views()
        else:
            QMessageBox.information(
                self,
                "Event already reviewed",
                "The selected event is already reviewed or no longer exists.",
            )

    def _handle_apply_association_settings(self):
        try:
            self.controller.set_association_limits(
                self.spn_association_hours.value(),
                self.spn_association_distance.value(),
            )
            self.replica_manager = self.controller.replica_manager
            self._refresh_event_views()
            self.log_message(
                "Association settings applied: "
                f"W={self.replica_manager.W_hours:g} hours, "
                f"R={self.replica_manager.R_km:g} km"
            )
        except (TypeError, ValueError) as error:
            QMessageBox.warning(
                self, "Invalid association settings", str(error)
            )

    def _handle_enqueue_report(self):
        try:
            station = self.txt_report_station.text().strip()
            if not station:
                raise ValueError("Enter the reporting station.")

            self.controller.enqueue_event_report(
                {
                    "event_id": self.spn_report_id.value(),
                    "revision": self.spn_report_revision.value(),
                    "magnitude": self.spn_report_magnitude.value(),
                    "depth": self.spn_report_depth.value(),
                    "x": self.spn_report_x.value(),
                    "y": self.spn_report_y.value(),
                    "timestamp": (
                        self.dt_report_timestamp.dateTime()
                        .toUTC()
                        .toPyDateTime()
                        .isoformat()
                    ),
                    "station": station,
                    "is_populated": self.map_manager.is_in_populated_zone(
                        self.spn_report_x.value(), self.spn_report_y.value()
                    ),
                }
            )
            self._refresh_event_views()
            self.log_message(
                f"Queued revision {self.spn_report_revision.value()} "
                f"of SIS-{self.spn_report_id.value():06d}"
            )
        except (TypeError, ValueError) as error:
            QMessageBox.warning(self, "Invalid report", str(error))

    def _handle_process_report(self):
        try:
            result = self.controller.process_next_event_report()
        except (TypeError, ValueError, KeyError, RuntimeError) as error:
            QMessageBox.critical(self, "Report processing failed", str(error))
            return

        messages = {
            "empty": "The report queue is empty.",
            "created": "New event created from the station report.",
            "confirmed": "Report confirmed; station added to the event.",
            "duplicate": "This station has already confirmed the event.",
            "updated": "Newer report revision applied to the event.",
            "reactivated": "Newer revision restored the archived event to the active tree.",
            "confirmed_archived": "Report confirmed an archived event; it remains archived.",
            "stale": "Older report discarded; current event was not changed.",
            "conflict": "Same revision contains conflicting event data.",
            "id_unavailable": "This event ID is reserved and cannot be reused.",
        }
        self._refresh_event_views()
        self.log_message(f"FIFO processing: {result}")
        if result == "empty":
            QMessageBox.information(self, "Report queue", messages[result])
        elif result in ("conflict", "id_unavailable"):
            QMessageBox.warning(self, "Report not applied", messages[result])
        else:
            QMessageBox.information(self, "Report processed", messages[result])

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
            self.controller.start_stress_mode()
            self.log_message("Stress simulation started; automatic rotations paused.")
            self._refresh_event_views()
            return

        try:
            rotations = self.controller.recover_stress_mode()
        except RuntimeError as error:
            QMessageBox.critical(self, "AVL recovery failed", str(error))
            self.log_message(f"AVL recovery failed: {error}")
            return

        self.btn_stress.setText("Start Stress Simulation")
        self.log_message(f"Stress simulation finished; performed {rotations} rotations.")
        self._refresh_event_views()

    def _handle_undo(self):
        if not self.controller.undo():
            QMessageBox.information(
                self, "Nothing to undo", "There are no event changes to undo."
            )
            return

        self._sync_controller_settings()
        self.log_message("Undid the last event change.")
        self._refresh_event_views()

    def _refresh_event_views(self):
        events = self.events
        costly_event_ids = {
            item["event"].id
            for item in self.controller.query_costly_access_events()["events"]
        }
        self.lbl_simulation_clock.setText(
            f"Simulation clock (UTC): "
            f"{self.controller.simulation_clock.isoformat(timespec='seconds')}"
        )
        metrics = self.controller.get_dashboard_metrics()
        priorities = metrics["priority_counts"]
        rotation_cases = metrics["rotation_cases"]
        counters = metrics["operation_counters"]
        self.lbl_system_metrics.setText(
            f"Active: {metrics['active_events']} | "
            f"Archived: {metrics['archived_events']} | "
            f"Height: {metrics['height']} | Leaves: {metrics['leaves']}\n"
            f"Priorities P1/P2/P3: {priorities[1]}/{priorities[2]}/"
            f"{priorities[3]} | Pending: {metrics['pending_events']} | "
            f"Costly access: {metrics['costly_access_events']}\n"
            f"Rotation cases LL/RR/LR/RL: {rotation_cases['LL']}/"
            f"{rotation_cases['RR']}/{rotation_cases['LR']}/"
            f"{rotation_cases['RL']} | Simple left/right: "
            f"{metrics['simple_left_rotations']}/"
            f"{metrics['simple_right_rotations']}\n"
            f"Corrections: {counters['corrections_accepted']} | "
            f"Discarded reports: {counters['reports_discarded']} | "
            f"Conflicts: {counters['conflicts']} | "
            f"Archived branches/events: {counters['mass_archives']}/"
            f"{counters['events_archived']}"
        )
        self.map_viewer.set_data(events, self.map_manager.zones)
        self.tree_viewer.populate_tree(
            events
            + list(self.controller.event_manager.archived_events.values()),
            self.replica_manager,
            self.controller.tree.root,
            self.controller.build_comparison_tree().root,
        )
        self.table.setRowCount(len(events))
        queued_reports = self.controller.report_queue.to_list()
        self.report_queue_table.setRowCount(len(queued_reports))
        for row, report in enumerate(queued_reports):
            report_values = (
                f"SIS-{report['event_id']:06d}",
                report["revision"],
                report["station"],
            )
            for column, value in enumerate(report_values):
                self.report_queue_table.setItem(
                    row, column, QTableWidgetItem(str(value))
                )
        if hasattr(self, "btn_stress"):
            self.btn_stress.setText(
                "Finish Stress Simulation"
                if self.controller.stress_manager.is_stress_mode
                else "Start Stress Simulation"
            )
            self.lbl_stress_mode.setText(
                "Automatic AVL balancing is paused."
                if self.controller.stress_manager.is_stress_mode
                else "Automatic AVL balancing is active."
            )

        for row, event in enumerate(events):
            values = (
                event.display_id,
                event.x,
                event.y,
                event.depth,
                event.magnitude,
                event.timestamp,
                "COSTLY"
                if event.id in costly_event_ids
                else "Normal",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, event.id)
                self.table.setItem(row, column, item)
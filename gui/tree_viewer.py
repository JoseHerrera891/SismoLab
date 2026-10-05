# gui/tree_viewer.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel
from PyQt6.QtCore import Qt


class TreeViewer(QWidget):
    """
    Tree Visualization component for displaying main seismic events
    and their associated replica hierarchies.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """
        Initializes layout and tree structure controls.
        """
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Section Header Label
        header_label = QLabel("Seismic Event & Replica Hierarchy")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px;")
        layout.addWidget(header_label)

        # Tree Widget Construction
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Event ID", "Magnitude", "Coordinates (X, Y, Z)", "Timestamp"])
        layout.addWidget(self.tree)

    def populate_tree(self, events: list, replica_manager):
        """
        Populates the tree widget with main events as root nodes and 
        their corresponding replicas as child nodes.
        """
        self.tree.clear()

        # Group events by main reference
        main_events = []
        replicas_by_main = {}

        for ev in events:
            candidates = replica_manager.get_candidates(ev, events)
            main_ref = replica_manager.select_main_reference(ev, candidates)

            if main_ref is None:
                # Event is a main reference (root node)
                main_events.append(ev)
            else:
                # Event is a replica of main_ref
                if main_ref.id not in replicas_by_main:
                    replicas_by_main[main_ref.id] = []
                replicas_by_main[main_ref.id].append(ev)

        # Render Tree Nodes
        for main_ev in main_events:
            root_item = QTreeWidgetItem([
                main_ev.display_id,
                f"M {main_ev.magnitude}",
                f"({main_ev.x}, {main_ev.y}, {main_ev.z})",
                str(main_ev.timestamp)
            ])
            
            # Attach child replicas if any exist
            if main_ev.id in replicas_by_main:
                for replica in replicas_by_main[main_ev.id]:
                    child_item = QTreeWidgetItem([
                        f"Replica: {replica.display_id}",
                        f"M {replica.magnitude}",
                        f"({replica.x}, {replica.y}, {replica.z})",
                        str(replica.timestamp)
                    ])
                    root_item.addChild(child_item)

            self.tree.addTopLevelItem(root_item)

        self.tree.expandAll()
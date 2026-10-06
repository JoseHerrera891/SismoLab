from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from core.bst_tree import measure_tree


class AVLCanvas(QWidget):
    #canvas with tree and nodes

    NODE_WIDTH = 96
    NODE_HEIGHT = 58
    HORIZONTAL_GAP = 28
    LEVEL_GAP = 92
    PADDING = 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self.root = None
        self.positions = {}
        self.edges = []
        self.setMinimumSize(400, 240)

    def set_root(self, root):
        self.root = root
        self.positions = {}
        self.edges = []
        #sets root and its properties
        inorder_nodes = []
        max_depth = 0
        stack = []
        current = root
        depth = 0
        while current is not None or stack:
            while current is not None:
                stack.append((current, depth))
                current = current.getLeftChild()
                depth += 1
            current, depth = stack.pop()
            inorder_nodes.append((current, depth))
            max_depth = max(max_depth, depth)
            current = current.getRightChild()
            depth += 1

        node_spacing = self.NODE_WIDTH + self.HORIZONTAL_GAP
        for index, (node, depth) in enumerate(inorder_nodes):
            self.positions[node] = QPointF(
                self.PADDING + index * node_spacing + self.NODE_WIDTH / 2,
                self.PADDING + depth * self.LEVEL_GAP + self.NODE_HEIGHT / 2,
            )
            if node.getLeftChild() is not None:
                self.edges.append((node, node.getLeftChild()))
            if node.getRightChild() is not None:
                self.edges.append((node, node.getRightChild()))

        content_width = (
            self.PADDING * 2
            + max(1, len(inorder_nodes)) * node_spacing
            - self.HORIZONTAL_GAP
        )
        content_height = (
            self.PADDING * 2
            + (max_depth + 1) * self.LEVEL_GAP
            - (self.LEVEL_GAP - self.NODE_HEIGHT)
        )
        self.setMinimumSize(max(400, content_width), max(240, content_height))
        self.resize(max(400, content_width), max(240, content_height))
        self.update()

    def sizeHint(self):
        return self.minimumSize()
        #paint event node
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f8fafc"))

        if self.root is None:
            painter.setPen(QColor("#64748b"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "No events in this tree",
            )
            return

        painter.setPen(QPen(QColor("#64748b"), 2))
        for parent, child in self.edges:
            painter.drawLine(self.positions[parent], self.positions[child])
        #same as the map, the tree has 3 color for the 3 priorities
        priority_colors = {
            1: QColor("#4da6ff"),
            2: QColor("#d39b00"),
            3: QColor("#ff4d4d"),
        }
        for node, center in self.positions.items():
            event = node.getValue()
            rect_x = center.x() - self.NODE_WIDTH / 2
            rect_y = center.y() - self.NODE_HEIGHT / 2

            color = priority_colors[event.priority]
            fill = QColor(color)
            fill.setAlpha(35)
            painter.setPen(QPen(color, 2))
            painter.setBrush(fill)
            painter.drawRoundedRect(
                int(rect_x),
                int(rect_y),
                self.NODE_WIDTH,
                self.NODE_HEIGHT,
                8,
                8,
            )

            painter.setPen(QColor("#172033"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(
                int(rect_x + 4),
                int(rect_y + 8),
                self.NODE_WIDTH - 8,
                20,
                Qt.AlignmentFlag.AlignCenter,
                event.display_id,
            )
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(
                int(rect_x + 4),
                int(rect_y + 29),
                self.NODE_WIDTH - 8,
                18,
                Qt.AlignmentFlag.AlignCenter,
                f"P{event.priority} | M{event.magnitude:.1f}",
            )


class TreeViewer(QWidget):
    #opens the two tress in a separate window

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events = []
        self._replica_manager = None
        self._avl_root = None
        self._bst_root = None
        self._tree_window = None
        self.avl_canvas = None
        self.bst_canvas = None
        self.avl_metrics_label = None
        self.bst_metrics_label = None
        self.replica_tree = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.btn_show_trees = QPushButton("View AVL, BST and Replica Trees")
        self.btn_show_trees.clicked.connect(self._show_tree_window)
        layout.addWidget(self.btn_show_trees)

    def _show_tree_window(self):
        if self._tree_window is None:
            self._create_tree_window()
        self._refresh_tree_window()
        self._tree_window.show()
        self._tree_window.raise_()
        self._tree_window.activateWindow()
        #the real function of this file, load the avl and bst tree from core and uses it to show the graphcis trees
    def _create_tree_window(self):
        self._tree_window = QDialog(self)
        self._tree_window.setWindowTitle("AVL, BST and Replica Hierarchy")
        self._tree_window.resize(1500, 700)
        self._tree_window.setAttribute(
            Qt.WidgetAttribute.WA_DeleteOnClose, True
        )
        self._tree_window.finished.connect(self._on_tree_window_closed)

        layout = QVBoxLayout(self._tree_window)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        avl_panel = QWidget()
        avl_layout = QVBoxLayout(avl_panel)
        avl_layout.addWidget(QLabel("AVL Tree"))
        self.avl_metrics_label = QLabel()
        avl_layout.addWidget(self.avl_metrics_label)
        self.avl_canvas = AVLCanvas()
        avl_scroll_area = QScrollArea()
        avl_scroll_area.setWidgetResizable(False)
        avl_scroll_area.setWidget(self.avl_canvas)
        avl_layout.addWidget(avl_scroll_area)

        bst_panel = QWidget()
        bst_layout = QVBoxLayout(bst_panel)
        bst_layout.addWidget(QLabel("Unbalanced BST"))
        self.bst_metrics_label = QLabel()
        bst_layout.addWidget(self.bst_metrics_label)
        self.bst_canvas = AVLCanvas()
        bst_scroll_area = QScrollArea()
        bst_scroll_area.setWidgetResizable(False)
        bst_scroll_area.setWidget(self.bst_canvas)
        bst_layout.addWidget(bst_scroll_area)

        replica_panel = QWidget()
        replica_layout = QVBoxLayout(replica_panel)
        replica_layout.addWidget(QLabel("Replica Hierarchy"))
        self.replica_tree = QTreeWidget()
        self.replica_tree.setHeaderLabels(
            ["Event ID", "Magnitude", "Coordinates (X, Y, Z)", "Timestamp"]
        )
        replica_layout.addWidget(self.replica_tree)

        splitter.addWidget(avl_panel)
        splitter.addWidget(bst_panel)
        splitter.addWidget(replica_panel)
        splitter.setSizes([500, 500, 500])
        layout.addWidget(splitter)

    def _on_tree_window_closed(self):
        self._tree_window = None
        self.avl_canvas = None
        self.bst_canvas = None
        self.avl_metrics_label = None
        self.bst_metrics_label = None
        self.replica_tree = None
        #this triggers only when a change is done in the event list, modifi it, eliminate, etc.
    def _refresh_tree_window(self):
        if self._tree_window is None:
            return

        self.avl_canvas.set_root(self._avl_root)
        self.bst_canvas.set_root(self._bst_root)
        self._set_metrics_label(self.avl_metrics_label, self._avl_root)
        self._set_metrics_label(self.bst_metrics_label, self._bst_root)
        self.replica_tree.clear()

        if self._replica_manager is None:
            return

        main_events = []
        replicas_by_main = {}

        for event in self._events:
            candidates = self._replica_manager.get_candidates(
                event, self._events
            )
            main_reference = self._replica_manager.select_main_reference(
                event, candidates
            )

            if main_reference is None:
                main_events.append(event)
            else:
                replicas_by_main.setdefault(main_reference.id, []).append(event)

        for main_event in main_events:
            root_item = QTreeWidgetItem(
                [
                    main_event.display_id,
                    f"M {main_event.magnitude}",
                    f"({main_event.x}, {main_event.y}, {main_event.z})",
                    str(main_event.timestamp),
                ]
            )

            for replica in replicas_by_main.get(main_event.id, []):
                root_item.addChild(
                    QTreeWidgetItem(
                        [
                            f"Replica: {replica.display_id}",
                            f"M {replica.magnitude}",
                            f"({replica.x}, {replica.y}, {replica.z})",
                            str(replica.timestamp),
                        ]
                    )
                )

            self.replica_tree.addTopLevelItem(root_item)

        self.replica_tree.expandAll()

    @staticmethod
    def _set_metrics_label(label, root): #this shows the metric at the end of the program
        metrics = measure_tree(root)
        label.setText(
            f"Nodes: {metrics['nodes']} | Height: {metrics['height']} | "
            f"Leaves: {metrics['leaves']} | Avg. search comparisons: "
            f"{metrics['average_search_comparisons']:.2f}"
        )

    def populate_tree(
        self, events: list, replica_manager, avl_root=None, bst_root=None
    ):
        #store de last data and puts it on the tree
        self._events = list(events)
        self._replica_manager = replica_manager
        self._avl_root = avl_root
        self._bst_root = bst_root
        self._refresh_tree_window()

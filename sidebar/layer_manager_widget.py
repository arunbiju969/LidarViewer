from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt
import os

class LayerManagerWidget(QWidget):
    layer_selected = Signal(str)  # Emits the selected layer's UUID
    layer_added = Signal()
    layer_removed = Signal(str)  # Emits the removed layer's UUID
    layer_toggled = Signal(str, bool)  # Emits (uuid, checked)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("layer_manager_widget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.label = QLabel("Layers")
        layout.addWidget(self.label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.remove_btn = QPushButton("Remove")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        layout.addLayout(btn_layout)

        self.add_btn.clicked.connect(self._on_add)
        self.remove_btn.clicked.connect(self._on_remove)
        self.list_widget.currentItemChanged.connect(self._on_select)
        self.list_widget.itemChanged.connect(self._on_item_changed)

    def set_layers(self, layers, checked_uuids=None):
        """
        layers: list of (uuid, file_path) tuples
        checked_uuids: set of uuids to be checked (default: all checked)
        """
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        if checked_uuids is None:
            checked_uuids = set(uuid for uuid, _ in layers)
        for uuid, file_path in layers:
            filename = os.path.basename(file_path)
            item = QListWidgetItem(f"{filename} [{uuid[:8]}]")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Checked if uuid in checked_uuids else Qt.Unchecked)
            item.setData(Qt.UserRole, uuid)  # Store full UUID
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)

    def _on_add(self):
        self.layer_added.emit()

    def _on_remove(self):
        current = self.list_widget.currentRow()
        if current >= 0:
            uuid = self.get_selected_uuid()
            if uuid:
                self.layer_removed.emit(uuid)

    def _on_select(self, current, previous):
        uuid = self.get_selected_uuid()
        if uuid:
            print(f"[DEBUG] Emitting layer_selected: uuid={uuid}")
            self.layer_selected.emit(uuid)

    def _on_item_changed(self, item):
        uuid = self._extract_uuid_from_item(item)
        if uuid:
            checked = item.checkState() == Qt.Checked
            print(f"[DEBUG] Emitting layer_toggled: uuid={uuid}, checked={checked}")
            self.layer_toggled.emit(uuid, checked)

    def get_selected_uuid(self):
        current = self.list_widget.currentRow()
        if current >= 0:
            item = self.list_widget.item(current)
            return self._extract_uuid_from_item(item)
        return None

    def _extract_uuid_from_item(self, item):
        if item is not None:
            return item.data(Qt.UserRole)
        return None

    def set_layer_checked(self, uuid, checked=True):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == uuid:
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                break

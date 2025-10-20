from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel
from PyQt6.QtCore import pyqtSignal as Signal, Qt
import os


class LayerManagerUIStyles:
    """Theme-aware styling for layer manager components"""
    
    @staticmethod
    def get_button_style():
        """Enhanced button styling for dark theme"""
        return """
            QPushButton {
                background-color: #2e2e2e;
                border: 2px solid #3daee9;
                border-radius: 6px;
                padding: 6px 8px;
                color: white;
                font-weight: bold;
                min-height: 16px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #5cbef0;
            }
            QPushButton:pressed {
                background-color: #252525;
                border-color: #2a9dd4;
            }
        """
    
    @staticmethod
    def get_button_style_light():
        """Enhanced button styling for light theme"""
        return """
            QPushButton {
                background-color: #f0f0f0;
                border: 2px solid #3daee9;
                border-radius: 6px;
                padding: 6px 8px;
                color: #333;
                font-weight: bold;
                min-height: 16px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #5cbef0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
                border-color: #2a9dd4;
            }
        """
    
    @staticmethod
    def get_listwidget_style():
        """Enhanced list widget styling for dark theme"""
        return """
            QListWidget {
                background-color: #2e2e2e;
                border: 2px solid #3daee9;
                border-radius: 4px;
                color: white;
                selection-background-color: #3daee9;
                selection-color: white;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #444;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #3daee9;
            }
        """
    
    @staticmethod
    def get_label_style():
        """Label styling for dark theme"""
        return """
            QLabel {
                color: white;
                font-weight: bold;
            }
        """
    
    @staticmethod
    def should_apply_dark_layer_style():
        """Check if we should apply dark theme styling"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                # Try to get the main window and check its theme
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'sidebar') and hasattr(widget.sidebar, 'theme_box'):
                        current_theme = widget.sidebar.theme_box.currentText()
                        return current_theme.lower() == "dark"
        except Exception as e:
            print(f"[DEBUG] LayerManager: Theme detection failed: {e}")
        
        return False


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
        
        # Store styled components for theme updates
        self._styled_components = [
            ('button', self.add_btn),
            ('button', self.remove_btn),
            ('listwidget', self.list_widget),
            ('label', self.label),
        ]

        self.add_btn.clicked.connect(self._on_add)
        self.remove_btn.clicked.connect(self._on_remove)
        self.list_widget.currentItemChanged.connect(self._on_select)
        self.list_widget.itemChanged.connect(self._on_item_changed)
    
    def update_theme_styling(self):
        """Update theme styling for all layer manager components"""
        is_dark = LayerManagerUIStyles.should_apply_dark_layer_style()
        
        for component_type, widget in self._styled_components:
            if component_type == 'button':
                if is_dark:
                    widget.setStyleSheet(LayerManagerUIStyles.get_button_style())
                else:
                    # Apply enhanced styling even in light theme
                    widget.setStyleSheet(LayerManagerUIStyles.get_button_style_light())
            elif component_type == 'listwidget':
                if is_dark:
                    widget.setStyleSheet(LayerManagerUIStyles.get_listwidget_style())
                else:
                    widget.setStyleSheet("")  # Clear custom styling for light theme
            elif component_type == 'label':
                if is_dark:
                    widget.setStyleSheet(LayerManagerUIStyles.get_label_style())
                else:
                    widget.setStyleSheet("")  # Clear custom styling for light theme

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

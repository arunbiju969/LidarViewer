from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout, QComboBox, QPushButton, QColorDialog, QHBoxLayout
)
from PySide6.QtCore import Qt
from .layer_manager_widget import LayerManagerWidget

class SidebarWidget(QWidget):
    def set_status(self, text):
        print(f"[DEBUG] set_status called with text: {text}")
        self.status_label.setText(text)

    def update_file_info(self, filename, num_points):
        print(f"[DEBUG] update_file_info called with filename: {filename}, num_points: {num_points}")
        self.info_file.setText(filename)
        self.info_points.setText(str(num_points))

    def update_dimensions(self, dims, enabled=True):
        print(f"[DEBUG] update_dimensions called with dims: {dims}, enabled: {enabled}")
        self.color_controls.update_dimensions(dims, enabled)

    def update_layers(self, layers, current_uuid=None, checked_uuids=None):
        """
        layers: list of (uuid, file_path)
        current_uuid: uuid to select
        checked_uuids: set of uuids to be checked (visible)
        """
        self.layer_manager.set_layers(layers, checked_uuids=checked_uuids)
        # Select the current layer if provided
        if current_uuid:
            for i in range(self.layer_manager.list_widget.count()):
                text = self.layer_manager.list_widget.item(i).text()
                if f"[{current_uuid[:8]}]" in text:
                    self.layer_manager.list_widget.setCurrentRow(i)
                    break

    def __init__(self, parent=None):
        print("[DEBUG] SidebarWidget __init__ called")
        super().__init__(parent)
        self.layer_manager = LayerManagerWidget()
        self.button = QPushButton("Open LAS/LAZ File")
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.info_group = QGroupBox("Point Cloud Info")
        self.info_group.setCheckable(True)
        self.info_group.setChecked(True)
        self.info_group.setMinimumHeight(180)
        self.info_group.setMinimumWidth(220)
        self.setFixedWidth(260)
        self.setObjectName("sidebar")
        self.setStyleSheet("#sidebar { min-width: 260px; max-width: 260px; width: 260px; border: 2px solid #3daee9; border-radius: 8px; background: #f8f8f8; }")
        self.info_layout = QFormLayout()
        self.info_file = QLabel("-")
        self.info_points = QLabel("-")
        self.info_layout.addRow("File:", self.info_file)
        self.info_layout.addRow("Points:", self.info_points)
        self.info_group.setLayout(self.info_layout)
        from .color_controls import ColorControlsWidget
        from .point_size_controls import PointSizeControlsWidget
        self.color_controls = ColorControlsWidget()
        self.point_size_controls = PointSizeControlsWidget()
        self.projection_box = QComboBox()
        self.projection_box.addItems(["Parallel", "Perspective"])
        self.projection_box.setCurrentIndex(0)
        self.theme_box = QComboBox()
        self.theme_box.addItems(["Light", "Dark"])
        self.theme_box.setCurrentIndex(0)
        # New layout: top = layer manager, bottom = rest of sidebar
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.layer_manager)
        # Bottom part (existing controls)
        bottom_layout = QVBoxLayout()
        bottom_layout.addWidget(self.button)
        bottom_layout.addWidget(self.status_label)
        bottom_layout.addWidget(self.info_group)
        bottom_layout.addWidget(self.color_controls)
        bottom_layout.addWidget(QLabel("Point Size:"))
        bottom_layout.addWidget(self.point_size_controls)
        bottom_layout.addWidget(QLabel("Projection:"))
        bottom_layout.addWidget(self.projection_box)
        bottom_layout.addWidget(QLabel("Theme:"))
        bottom_layout.addWidget(self.theme_box)
        bottom_layout.addStretch(1)
        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)
        print("[DEBUG] SidebarWidget __init__ complete")

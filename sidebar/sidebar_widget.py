from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout, QComboBox, QPushButton, QColorDialog, QHBoxLayout
)
from PySide6.QtCore import Qt

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
    def __init__(self, parent=None):
        print("[DEBUG] SidebarWidget __init__ called")
        super().__init__(parent)
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
        # Add border for light theme as well, use :not([styleSheet]) to override only if not themed
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

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.button)
        left_layout.addWidget(self.status_label)
        left_layout.addWidget(self.info_group)
        left_layout.addWidget(self.color_controls)
        left_layout.addWidget(QLabel("Point Size:"))
        left_layout.addWidget(self.point_size_controls)
        left_layout.addWidget(QLabel("Projection:"))
        left_layout.addWidget(self.projection_box)
        left_layout.addWidget(QLabel("Theme:"))
        left_layout.addWidget(self.theme_box)
        left_layout.addStretch(1)
        self.setLayout(left_layout)
        print("[DEBUG] SidebarWidget __init__ complete")

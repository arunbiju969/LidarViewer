from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QColorDialog)
from PySide6.QtCore import Qt

class ColorControlsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.on_custom_color_set = None  # Callback for color set

        # Color by dropdown
        self.dimension_box = QComboBox()
        self.dimension_box.addItem("(No file loaded)")
        self.dimension_box.setEnabled(False)

        # Colormap dropdown
        self.colormap_box = QComboBox()
        self.colormap_box.addItems([
            "viridis", "plasma", "inferno", "magma", "cividis", "jet", "cool", "hot", "spring", "summer", "autumn", "winter", "gray", "Custom"
        ])
        self.colormap_box.setCurrentText("viridis")

        # Color pickers for custom gradient
        self.color_start_btn = QPushButton("Start Color")
        self.color_mid_btn = QPushButton("Mid Color")
        self.color_end_btn = QPushButton("End Color")
        self.color_start_btn.setStyleSheet("background: #0000ff")
        self.color_mid_btn.setStyleSheet("background: #00ff00")
        self.color_end_btn.setStyleSheet("background: #ff0000")
        self.color_start = '#0000ff'
        self.color_mid = '#00ff00'
        self.color_end = '#ff0000'

        def pick_color(btn, attr):
            dlg = QColorDialog()
            if dlg.exec():
                color = dlg.selectedColor().name()
                btn.setStyleSheet(f"background: {color}")
                setattr(self, attr, color)
                if self.on_custom_color_set:
                    print(f"[DEBUG] [ColorControlsWidget] Calling on_custom_color_set after picking {attr}: {color}")
                    self.on_custom_color_set()

        self.color_start_btn.clicked.connect(lambda: pick_color(self.color_start_btn, 'color_start'))
        self.color_mid_btn.clicked.connect(lambda: pick_color(self.color_mid_btn, 'color_mid'))
        self.color_end_btn.clicked.connect(lambda: pick_color(self.color_end_btn, 'color_end'))

        color_layout = QHBoxLayout()
        color_layout.addWidget(self.color_start_btn)
        color_layout.addWidget(self.color_mid_btn)
        color_layout.addWidget(self.color_end_btn)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Color by:"))
        layout.addWidget(self.dimension_box)
        layout.addWidget(QLabel("Colormap:"))
        layout.addWidget(self.colormap_box)
        layout.addLayout(color_layout)
        self.setLayout(layout)

    def update_dimensions(self, dims, enabled=True):
        self.dimension_box.blockSignals(True)
        self.dimension_box.clear()
        if dims:
            self.dimension_box.addItems(dims)
            self.dimension_box.setEnabled(enabled)
        else:
            self.dimension_box.addItem("(No color dimension)")
            self.dimension_box.setEnabled(False)
        self.dimension_box.blockSignals(False)

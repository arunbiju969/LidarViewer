from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider
from PySide6.QtCore import Qt

class PointSizeControlsWidget(QWidget):
    def __init__(self, parent=None, min_size=1, max_size=20, default_size=3):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.label = QLabel(f"Point Size: {default_size}", self)
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setMinimum(min_size)
        self.slider.setMaximum(max_size)
        self.slider.setValue(default_size)
        self.slider.setTickInterval(1)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.slider)
        self.setLayout(self.layout)
        self.slider.valueChanged.connect(self._on_slider_changed)
        self.on_point_size_changed = None  # Callback for parent

    def _on_slider_changed(self, value):
        self.label.setText(f"Point Size: {value}")
        if self.on_point_size_changed:
            self.on_point_size_changed(value)

    def set_point_size(self, value):
        self.slider.setValue(value)

    def get_point_size(self):
        return self.slider.value()

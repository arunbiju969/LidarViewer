from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider
from PySide6.QtCore import Qt


class PointSizeUIStyles:
    """Theme-aware styling for point size controls"""
    
    @staticmethod
    def get_label_style():
        """Label styling for dark theme"""
        return """
            QLabel {
                color: white;
            }
        """
    
    @staticmethod
    def get_slider_style():
        """Enhanced slider styling for dark theme"""
        return """
            QSlider::groove:horizontal {
                border: 1px solid #3daee9;
                height: 6px;
                background: #2e2e2e;
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3daee9;
                border: 1px solid #3daee9;
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #5cbef0;
            }
            QSlider::sub-page:horizontal {
                background: #3daee9;
                border: 1px solid #3daee9;
                height: 6px;
                border-radius: 3px;
            }
        """
    
    @staticmethod
    def should_apply_dark_pointsize_style():
        """Check if we should apply dark theme styling"""
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                # Try to get the main window and check its theme
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'sidebar') and hasattr(widget.sidebar, 'theme_box'):
                        current_theme = widget.sidebar.theme_box.currentText()
                        return current_theme.lower() == "dark"
        except Exception as e:
            print(f"[DEBUG] PointSizeControls: Theme detection failed: {e}")
        
        return False


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
        
        # Store styled components for theme updates
        self._styled_components = [
            ('label', self.label),
            ('slider', self.slider),
        ]

    def _on_slider_changed(self, value):
        self.label.setText(f"Point Size: {value}")
        if self.on_point_size_changed:
            self.on_point_size_changed(value)

    def set_point_size(self, value):
        self.slider.setValue(value)

    def get_point_size(self):
        return self.slider.value()
    
    def update_theme_styling(self):
        """Update theme styling for point size control components"""
        is_dark = PointSizeUIStyles.should_apply_dark_pointsize_style()
        
        for component_type, widget in self._styled_components:
            if is_dark:
                if component_type == 'label':
                    widget.setStyleSheet(PointSizeUIStyles.get_label_style())
                elif component_type == 'slider':
                    widget.setStyleSheet(PointSizeUIStyles.get_slider_style())
            else:
                widget.setStyleSheet("")  # Clear custom styling for light theme

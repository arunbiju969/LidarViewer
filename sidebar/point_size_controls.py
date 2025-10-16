from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider, QPushButton
from .sidebar_widget import SidebarUIStyles
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
        self.min_size = min_size
        self.max_size = max_size
        self.value = default_size
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        self.btn_decrease = QPushButton("−", self)  # Use Unicode minus for better appearance
        self.btn_increase = QPushButton("+", self)
        self.btn_decrease.setFixedWidth(28)
        self.btn_increase.setFixedWidth(28)
        # Apply sidebar button style for consistency
        self.btn_decrease.setStyleSheet(SidebarUIStyles.get_button_style())
        self.btn_increase.setStyleSheet(SidebarUIStyles.get_button_style())
        # Set font to match other sidebar buttons (bold, same size)
        font = self.btn_decrease.font()
        font.setBold(True)
        font.setPointSize(12)
        self.btn_decrease.setFont(font)
        self.btn_increase.setFont(font)
        self.btn_decrease.clicked.connect(self._decrease)
        self.btn_increase.clicked.connect(self._increase)
        self.label = QLabel(f"{self.value}", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setMinimumWidth(32)
        self.layout.addStretch(1)
        self.layout.addWidget(self.btn_decrease)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.btn_increase)
        self.layout.addStretch(1)
        self.setLayout(self.layout)
        self.on_point_size_changed = None  # Callback for parent
        # Store styled components for theme updates
        self._styled_components = [
            ('label', self.label),
            ('button', self.btn_decrease),
            ('button', self.btn_increase),
        ]

    def _decrease(self):
        if self.value > self.min_size:
            self.value -= 1
            self.label.setText(str(self.value))
            if self.on_point_size_changed:
                self.on_point_size_changed(self.value)

    def _increase(self):
        if self.value < self.max_size:
            self.value += 1
            self.label.setText(str(self.value))
            if self.on_point_size_changed:
                self.on_point_size_changed(self.value)

    def set_point_size(self, value):
        if self.min_size <= value <= self.max_size:
            self.value = value
            self.label.setText(str(self.value))

    def get_point_size(self):
        return self.value

    def update_theme_styling(self):
        """Update theme styling for point size control components"""
        is_dark = PointSizeUIStyles.should_apply_dark_pointsize_style()
        for component_type, widget in self._styled_components:
            if is_dark:
                if component_type == 'label':
                    widget.setStyleSheet(PointSizeUIStyles.get_label_style())
                elif component_type == 'button':
                    widget.setStyleSheet(SidebarUIStyles.get_button_style())
            else:
                widget.setStyleSheet("")  # Clear custom styling for light theme

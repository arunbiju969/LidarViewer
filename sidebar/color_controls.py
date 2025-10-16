from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QColorDialog)
from PySide6.QtCore import Qt

from layers.layer_db import VALUE_COLORMAP_OPTION


class ColorControlsUIStyles:
    """Theme-aware styling for color controls components"""
    
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
    def get_combobox_style():
        """Enhanced combobox styling for dark theme"""
        return """
            QComboBox {
                background-color: #2e2e2e;
                border: 2px solid #3daee9;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #5cbef0;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 1px;
                border-left-color: #3daee9;
                border-left-style: solid;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: #3daee9;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid white;
            }
            QComboBox QAbstractItemView {
                background-color: #2e2e2e;
                border: 1px solid #3daee9;
                color: white;
                selection-background-color: #3daee9;
            }
        """
    
    @staticmethod
    def should_apply_dark_color_style():
        """Check if we should apply dark theme styling"""
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                # Try to get the main window and check its theme
                for widget in app.topLevelWidgets():  # type: ignore[attr-defined]
                    if hasattr(widget, 'sidebar') and hasattr(widget.sidebar, 'theme_box'):
                        current_theme = widget.sidebar.theme_box.currentText()
                        return current_theme.lower() == "dark"
        except Exception as e:
            print(f"[DEBUG] ColorControls: Theme detection failed: {e}")
        
        return False


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
            "viridis", "plasma", "inferno", "magma", "cividis", "jet", "cool", "hot", "spring", "summer", "autumn", "winter", "gray", VALUE_COLORMAP_OPTION, "Custom"
        ])
        self.colormap_box.setCurrentText("viridis")
        self.colormap_box.currentTextChanged.connect(self._on_colormap_changed)

        # Color pickers for custom gradient
        self.color_start_btn = QPushButton("Start")
        self.color_mid_btn = QPushButton("Mid")
        self.color_end_btn = QPushButton("End")
        self.color_start_btn.setStyleSheet("background: #87ceeb; color: #333; font-size: 10px; font-weight: bold;")
        self.color_mid_btn.setStyleSheet("background: #98fb98; color: #333; font-size: 10px; font-weight: bold;")
        self.color_end_btn.setStyleSheet("background: #ffa0a0; color: #333; font-size: 10px; font-weight: bold;")
        self.color_start = '#87ceeb'
        self.color_mid = '#98fb98'
        self.color_end = '#ffa0a0'
        
        # Store styled components for theme updates
        self._styled_components = [
            ('combobox', self.dimension_box),
            ('combobox', self.colormap_box),
            ('button', self.color_start_btn),
            ('button', self.color_mid_btn),
            ('button', self.color_end_btn),
        ]

        def pick_color(btn, attr):
            dlg = QColorDialog()
            if dlg.exec():
                color = dlg.selectedColor().name()
                btn.setStyleSheet(f"background: {color}; color: #333; font-size: 10px; font-weight: bold;")
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
        # Ensure color pickers reflect current mode
        self._on_colormap_changed(self.colormap_box.currentText())

    def update_theme_styling(self):
        """Update theme styling for all color control components"""
        is_dark = ColorControlsUIStyles.should_apply_dark_color_style()
        
        for component_type, widget in self._styled_components:
            if component_type == 'button':
                # For color buttons, preserve background color but add enhanced styling
                current_bg = widget.styleSheet()
                if 'background:' in current_bg:
                    # Extract the background color
                    bg_color = current_bg.split('background:')[1].strip()
                    if is_dark:
                        enhanced_style = ColorControlsUIStyles.get_button_style()
                    else:
                        enhanced_style = ColorControlsUIStyles.get_button_style_light()
                    # Override background color in enhanced style
                    enhanced_style = enhanced_style.replace('background-color: #2e2e2e;' if is_dark else 'background-color: #f0f0f0;', f'background-color: {bg_color};')
                    widget.setStyleSheet(enhanced_style)
                else:
                    if is_dark:
                        widget.setStyleSheet(ColorControlsUIStyles.get_button_style())
                    else:
                        widget.setStyleSheet(ColorControlsUIStyles.get_button_style_light())
            elif component_type == 'combobox':
                if is_dark:
                    widget.setStyleSheet(ColorControlsUIStyles.get_combobox_style())
                else:
                    widget.setStyleSheet("")  # Clear styling for light theme

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

    def _on_colormap_changed(self, value: str):
        is_custom = value == "Custom"
        is_value_colors = value == VALUE_COLORMAP_OPTION
        tooltip_map = {
            'custom': "Pick the gradient control color for this stop.",
            'value_colors': "Colors are generated automatically for each unique value.",
            'other': "Switch to Custom to edit gradient colors manually."
        }
        tooltip_key = 'custom' if is_custom else ('value_colors' if is_value_colors else 'other')
        tooltip = tooltip_map[tooltip_key]
        for btn in (self.color_start_btn, self.color_mid_btn, self.color_end_btn):
            btn.setEnabled(is_custom)
            btn.setToolTip(tooltip)

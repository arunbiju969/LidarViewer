from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout, QComboBox, QPushButton, QColorDialog, QHBoxLayout, QCheckBox
)
from PySide6.QtCore import Qt
from .layer_manager_widget import LayerManagerWidget
from theme.theme_manager import UnifiedThemeManager


class SidebarUIStyles:
    """Theme-aware styling for sidebar components"""
    
    @staticmethod
    def get_button_style():
        """Enhanced button styling for both light and dark themes"""
        return """
            QPushButton {
                background-color: #2e2e2e;
                border: 2px solid #3daee9;
                border-radius: 6px;
                padding: 8px 12px;
                color: white;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #5cbef0;
            }
            QPushButton:pressed {
                background-color: #252525;
                border-color: #2a9dd4;
            }
            QPushButton:disabled {
                background-color: #1a1a1a;
                border-color: #444;
                color: #666;
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
                padding: 8px 12px;
                color: #333;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #5cbef0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
                border-color: #2a9dd4;
            }
            QPushButton:disabled {
                background-color: #f8f8f8;
                border-color: #ccc;
                color: #999;
            }
        """
    
    @staticmethod
    def get_groupbox_style():
        """Custom group box styling to match main background"""
        return """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3daee9;
                border-radius: 8px;
                margin: 6px 0px;
                padding-top: 8px;
                background-color: #181a1b;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: #181a1b;
                color: white;
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
    def get_sidebar_style():
        """Main sidebar container styling"""
        return """
            #sidebar { 
                min-width: 260px; 
                max-width: 260px; 
                width: 260px; 
                border: 2px solid #3daee9; 
                border-radius: 8px; 
                background: #181a1b;
            }
        """
    
    @staticmethod
    def get_label_style():
        """Label styling for dark theme"""
        return """
            QLabel {
                color: white;
            }
        """
    
    @staticmethod
    def should_apply_dark_sidebar_style():
        """Check if we should apply dark theme sidebar styling"""
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
            print(f"[DEBUG] Sidebar: Theme detection failed: {e}")
        
        # Default to not applying dark styling if we can't determine theme
        return False


class SidebarWidget(QWidget):
    def get_sidebar_settings(self):
        color_controls = self.color_controls
        point_size_controls = self.point_size_controls
        return {
            'dimension': color_controls.dimension_box.currentText(),
            'colormap': color_controls.colormap_box.currentText(),
            'color_start': getattr(color_controls, 'color_start', None),
            'color_mid': getattr(color_controls, 'color_mid', None),
            'color_end': getattr(color_controls, 'color_end', None),
            'point_size': point_size_controls.get_point_size() if hasattr(point_size_controls, 'get_point_size') else None,
            'performance_mode': self.performance_box.currentText(),
            'lod_enabled': self.lod_enabled_checkbox.isChecked(),
            'lod_level': self.lod_level_box.currentText(),
        }

    def set_sidebar_settings(self, settings):
        color_controls = self.color_controls
        point_size_controls = self.point_size_controls
        widgets = [
            color_controls.dimension_box,
            color_controls.colormap_box,
            getattr(point_size_controls, 'slider', None),
            self.performance_box,
            self.lod_enabled_checkbox,
            self.lod_level_box,
        ]
        for w in widgets:
            if w is not None:
                w.blockSignals(True)
        try:
            if 'dimension' in settings:
                idx = color_controls.dimension_box.findText(settings['dimension'])
                if idx != -1:
                    color_controls.dimension_box.setCurrentIndex(idx)
            if 'colormap' in settings:
                idx = color_controls.colormap_box.findText(settings['colormap'])
                if idx != -1:
                    color_controls.colormap_box.setCurrentIndex(idx)
            if 'color_start' in settings and hasattr(color_controls, 'color_start'):
                color_controls.color_start = settings['color_start']
            if 'color_mid' in settings and hasattr(color_controls, 'color_mid'):
                color_controls.color_mid = settings['color_mid']
            if 'color_end' in settings and hasattr(color_controls, 'color_end'):
                color_controls.color_end = settings['color_end']
            if 'point_size' in settings and hasattr(point_size_controls, 'set_point_size'):
                point_size_controls.set_point_size(settings['point_size'])
            if 'performance_mode' in settings:
                idx = self.performance_box.findText(settings['performance_mode'])
                if idx != -1:
                    self.performance_box.setCurrentIndex(idx)
            if 'lod_enabled' in settings:
                self.lod_enabled_checkbox.setChecked(settings['lod_enabled'])
            if 'lod_level' in settings:
                idx = self.lod_level_box.findText(settings['lod_level'])
                if idx != -1:
                    self.lod_level_box.setCurrentIndex(idx)
        finally:
            for w in widgets:
                if w is not None:
                    w.blockSignals(False)
    def set_status(self, text):
        print(f"[DEBUG] set_status called with text: {text}")
        self.status_label.setText(text)
    
    def update_lod_status(self, lod_info):
        """Update LOD status label with current performance information"""
        if not lod_info:
            self.lod_status_label.setText("LOD: Ready")
            return
        
        level = lod_info.get('level', 'unknown')
        final_count = lod_info.get('final_count', 0)
        reduction = lod_info.get('reduction_percent', 0)
        
        if reduction > 0:
            status_text = f"LOD: {level.title()} ({final_count:,}pts, -{reduction:.0f}%)"
        else:
            status_text = f"LOD: {level.title()} ({final_count:,}pts)"
        
        self.lod_status_label.setText(status_text)
        print(f"[DEBUG] Updated LOD status: {status_text}")

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
        
        # Initialize components first
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
        
        # Store references to styled components for theme updates
        self._styled_components = []
        
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
        
        # Performance mode dropdown
        self.performance_box = QComboBox()
        self.performance_box.addItems(["Auto", "Performance", "Quality"])
        self.performance_box.setCurrentIndex(0)  # Default to "Auto"
        
        # LOD (Level-of-Detail) controls
        self.lod_enabled_checkbox = QCheckBox("Enable LOD System")
        self.lod_enabled_checkbox.setChecked(True)  # Default enabled
        self.lod_enabled_checkbox.setToolTip("Enable Level-of-Detail system for better performance with large datasets")
        
        self.lod_level_box = QComboBox()
        self.lod_level_box.addItems(["Auto", "Close", "Near", "Medium", "Far"])
        self.lod_level_box.setCurrentIndex(0)  # Default to "Auto"
        self.lod_level_box.setToolTip("Override automatic LOD level (for testing/manual control)")
        
        # LOD status label
        self.lod_status_label = QLabel("LOD: Ready")
        self.lod_status_label.setStyleSheet("color: #666; font-size: 10px;")
        self.lod_status_label.setToolTip("Current LOD system status and performance info")
        
        # Store styled components for theme updates
        self._styled_components = [
            ('button', self.button),
            ('groupbox', self.info_group),
            ('combobox', self.projection_box),
            ('combobox', self.theme_box),
            ('combobox', self.performance_box),
            ('combobox', self.lod_level_box),
            ('checkbox', self.lod_enabled_checkbox),
            ('label', self.status_label),
            ('label', self.info_file),
            ('label', self.info_points),
            ('label', self.lod_status_label),
        ]
        
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
        bottom_layout.addWidget(QLabel("Performance:"))
        bottom_layout.addWidget(self.performance_box)
        
        # LOD controls
        bottom_layout.addWidget(QLabel("Level-of-Detail:"))
        bottom_layout.addWidget(self.lod_enabled_checkbox)
        bottom_layout.addWidget(QLabel("LOD Level:"))
        bottom_layout.addWidget(self.lod_level_box)
        bottom_layout.addWidget(self.lod_status_label)
        
        bottom_layout.addWidget(QLabel("Theme:"))
        bottom_layout.addWidget(self.theme_box)
        bottom_layout.addStretch(1)
        
        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)
        
        # Apply initial styling
        self._apply_initial_styling()
        
        print("[DEBUG] SidebarWidget __init__ complete")
    
    def _apply_initial_styling(self):
        """Apply initial styling using unified theme manager"""
        print("[DEBUG] SidebarWidget: Using unified theme manager for styling")
        # The unified theme manager handles all styling globally
        pass
    
    def update_theme_styling(self):
        """Update theme styling using unified theme manager"""
        print("[DEBUG] SidebarWidget: Theme styling handled by unified theme manager")
        # The unified theme manager handles all styling globally
        pass
    
    def connect_theme_signals(self):
        """Connect to theme change signals - called from main window after initialization"""
        try:
            # No need to connect since unified theme manager handles all styling
            print("[DEBUG] Sidebar: Using unified theme manager - no local theme signals needed")
        except Exception as e:
            print(f"[DEBUG] Sidebar: Failed to connect theme signals: {e}")

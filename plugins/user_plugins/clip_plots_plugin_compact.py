"""
Compact Clip Plots Plugin - Modular PolyClipData Integration
"""

import os
import sqlite3
import shapefile
import glob
import shutil
from PySide6.QtWidgets import *
from PySide6.QtCore import QProcess, Qt
from plugins.plugin_manager import BasePlugin, PluginInfo


class SettingsDB:
    """Handles all database operations for settings"""
    
    def __init__(self, plugin_dir):
        self.db_path = os.path.join(plugin_dir, 'clip_plots_settings.db')
        self._init_db()
    
    def _init_db(self):
        """Initialize the settings database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            )''')
    
    def save(self, key, value):
        """Save a setting"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    
    def load(self, key, default=''):
        """Load a setting"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            return row[0] if row else default


class ClipPlotsWidget(QWidget):
    """Compact main widget for Clip Plots functionality"""
    
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.process = None
        self._pending_rename = None
        
        # Initialize settings database
        plugin_dir = os.path.dirname(os.path.dirname(__file__))
        self.db = SettingsDB(plugin_dir)
        
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialize compact UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)  # Reduced margins
        layout.setSpacing(6)  # Reduced vertical spacing between sections
        
        # Set minimum width for the widget to ensure proper display
        self.setMinimumWidth(320)  # Reduced from 400 to 320
        
        # Header
        header_widget = self._create_header()
        layout.addWidget(header_widget)
        
        # Configuration section
        config_section = self._create_section("Configuration", [
            self._create_field("Executable", "exe", "PolyClipData.exe", self._browse_exe),
            self._create_field("Shapefile", "shapefile", "Polygon file (.shp)", self._browse_shapefile)
        ])
        layout.addWidget(config_section)
        
        # Options section
        options_section = self._create_section("Options", [
            self._create_multifile_option(),
            self._create_field_selection()
        ])
        layout.addWidget(options_section)
        
        # Input/Output section
        io_section = self._create_section("Input/Output", [
            self._create_las_input(),
            self._create_field("Output Prefix", "prefix", "clipped"),
            self._create_field("Output Folder", "output", "Select directory", self._browse_output)
        ])
        layout.addWidget(io_section)
        
        # Action button
        run_btn = QPushButton('Run PolyClipData')
        # Styling handled by unified theme manager
        run_btn.setMinimumHeight(24)  # Reduced from 32 to 24
        run_btn.clicked.connect(self._run_process)
        layout.addWidget(run_btn)
        
        # Log section
        self.log_section = QGroupBox("Process Output")
        
        log_layout = QVBoxLayout(self.log_section)
        log_layout.setContentsMargins(8, 10, 8, 8)  # Reduced margins
        
        self.log = QTextEdit()
        self.log.setMaximumHeight(80)  # Reduced from 100 to 80
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Process output will appear here...")
        log_layout.addWidget(self.log)
        layout.addWidget(self.log_section)
        
        layout.addStretch()
    
    def _create_header(self):
        """Create simple header"""
        frame = QFrame()
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("PolyClip")
        title.setStyleSheet("font-size: 12px; font-weight: bold;")  # Reduced from 14px
        
        subtitle = QLabel("LiDAR Clipping Tool")
        subtitle.setStyleSheet("font-size: 9px;")  # Reduced from 10px
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self._close_plugin)
        layout.addWidget(close_btn)
        
        return frame
    
    def _create_section(self, title, widgets):
        """Create a section"""
        section = QGroupBox(title)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(10, 12, 10, 8)  # Reduced margins
        layout.setSpacing(6)  # Reduced spacing between items
        
        for widget in widgets:
            if widget:
                layout.addWidget(widget)
        
        return section
    
    def _create_field(self, label, key, placeholder, browse_func=None):
        """Create a simple input field"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # Reduced space between label and input
        
        # Label
        label_widget = QLabel(label)
        layout.addWidget(label_widget)
        
        # Input row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)  # Reduced space between input and button
        
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setMinimumHeight(22)  # Reduced from 28 to 22
        field.textChanged.connect(lambda text: self.db.save(key, text))
        setattr(self, f"{key}_field", field)
        input_layout.addWidget(field)
        
        if browse_func:
            btn = QPushButton('Browse...')
            btn.setMinimumWidth(70)  # Reduced from 85 to 70
            btn.setMinimumHeight(22)  # Reduced to match input field height
            btn.clicked.connect(browse_func)
            input_layout.addWidget(btn)
        
        layout.addLayout(input_layout)
        return frame
    
    def _create_multifile_option(self):
        """Create multifile checkbox"""
        self.multifile_check = QCheckBox('Save as multiple files (one per polygon)')
        self.multifile_check.setChecked(True)
        self.multifile_check.stateChanged.connect(self._on_multifile_changed)
        return self.multifile_check
    
    def _create_field_selection(self):
        """Create field selection dropdown"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # Reduced space between label and dropdown
        
        label = QLabel("Field for Output Naming")
        layout.addWidget(label)
        
        self.field_combo = QComboBox()
        self.field_combo.setMinimumHeight(22)  # Reduced to match other inputs
        self.field_combo.setEnabled(False)
        layout.addWidget(self.field_combo)
        
        return frame
    
    def _create_las_input(self):
        """Create LAS input with current layer button"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # Reduced space between elements
        
        label = QLabel("LAS Input File")
        layout.addWidget(label)
        
        # Input row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)  # Reduced space between input and button
        
        self.las_field = QLineEdit()
        self.las_field.setPlaceholderText("Select LAS/LAZ file...")
        self.las_field.setMinimumHeight(22)  # Reduced to match other inputs
        self.las_field.textChanged.connect(lambda text: self.db.save('las', text))
        input_layout.addWidget(self.las_field)
        
        browse_btn = QPushButton('Browse...')
        browse_btn.setMinimumWidth(70)  # Reduced to match other browse buttons
        browse_btn.setMinimumHeight(22)  # Reduced to match input field height
        browse_btn.clicked.connect(self._browse_las)
        input_layout.addWidget(browse_btn)
        
        layout.addLayout(input_layout)
        
        # Current layer button
        current_btn = QPushButton('Use Current Layer')
        current_btn.setMinimumHeight(24)  # Reduced from 32 to 24
        current_btn.clicked.connect(self._use_current_layer)
        layout.addWidget(current_btn)
        
        return frame
    
    def _close_plugin(self):
        """Close the plugin widget"""
        if hasattr(self.plugin, 'dock_widget') and self.plugin.dock_widget:
            self.plugin.dock_widget.hide()
    
    def _browse_exe(self):
        """Browse for executable"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select PolyClipData.exe', '', 'Executables (*.exe)')
        if path:
            self.exe_field.setText(path)
    
    def _browse_shapefile(self):
        """Browse for shapefile"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select Shapefile', '', 'Shapefiles (*.shp)')
        if path:
            self.shapefile_field.setText(path)
            self._load_shapefile_fields(path)
    
    def _browse_las(self):
        """Browse for LAS file"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select LAS File', '', 'LAS Files (*.las *.laz)')
        if path:
            self.las_field.setText(path)
    
    def _browse_output(self):
        """Browse for output folder"""
        path = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if path:
            self.output_field.setText(path)
    
    def _use_current_layer(self):
        """Use current layer from viewer"""
        current_layer = self.plugin.api.get_current_layer()
        if not current_layer:
            QMessageBox.warning(self, 'No Layer', 'No layer is currently selected.')
            return
        
        file_path = current_layer.get('file_path', '')
        if file_path and os.path.exists(file_path):
            self.las_field.setText(file_path)
            self.plugin.api.update_status(f'Using current layer: {os.path.basename(file_path)}')
        else:
            QMessageBox.warning(self, 'No File', 'Current layer has no associated LAS file.')
    
    def _load_shapefile_fields(self, path):
        """Load fields from shapefile"""
        try:
            sf = shapefile.Reader(path)
            fields = [f[0] for f in sf.fields[1:]]  # skip DeletionFlag
            self.field_combo.clear()
            self.field_combo.addItems(fields)
            self.field_combo.setEnabled(True)
            self.log.append(f'[INFO] Loaded shapefile with {len(fields)} fields')
        except Exception as e:
            self.field_combo.clear()
            self.field_combo.setEnabled(False)
            self.log.append(f'[ERROR] Could not read shapefile: {e}')
    
    def _on_multifile_changed(self):
        """Handle multifile checkbox change"""
        self.field_combo.setEnabled(self.multifile_check.isChecked())
    
    def _load_settings(self):
        """Load saved settings"""
        self.exe_field.setText(self.db.load('exe'))
        self.shapefile_field.setText(self.db.load('shapefile'))
        self.las_field.setText(self.db.load('las'))
        self.prefix_field.setText(self.db.load('prefix', 'clipped'))
        self.output_field.setText(self.db.load('output'))
        
        # Load shapefile fields if available
        shp_path = self.shapefile_field.text()
        if shp_path and os.path.isfile(shp_path):
            self._load_shapefile_fields(shp_path)
    
    def _run_process(self):
        """Run PolyClipData process"""
        # Validate inputs
        exe = self.exe_field.text().strip()
        shp = self.shapefile_field.text().strip()
        las_file = self.las_field.text().strip()
        out_dir = self.output_field.text().strip()
        prefix = self.prefix_field.text().strip() or 'clipped'
        
        if not all([exe, shp, las_file, out_dir]):
            QMessageBox.warning(self, 'Missing Info', 'Please fill all required fields.')
            return
        
        if not os.path.isfile(las_file):
            QMessageBox.warning(self, 'Invalid File', 'LAS file does not exist.')
            return
        
        # Build command
        multifile = self.multifile_check.isChecked()
        if multifile:
            field_idx = self.field_combo.currentIndex() + 1
            if field_idx < 1:
                QMessageBox.warning(self, 'Missing Field', 'Please select a field for multifile output.')
                return
            
            out_base = os.path.join(out_dir, prefix)
            cmd = [exe, '/verbose', '/multifile', f'/shape:{field_idx},*', shp, out_base, las_file]
            
            # Prepare for renaming
            try:
                sf = shapefile.Reader(shp)
                field_name = self.field_combo.currentText()
                field_values = [str(rec[sf.fields[1:].index([f for f in sf.fields[1:] if f[0]==field_name][0])]) for rec in sf.records()]
                self._pending_rename = (out_base, field_values, prefix)
            except Exception as e:
                QMessageBox.warning(self, 'Field Error', f'Could not read field values: {e}')
                return
        else:
            out_file = os.path.join(out_dir, f'{prefix}_{os.path.basename(las_file)}')
            cmd = [exe, '/verbose', shp, out_file, las_file]
            self._pending_rename = None
        
        # Execute
        self.log.clear()
        self.log.append(f'[INFO] Running: {" ".join(cmd)}')
        
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_output)
        self.process.finished.connect(self._on_finished)
        self.process.start(cmd[0], cmd[1:])
    
    def _on_output(self):
        """Handle process output"""
        if self.process:
            data = self.process.readAllStandardOutput().data().decode(errors='replace')
            if data:
                self.log.append(data)
    
    def _on_finished(self, exit_code, exit_status):
        """Handle process completion"""
        if exit_code == 0:
            # Handle file renaming for multifile output
            if self._pending_rename:
                out_base, field_values, prefix = self._pending_rename
                las_files = sorted(glob.glob(os.path.join(os.path.dirname(out_base), os.path.basename(out_base) + '*')))
                
                for src, val in zip(las_files, field_values):
                    ext = os.path.splitext(src)[1]
                    dst = os.path.join(os.path.dirname(src), f'{prefix}_{val}{ext}')
                    try:
                        shutil.move(src, dst)
                        self.log.append(f'[INFO] Renamed: {os.path.basename(src)} -> {os.path.basename(dst)}')
                    except Exception as e:
                        self.log.append(f'[WARN] Rename failed: {e}')
            
            self.log.append('[SUCCESS] Process completed!')
            QMessageBox.information(self, 'Success', 'PolyClipData completed successfully!')
        else:
            self.log.append(f'[ERROR] Process failed with exit code {exit_code}')
            QMessageBox.warning(self, 'Error', f'Process failed with exit code {exit_code}')


class ClipPlotsPlugin(BasePlugin):
    """Compact Clip Plots Plugin"""
    
    def __init__(self, api):
        super().__init__(api)
        self.widget = None
        self.dock_widget = None
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="Clip Plots",
            version="2.0.0",
            author="LiDAR Viewer",
            description="Compact PolyClipData integration for clipping LiDAR point clouds with shapefiles.",
            category="Tools"
        )
    
    def activate(self):
        """Activate plugin"""
        self.widget = ClipPlotsWidget(self)
        
        self.dock_widget = self.add_dock_widget(
            "Clip Plots", 
            self.widget, 
            Qt.RightDockWidgetArea,
            visible=False
        )
        
        if self.dock_widget:
            from PySide6.QtWidgets import QDockWidget, QWidget
            self.dock_widget.setFeatures(
                QDockWidget.DockWidgetFeature.DockWidgetClosable | 
                QDockWidget.DockWidgetFeature.DockWidgetMovable
            )
            
            # Remove title bar by setting custom empty title widget
            empty_title = QWidget()
            empty_title.setFixedHeight(0)
            self.dock_widget.setTitleBarWidget(empty_title)
        
        self.add_menu_item("Tools", "Clip Plots", self.show_dock_widget)
        print("[INFO] Compact Clip Plots plugin activated")
    
    def show_dock_widget(self):
        """Show dock widget using BasePlugin's replacement logic"""
        return super().show_dock_widget()
    
    def deactivate(self):
        """Deactivate plugin"""
        super().deactivate()
        print("[INFO] Clip Plots plugin deactivated")

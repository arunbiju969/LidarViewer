"""
GridMetrics Plugin for LiDAR Viewer

This plugin provides batch processing of LAS files using FUSION's GridMetrics tool
to generate grid-based forest metrics including mean height, cover, and percentiles.
"""

import os
import sys
import subprocess
import sqlite3
import glob
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QThread, Signal

from plugins.plugin_manager import BasePlugin, PluginInfo


class SettingsDB:
    """Handles all database operations for settings"""
    
    def __init__(self, plugin_dir):
        self.db_path = os.path.join(plugin_dir, 'gridmetrics_settings.db')
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


class GridMetricsWorker(QThread):
    """Worker thread for GridMetrics batch processing"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal()

    def __init__(self, las_files, normalized_dir, gridmetrics_exe, output_dir, ground_model, height_break, cell_size):
        super().__init__()
        self.las_files = las_files
        self.normalized_dir = normalized_dir
        self.gridmetrics_exe = gridmetrics_exe
        self.output_dir = output_dir
        self.ground_model = ground_model
        self.height_break = height_break
        self.cell_size = cell_size
        self._is_running = True

    def run(self):
        total = len(self.las_files)
        for idx, las_file in enumerate(self.las_files):
            if not self._is_running:
                break
            
            stand_file_full_name = os.path.join(self.normalized_dir, las_file)
            stand_file_no_ext = os.path.splitext(las_file)[0]
            output_base_name = os.path.join(self.output_dir, f'{stand_file_no_ext}_gridmetrics')
            
            rel_gridmetrics_exe = os.path.relpath(self.gridmetrics_exe, start=os.getcwd())
            if not os.path.dirname(rel_gridmetrics_exe):
                rel_gridmetrics_exe = f'.\\{rel_gridmetrics_exe}'
            
            rel_output_base_name = os.path.relpath(output_base_name, start=os.getcwd())
            rel_stand_file_full_name = os.path.relpath(stand_file_full_name, start=os.getcwd())
            
            cmd_str = (
                f'& "{rel_gridmetrics_exe}" /raster:mean,cover,p90 /ascii /minht:{self.height_break} /verbose {self.ground_model} {self.height_break} {self.cell_size} '
                f'"{rel_output_base_name}" "{rel_stand_file_full_name}"'
            )
            
            self.log_signal.emit(f'Running GridMetrics for: {las_file}')
            self.log_signal.emit(f'Command: {cmd_str}')
            
            try:
                result = subprocess.run([
                    'powershell',
                    '-Command',
                    cmd_str
                ], shell=True, capture_output=True, text=True)
                
                self.log_signal.emit(f'STDOUT: {result.stdout[:500]}')
                if result.stderr:
                    self.log_signal.emit(f'STDERR: {result.stderr}')
                self.log_signal.emit(f'Return code: {result.returncode}')
                
                if result.returncode != 0:
                    self.log_signal.emit(f'[ERROR] GridMetrics failed for {os.path.basename(las_file)} with error code {result.returncode}.')
                else:
                    self.log_signal.emit(f'[SUCCESS] GridMetrics completed for {os.path.basename(las_file)}.')
            except Exception as e:
                self.log_signal.emit(f'[ERROR] Exception processing {os.path.basename(las_file)}: {str(e)}')
            
            self.progress_signal.emit(idx + 1, total)
        
        self.finished_signal.emit()

    def stop(self):
        self._is_running = False


class GridMetricsWidget(QWidget):
    """Compact main widget for GridMetrics functionality"""
    
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.worker = None
        
        # Initialize settings database
        plugin_dir = os.path.dirname(os.path.dirname(__file__))
        self.db = SettingsDB(plugin_dir)
        
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialize compact UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)
        
        # Set minimum width
        self.setMinimumWidth(320)
        
        # Header
        header_widget = self._create_header()
        layout.addWidget(header_widget)
        
        # Configuration section
        config_section = self._create_section("Configuration", [
            self._create_field("GridMetrics.exe", "exe", "GridMetrics.exe", self._browse_exe),
            self._create_field("Input LAS Folder", "input", "Normalized LAS folder", self._browse_input),
            self._create_field("Output Folder", "output", "Output directory", self._browse_output)
        ])
        layout.addWidget(config_section)
        
        # Parameters section
        params_section = self._create_section("Parameters", [
            self._create_param_fields()
        ])
        layout.addWidget(params_section)
        
        # File List section
        files_section = self._create_files_section()
        layout.addWidget(files_section)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        scan_btn = QPushButton('Scan LAS Files')
        scan_btn.setMinimumHeight(24)
        scan_btn.clicked.connect(self._scan_files)
        buttons_layout.addWidget(scan_btn)
        
        current_btn = QPushButton('Use Current Layer')
        current_btn.setMinimumHeight(24)
        current_btn.clicked.connect(self._use_current_layer)
        buttons_layout.addWidget(current_btn)
        layout.addLayout(buttons_layout)
        
        self.run_btn = QPushButton('Run GridMetrics Batch')
        self.run_btn.setMinimumHeight(28)
        self.run_btn.clicked.connect(self._run_process)
        layout.addWidget(self.run_btn)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setMinimumHeight(20)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Log section
        self.log_section = QGroupBox("Process Output")
        log_layout = QVBoxLayout(self.log_section)
        log_layout.setContentsMargins(8, 10, 8, 8)
        
        self.log = QTextEdit()
        self.log.setMaximumHeight(100)
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Process output will appear here...")
        log_layout.addWidget(self.log)
        layout.addWidget(self.log_section)
        
        layout.addStretch()
    
    def _create_header(self):
        """Create header with close button"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("GridMetrics")
        title.setStyleSheet("font-size: 12px; font-weight: bold;")
        
        subtitle = QLabel("Batch Forest Metrics Processing")
        subtitle.setStyleSheet("font-size: 9px;")
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self._close_plugin)
        layout.addWidget(close_btn)
        
        return frame
    
    def _create_section(self, title, widgets):
        """Create a section"""
        section = QGroupBox(title)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(10, 12, 10, 8)
        layout.setSpacing(6)
        
        for widget in widgets:
            if widget:
                layout.addWidget(widget)
        
        return section
    
    def _create_field(self, label, key, placeholder, browse_func=None):
        """Create a field with browse button"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Label
        label_widget = QLabel(label)
        layout.addWidget(label_widget)
        
        # Input row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setMinimumHeight(22)
        field.textChanged.connect(lambda text: self.db.save(key, text))
        setattr(self, f"{key}_field", field)
        input_layout.addWidget(field)
        
        if browse_func:
            btn = QPushButton('Browse...')
            btn.setMinimumWidth(70)
            btn.setMinimumHeight(22)
            btn.clicked.connect(browse_func)
            input_layout.addWidget(btn)
        
        layout.addLayout(input_layout)
        return frame
    
    def _create_param_fields(self):
        """Create parameter input fields"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Cell Size
        cell_layout = QVBoxLayout()
        cell_layout.addWidget(QLabel("Cell Size"))
        self.cell_size_field = QLineEdit("15.0")
        self.cell_size_field.setMinimumHeight(22)
        self.cell_size_field.textChanged.connect(lambda text: self.db.save('cell_size', text))
        cell_layout.addWidget(self.cell_size_field)
        layout.addLayout(cell_layout)
        
        # Height Break
        height_layout = QVBoxLayout()
        height_layout.addWidget(QLabel("Height Break"))
        self.height_break_field = QLineEdit("0.0")
        self.height_break_field.setMinimumHeight(22)
        self.height_break_field.textChanged.connect(lambda text: self.db.save('height_break', text))
        height_layout.addWidget(self.height_break_field)
        layout.addLayout(height_layout)
        
        return frame
    
    def _create_files_section(self):
        """Create file list section"""
        section = QGroupBox("LAS Files to Process")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(10, 12, 10, 8)
        
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(80)
        layout.addWidget(self.file_list)
        
        info_label = QLabel("Found files will appear here")
        info_label.setStyleSheet("font-size: 9px; color: #666;")
        layout.addWidget(info_label)
        
        return section
    
    def _close_plugin(self):
        """Close the plugin widget"""
        if hasattr(self.plugin, 'dock_widget') and self.plugin.dock_widget:
            self.plugin.dock_widget.hide()
    
    def _browse_exe(self):
        """Browse for GridMetrics.exe"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select GridMetrics.exe', '', 'Executables (*.exe)')
        if path:
            self.exe_field.setText(path)
    
    def _browse_input(self):
        """Browse for input folder"""
        path = QFileDialog.getExistingDirectory(self, 'Select Normalized LAS Folder')
        if path:
            self.input_field.setText(path)
    
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
            # Set input folder to the directory containing the current file
            input_dir = os.path.dirname(file_path)
            self.input_field.setText(input_dir)
            self.plugin.api.update_status(f'Using directory of current layer: {os.path.basename(input_dir)}')
            # Auto-scan for files in that directory
            self._scan_files()
        else:
            QMessageBox.warning(self, 'No File', 'Current layer has no associated LAS file.')
    
    def _scan_files(self):
        """Scan for LAS files in input directory"""
        folder = self.input_field.text().strip()
        if not os.path.isdir(folder):
            QMessageBox.warning(self, 'Invalid Folder', 'Please select a valid input folder.')
            return
        
        las_files = glob.glob(os.path.join(folder, '*.las')) + glob.glob(os.path.join(folder, '*.laz'))
        self.file_list.clear()
        
        for f in las_files:
            item = QListWidgetItem(os.path.basename(f))
            item.setData(Qt.UserRole, f)  # Store full path
            self.file_list.addItem(item)
        
        self.log.append(f'[INFO] Found {len(las_files)} LAS/LAZ files.')
    
    def _load_settings(self):
        """Load saved settings"""
        self.exe_field.setText(self.db.load('exe'))
        self.input_field.setText(self.db.load('input'))
        self.output_field.setText(self.db.load('output'))
        self.cell_size_field.setText(self.db.load('cell_size', '15.0'))
        self.height_break_field.setText(self.db.load('height_break', '0.0'))
    
    def _run_process(self):
        """Run GridMetrics batch processing"""
        # Validate inputs
        exe = self.exe_field.text().strip()
        input_dir = self.input_field.text().strip()
        output_dir = self.output_field.text().strip()
        
        if not all([exe, input_dir, output_dir]):
            QMessageBox.warning(self, 'Missing Info', 'Please fill all required fields.')
            return
        
        if not os.path.isfile(exe):
            # Try to find GridMetrics.exe automatically
            exe_candidates = [
                os.path.join(os.path.dirname(__file__), '..', '..', 'Fusion', 'GridMetrics.exe'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'Fusion', 'GridMetrics64.exe'),
            ]
            
            found_exe = None
            for candidate in exe_candidates:
                if os.path.isfile(candidate):
                    found_exe = candidate
                    break
            
            if found_exe:
                exe = found_exe
                self.exe_field.setText(exe)
            else:
                QMessageBox.warning(self, 'Invalid Executable', 'GridMetrics.exe not found.')
                return
        
        if not os.path.isdir(input_dir):
            QMessageBox.warning(self, 'Invalid Input', 'Input folder not found.')
            return
        
        if not os.path.isdir(output_dir):
            QMessageBox.warning(self, 'Invalid Output', 'Output folder not found.')
            return
        
        # Get files from list
        las_files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            las_files.append(os.path.basename(item.data(Qt.UserRole)))
        
        if not las_files:
            QMessageBox.warning(self, 'No Files', 'No LAS files to process. Click "Scan LAS Files" first.')
            return
        
        # Start processing
        ground_model = '*'
        height_break = self.height_break_field.text().strip() or '0.0'
        cell_size = self.cell_size_field.text().strip() or '15.0'
        
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.log.clear()
        self.log.append(f'[INFO] Starting GridMetrics batch processing for {len(las_files)} files...')
        
        self.worker = GridMetricsWorker(las_files, input_dir, exe, output_dir, ground_model, height_break, cell_size)
        self.worker.log_signal.connect(self.log.append)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()
    
    def _update_progress(self, done, total):
        """Update progress bar"""
        if total > 0:
            self.progress.setValue(int(100 * done / total))
    
    def _on_finished(self):
        """Handle processing completion"""
        self.run_btn.setEnabled(True)
        self.progress.setValue(100)
        self.log.append('[SUCCESS] All GridMetrics processing complete!')
        QMessageBox.information(self, 'Complete', 'GridMetrics batch processing completed!')


class GridMetricsPlugin(BasePlugin):
    def __init__(self, api):
        super().__init__(api)
        self._info = PluginInfo(
            name="GridMetrics",
            version="1.0.0",
            description="Batch process LAS files using FUSION GridMetrics to generate forest metrics",
            author="LiDAR Viewer Team",
            category="Tools"
        )
        self.dock_widget = None
        self.widget = None
    
    @property
    def info(self) -> PluginInfo:
        """Plugin metadata"""
        return self._info
    
    def activate(self):
        """Activate the plugin"""
        from PySide6.QtWidgets import QDockWidget
        from PySide6.QtCore import Qt
        
        # Create the widget with plugin reference
        self.widget = GridMetricsWidget(self)
        
        # Use BasePlugin's add_dock_widget method (hidden by default)
        self.dock_widget = self.add_dock_widget(
            "GridMetrics", 
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
            
            # Remove title bar for compact look
            empty_title = QWidget()
            empty_title.setFixedHeight(0)
            self.dock_widget.setTitleBarWidget(empty_title)
        
        # Add menu action
        self.add_menu_item("Tools", "GridMetrics", self.show_dock_widget)
        
        print(f"[INFO] {self.info.name} plugin activated")
        return True
    
    def show_dock_widget(self):
        """Show dock widget using BasePlugin's replacement logic"""
        return super().show_dock_widget()
    
    def deactivate(self):
        """Deactivate the plugin"""
        if self.widget and hasattr(self.widget, 'worker') and self.widget.worker:
            self.widget.worker.stop()
        super().deactivate()
        print(f"[INFO] {self.info.name} plugin deactivated")

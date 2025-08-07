"""
Process All Stand Grid Plugin for LiDAR Viewer

This plugin provides batch processing of all LAS files in a normalized directory
using FUSION's GridMetrics tool with automated workflow capabilities.
"""

import os
import sys
import time
import glob
import sqlite3
import subprocess
from PySide6.QtWidgets import *
from PySide6.QtCore import QThread, Signal, Qt

from plugins.plugin_manager import BasePlugin, PluginInfo


class SettingsDB:
    """Handles all database operations for settings"""
    
    def __init__(self, plugin_dir):
        self.db_path = os.path.join(plugin_dir, 'process_all_stand_grid_settings.db')
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


class ProcessAllStandGridWorker(QThread):
    """Worker thread for batch GridMetrics processing"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal()

    def __init__(self, normalized_dir, cell_size, height_break, ground_model):
        super().__init__()
        self.normalized_dir = normalized_dir
        self.cell_size = cell_size
        self.height_break = height_break
        self.ground_model = ground_model
        self._is_running = True

    def run(self):
        try:
            # Set up paths
            gridmetrics_dir = os.path.join(self.normalized_dir, 'gridmetrics')
            os.makedirs(gridmetrics_dir, exist_ok=True)
            
            # Find GridMetrics executable
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            gridmetrics_exe = os.path.join(base_dir, 'Fusion', 'GridMetrics.exe')
            
            if not os.path.isfile(gridmetrics_exe):
                # Try 64-bit version
                gridmetrics_exe = os.path.join(base_dir, 'Fusion', 'GridMetrics64.exe')
                
            if not os.path.isfile(gridmetrics_exe):
                self.log_signal.emit('[ERROR] GridMetrics.exe not found in Fusion folder.')
                self.finished_signal.emit()
                return
            
            # Find LAS files
            las_files = [f for f in os.listdir(self.normalized_dir) if f.lower().endswith('.las')]
            if not las_files:
                self.log_signal.emit('[ERROR] No LAS files found in normalized directory.')
                self.finished_signal.emit()
                return
            
            self.log_signal.emit(f'[INFO] Found {len(las_files)} LAS files to process')
            self.log_signal.emit(f'[INFO] GridMetrics executable: {gridmetrics_exe}')
            self.log_signal.emit(f'[INFO] Output directory: {gridmetrics_dir}')
            
            total = len(las_files)
            processed_count = 0
            
            for idx, las_file in enumerate(las_files):
                if not self._is_running:
                    break
                
                # Add small delay between files
                time.sleep(1)
                
                stand_file_full_name = os.path.join(self.normalized_dir, las_file)
                stand_file_no_ext = os.path.splitext(las_file)[0]
                output_base_name = os.path.join(gridmetrics_dir, f'{stand_file_no_ext}_gridmetrics')
                
                # Use relative paths for all files
                rel_gridmetrics_exe = os.path.relpath(gridmetrics_exe, start=os.getcwd())
                if not os.path.dirname(rel_gridmetrics_exe):
                    rel_gridmetrics_exe = f'.\\{rel_gridmetrics_exe}'
                
                rel_output_base_name = os.path.relpath(output_base_name, start=os.getcwd())
                rel_stand_file_full_name = os.path.relpath(stand_file_full_name, start=os.getcwd())
                
                cmd_str = (
                    f'& "{rel_gridmetrics_exe}" /raster:mean,cover,p90 /ascii /minht:{self.height_break} /verbose {self.ground_model} {self.height_break} {self.cell_size} '
                    f'"{rel_output_base_name}" "{rel_stand_file_full_name}"'
                )
                
                self.log_signal.emit(f'[INFO] Processing: {las_file}')
                
                result = subprocess.run([
                    'powershell',
                    '-Command',
                    cmd_str
                ], shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    processed_count += 1
                    self.log_signal.emit(f'[SUCCESS] GridMetrics completed for {las_file}')
                else:
                    self.log_signal.emit(f'[ERROR] GridMetrics failed for {las_file} (code: {result.returncode})')
                
                # Update progress
                self.progress_signal.emit(idx + 1, total)
            
            self.log_signal.emit(f'[SUCCESS] Batch processing complete. {processed_count}/{total} files processed successfully.')
            self.finished_signal.emit()
            
        except Exception as e:
            self.log_signal.emit(f'[ERROR] Processing failed: {str(e)}')
            self.finished_signal.emit()

    def stop(self):
        self._is_running = False


class ProcessAllStandGridWidget(QWidget):
    """Compact main widget for Process All Stand Grid functionality"""
    
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.worker = None
        
        # Initialize settings database
        plugin_dir = os.path.dirname(os.path.dirname(__file__))
        self.db = SettingsDB(plugin_dir)
        
        self._init_ui()
        self._load_settings()
        self._detect_gridmetrics_exe()
    
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
            self._create_field("Normalized LAS Folder", "normalized_dir", "Folder with normalized LAS files", self._browse_dir)
        ])
        layout.addWidget(config_section)
        
        # Parameters section
        params_section = self._create_params_section()
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
        
        # Process buttons
        process_layout = QHBoxLayout()
        self.run_btn = QPushButton('Process All Files')
        self.run_btn.setMinimumHeight(28)
        self.run_btn.clicked.connect(self._run_process)
        process_layout.addWidget(self.run_btn)
        
        self.stop_btn = QPushButton('Stop')
        self.stop_btn.setMinimumHeight(28)
        self.stop_btn.clicked.connect(self._stop_process)
        self.stop_btn.setEnabled(False)
        process_layout.addWidget(self.stop_btn)
        layout.addLayout(process_layout)
        
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
        self.log.setMaximumHeight(120)
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
        
        title = QLabel("Process All Stand Grid")
        title.setStyleSheet("font-size: 12px; font-weight: bold;")
        
        subtitle = QLabel("Batch GridMetrics processing for all LAS files")
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
    
    def _create_params_section(self):
        """Create parameters section"""
        section = QGroupBox("GridMetrics Parameters")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(10, 12, 10, 8)
        layout.setSpacing(8)
        
        # Cell Size
        cell_layout = QHBoxLayout()
        cell_layout.addWidget(QLabel("Cell Size (m):"))
        self.cell_size_field = QDoubleSpinBox()
        self.cell_size_field.setRange(0.1, 100.0)
        self.cell_size_field.setDecimals(1)
        self.cell_size_field.setValue(15.0)
        self.cell_size_field.setMinimumHeight(22)
        self.cell_size_field.valueChanged.connect(lambda v: self.db.save('cell_size', str(v)))
        cell_layout.addWidget(self.cell_size_field)
        cell_layout.addStretch()
        layout.addLayout(cell_layout)
        
        # Height Break
        height_layout = QHBoxLayout()
        height_layout.addWidget(QLabel("Height Break (m):"))
        self.height_break_field = QDoubleSpinBox()
        self.height_break_field.setRange(0.0, 10.0)
        self.height_break_field.setDecimals(1)
        self.height_break_field.setValue(0.0)
        self.height_break_field.setMinimumHeight(22)
        self.height_break_field.valueChanged.connect(lambda v: self.db.save('height_break', str(v)))
        height_layout.addWidget(self.height_break_field)
        height_layout.addStretch()
        layout.addLayout(height_layout)
        
        return section
    
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
    
    def _browse_dir(self):
        """Browse for normalized LAS directory"""
        path = QFileDialog.getExistingDirectory(self, 'Select Normalized LAS Directory')
        if path:
            self.normalized_dir_field.setText(path)
    
    def _detect_gridmetrics_exe(self):
        """Auto-detect GridMetrics executable in workspace"""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        fusion_dir = os.path.join(base_dir, 'Fusion')
        
        if os.path.exists(fusion_dir):
            gridmetrics_path = os.path.join(fusion_dir, 'GridMetrics.exe')
            if not os.path.exists(gridmetrics_path):
                gridmetrics_path = os.path.join(fusion_dir, 'GridMetrics64.exe')
            
            if os.path.exists(gridmetrics_path):
                self.log.append(f"[INFO] Auto-detected GridMetrics: {gridmetrics_path}")
    
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
            self.normalized_dir_field.setText(input_dir)
            self.plugin.api.update_status(f'Using directory of current layer: {os.path.basename(input_dir)}')
            # Auto-scan for files in that directory
            self._scan_files()
        else:
            QMessageBox.warning(self, 'No File', 'Current layer has no associated LAS file.')
    
    def _scan_files(self):
        """Scan for LAS files in normalized directory"""
        folder = self.normalized_dir_field.text().strip()
        if not os.path.isdir(folder):
            QMessageBox.warning(self, 'Invalid Folder', 'Please select a valid normalized directory.')
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
        self.normalized_dir_field.setText(self.db.load('normalized_dir'))
        self.cell_size_field.setValue(float(self.db.load('cell_size', '15.0')))
        self.height_break_field.setValue(float(self.db.load('height_break', '0.0')))
    
    def _run_process(self):
        """Run batch processing"""
        # Validate inputs
        normalized_dir = self.normalized_dir_field.text().strip()
        
        if not normalized_dir or not os.path.isdir(normalized_dir):
            QMessageBox.warning(self, 'Invalid Directory', 'Please select a valid normalized LAS directory.')
            return
        
        # Get files from list
        las_files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            las_files.append(item.data(Qt.UserRole))
        
        if not las_files:
            QMessageBox.warning(self, 'No Files', 'No LAS files to process. Click "Scan LAS Files" first.')
            return
        
        # Get parameters
        cell_size = str(self.cell_size_field.value())
        height_break = str(self.height_break_field.value())
        ground_model = '*'  # Default ground model
        
        # Start processing
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.log.clear()
        self.log.append(f'[INFO] Starting batch processing for {len(las_files)} files...')
        self.log.append(f'[INFO] Parameters: Cell Size={cell_size}m, Height Break={height_break}m')
        
        self.worker = ProcessAllStandGridWorker(normalized_dir, cell_size, height_break, ground_model)
        self.worker.log_signal.connect(self.log.append)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()
    
    def _stop_process(self):
        """Stop processing"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.log.append('[INFO] Stop requested. Waiting for current file to complete...')
    
    def _update_progress(self, done, total):
        """Update progress bar"""
        if total > 0:
            self.progress.setValue(int(100 * done / total))
    
    def _on_finished(self):
        """Handle processing completion"""
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setValue(100)
        self.log.append('[SUCCESS] All batch processing complete!')
        QMessageBox.information(self, 'Complete', 'Batch GridMetrics processing completed!')


class ProcessAllStandGridPlugin(BasePlugin):
    """Process All Stand Grid Plugin"""
    
    def __init__(self, api):
        super().__init__(api)
        self.widget = None
        self.dock_widget = None
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="Process All Stand Grid",
            version="1.0.0",
            author="LiDAR Viewer",
            description="Batch process all LAS files using FUSION GridMetrics with automated workflow.",
            category="Tools"
        )
    
    def activate(self):
        """Activate plugin"""
        self.widget = ProcessAllStandGridWidget(self)
        
        self.dock_widget = self.add_dock_widget(
            "Process All Stand Grid", 
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
        
        self.add_menu_item("Tools", "Process All Stand Grid", self.show_dock_widget)
        print("[INFO] Process All Stand Grid plugin activated")
    
    def show_dock_widget(self):
        """Show dock widget using BasePlugin's replacement logic"""
        return super().show_dock_widget()
    
    def deactivate(self):
        """Deactivate plugin"""
        if self.widget and self.widget.worker and self.widget.worker.isRunning():
            self.widget.worker.stop()
            self.widget.worker.wait()
        super().deactivate()
        print("[INFO] Process All Stand Grid plugin deactivated")

"""
Normalize LAS Plugin for LiDAR Viewer

This plugin provides LAS normalization functionality using FUSION tools
to rename LAS files and normalize heights relative to ground DTM.
"""

import os
import sys
import re
import json
import sqlite3
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QFileDialog, QTextEdit, QListWidget, QMessageBox, QGroupBox, QFrame,
    QProgressBar, QScrollArea, QListWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from plugins.plugin_manager import BasePlugin, PluginInfo


class SettingsDB:
    """Handles all database operations for settings"""
    
    def __init__(self, plugin_dir):
        self.db_path = os.path.join(plugin_dir, 'normalize_las_settings.db')
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


class NormalizeLasWorker(QThread):
    """Worker thread for LAS normalization processing"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal()
    
    def __init__(self, input_dir, output_dir, ground_dtm, clipdata_exe, lasinfo_exe):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.ground_dtm = ground_dtm
        self.clipdata_exe = clipdata_exe
        self.lasinfo_exe = lasinfo_exe

    def run(self):
        """Execute the normalization process"""
        try:
            # Get LAS files
            las_files = [f for f in os.listdir(self.input_dir) if f.lower().endswith('.las')]
            if not las_files:
                self.log_signal.emit('[ERROR] No LAS files found in input directory.')
                self.finished_signal.emit()
                return
            
            self.log_signal.emit(f'[INFO] Found {len(las_files)} LAS files to process')
            
            # Prepare normalized output folder
            normalized_dir = os.path.join(self.output_dir, 'normalized')
            if not os.path.exists(normalized_dir):
                os.makedirs(normalized_dir)
            
            processed_count = 0
            total = len(las_files)
            
            # Process each LAS file
            for idx, las_name in enumerate(las_files):
                las_path = os.path.join(self.input_dir, las_name)
                base, ext = os.path.splitext(las_name)
                out_name = f'{base}_normalized{ext}'
                out_path = os.path.join(normalized_dir, out_name)
                
                self.log_signal.emit(f'[INFO] Processing: {las_name}')
                
                # Get bounding box using lasinfo64.exe
                lasinfo_cmd = [self.lasinfo_exe, '-i', las_path, '-json']
                
                try:
                    lasinfo_result = subprocess.run(lasinfo_cmd, shell=True, capture_output=True, text=True)
                    
                    min_x = min_y = max_x = max_y = None
                    
                    try:
                        info = json.loads(lasinfo_result.stderr)
                        header = info['lasinfo'][0]['las_header_entries']
                        min_x = str(header['min']['x'])
                        min_y = str(header['min']['y'])
                        max_x = str(header['max']['x'])
                        max_y = str(header['max']['y'])
                        self.log_signal.emit(f'  Extracted bounding box: {min_x}, {min_y}, {max_x}, {max_y}')
                    except Exception as e:
                        self.log_signal.emit(f'[ERROR] Error parsing JSON for {las_name}: {str(e)}')
                        continue
                    
                    if not all([min_x, min_y, max_x, max_y]):
                        self.log_signal.emit(f'[ERROR] Could not extract bounding box for {las_name}. Skipping.')
                        continue
                    
                    # Run clipdata64.exe with bounding box
                    cmd = [self.clipdata_exe, '/height', f'/dtm:{self.ground_dtm}', las_path, out_path, min_x, min_y, max_x, max_y]
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0 and os.path.exists(out_path):
                        processed_count += 1
                        self.log_signal.emit(f'[SUCCESS] Successfully normalized: {las_name}')
                    else:
                        self.log_signal.emit(f'[ERROR] Failed to normalize: {las_name}')
                        
                except Exception as e:
                    self.log_signal.emit(f'[ERROR] Exception processing {las_name}: {str(e)}')
                    continue
                
                # Update progress
                self.progress_signal.emit(idx + 1, total)
            
            self.log_signal.emit(f'[SUCCESS] Processing complete. {processed_count}/{len(las_files)} files normalized successfully.')
            self.finished_signal.emit()
            
        except Exception as e:
            self.log_signal.emit(f'[ERROR] Processing failed: {str(e)}')
            self.finished_signal.emit()


class NormalizeLasWidget(QWidget):
    """Compact main widget for Normalize LAS functionality"""
    
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.worker = None
        
        # Initialize settings database
        plugin_dir = os.path.dirname(os.path.dirname(__file__))
        self.db = SettingsDB(plugin_dir)
        
        self._init_ui()
        self._load_settings()
        self._detect_fusion_tools()
    
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
            self._create_field("Input LAS Folder", "input", "LAS files to normalize", self._browse_input),
            self._create_field("Output Folder", "output", "Output directory", self._browse_output),
            self._create_field("Ground DTM", "ground_dtm", "Ground DTM file", self._browse_ground_dtm)
        ])
        layout.addWidget(config_section)
        
        # Executables section
        exe_section = self._create_section("FUSION Tools", [
            self._create_field("clipdata64.exe", "clipdata_exe", "clipdata64.exe", self._browse_clipdata),
            self._create_field("lasinfo64.exe", "lasinfo_exe", "lasinfo64.exe", self._browse_lasinfo)
        ])
        layout.addWidget(exe_section)
        
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
        
        self.run_btn = QPushButton('Normalize LAS Files')
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
        
        title = QLabel("Normalize LAS")
        title.setStyleSheet("font-size: 12px; font-weight: bold;")
        
        subtitle = QLabel("Height normalization using FUSION clipdata64")
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
    
    def _browse_input(self):
        """Browse for input folder"""
        path = QFileDialog.getExistingDirectory(self, 'Select Input LAS Folder')
        if path:
            self.input_field.setText(path)
    
    def _browse_output(self):
        """Browse for output folder"""
        path = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if path:
            self.output_field.setText(path)
    
    def _browse_ground_dtm(self):
        """Browse for ground DTM file"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select Ground DTM', '', 'DTM Files (*.dtm);;All Files (*)')
        if path:
            self.ground_dtm_field.setText(path)
    
    def _browse_clipdata(self):
        """Browse for clipdata64.exe"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select clipdata64.exe', '', 'Executables (*.exe)')
        if path:
            self.clipdata_exe_field.setText(path)
    
    def _browse_lasinfo(self):
        """Browse for lasinfo64.exe"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select lasinfo64.exe', '', 'Executables (*.exe)')
        if path:
            self.lasinfo_exe_field.setText(path)
    
    def _detect_fusion_tools(self):
        """Auto-detect FUSION tools in workspace"""
        fusion_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Fusion')
        
        if os.path.exists(fusion_dir):
            clipdata_path = os.path.join(fusion_dir, 'clipdata64.exe')
            lasinfo_path = os.path.join(fusion_dir, 'lasinfo64.exe')
            
            if os.path.exists(clipdata_path) and not self.clipdata_exe_field.text():
                self.clipdata_exe_field.setText(clipdata_path)
                self.log.append("[INFO] Auto-detected clipdata64.exe")
            
            if os.path.exists(lasinfo_path) and not self.lasinfo_exe_field.text():
                self.lasinfo_exe_field.setText(lasinfo_path)
                self.log.append("[INFO] Auto-detected lasinfo64.exe")
    
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
        
        import glob
        las_files = glob.glob(os.path.join(folder, '*.las')) + glob.glob(os.path.join(folder, '*.laz'))
        self.file_list.clear()
        
        for f in las_files:
            item = QListWidgetItem(os.path.basename(f))
            item.setData(Qt.UserRole, f)  # Store full path
            self.file_list.addItem(item)
        
        self.log.append(f'[INFO] Found {len(las_files)} LAS/LAZ files.')
    
    def _load_settings(self):
        """Load saved settings"""
        self.input_field.setText(self.db.load('input'))
        self.output_field.setText(self.db.load('output'))
        self.ground_dtm_field.setText(self.db.load('ground_dtm'))
        self.clipdata_exe_field.setText(self.db.load('clipdata_exe'))
        self.lasinfo_exe_field.setText(self.db.load('lasinfo_exe'))
    
    def _run_process(self):
        """Run normalization processing"""
        # Validate inputs
        input_dir = self.input_field.text().strip()
        output_dir = self.output_field.text().strip()
        ground_dtm = self.ground_dtm_field.text().strip()
        clipdata_exe = self.clipdata_exe_field.text().strip()
        lasinfo_exe = self.lasinfo_exe_field.text().strip()
        
        if not all([input_dir, output_dir, ground_dtm, clipdata_exe, lasinfo_exe]):
            QMessageBox.warning(self, 'Missing Info', 'Please fill all required fields.')
            return
        
        if not os.path.isdir(input_dir):
            QMessageBox.warning(self, 'Invalid Input', 'Input folder not found.')
            return
        
        if not os.path.isdir(output_dir):
            QMessageBox.warning(self, 'Invalid Output', 'Output folder not found.')
            return
        
        if not os.path.isfile(ground_dtm):
            QMessageBox.warning(self, 'Invalid DTM', 'Ground DTM file not found.')
            return
        
        if not os.path.isfile(clipdata_exe):
            QMessageBox.warning(self, 'Invalid Executable', 'clipdata64.exe not found.')
            return
        
        if not os.path.isfile(lasinfo_exe):
            QMessageBox.warning(self, 'Invalid Executable', 'lasinfo64.exe not found.')
            return
        
        # Get files from list
        las_files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            las_files.append(item.data(Qt.UserRole))
        
        if not las_files:
            QMessageBox.warning(self, 'No Files', 'No LAS files to process. Click "Scan LAS Files" first.')
            return
        
        # Start processing
        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.log.clear()
        self.log.append(f'[INFO] Starting normalization for {len(las_files)} files...')
        
        self.worker = NormalizeLasWorker(input_dir, output_dir, ground_dtm, clipdata_exe, lasinfo_exe)
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
        self.log.append('[SUCCESS] All normalization processing complete!')
        QMessageBox.information(self, 'Complete', 'LAS normalization completed!')


class NormalizeLasPlugin(BasePlugin):
    """Normalize LAS Plugin"""
    
    def __init__(self, api):
        super().__init__(api)
        self.widget = None
        self.dock_widget = None
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="Normalize LAS",
            version="1.0.0",
            author="LiDAR Viewer",
            description="Height normalization using FUSION clipdata64 and ground DTM.",
            category="Tools"
        )
    
    def activate(self):
        """Activate plugin"""
        self.widget = NormalizeLasWidget(self)
        
        self.dock_widget = self.add_dock_widget(
            "Normalize LAS", 
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
        
        self.add_menu_item("Tools", "Normalize LAS", self.show_dock_widget)
        print("[INFO] Normalize LAS plugin activated")
    
    def show_dock_widget(self):
        """Show dock widget using BasePlugin's replacement logic"""
        return super().show_dock_widget()
    
    def deactivate(self):
        """Deactivate plugin"""
        if self.widget and self.widget.worker and self.widget.worker.isRunning():
            self.widget.worker.terminate()
            self.widget.worker.wait()
        super().deactivate()
        print("[INFO] Normalize LAS plugin deactivated")

"""
GroundFilter Plugin for LiDAR Viewer

This plugin provides ground filtering functionality using FUSION's GroundFilter tool
along with utilities for LAS info and DTM generation.
"""

import os
import sys
import sqlite3
import subprocess
import glob
from PySide6.QtWidgets import *
from PySide6.QtCore import QThread, Signal, Qt

from plugins.plugin_manager import BasePlugin, PluginInfo


class SettingsDB:
    """Handles all database operations for settings"""
    
    def __init__(self, plugin_dir):
        self.db_path = os.path.join(plugin_dir, 'groundfilter_settings.db')
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


class LasInfoWorker(QThread):
    """Worker thread for LAS info processing"""
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, exe_path, las_path):
        super().__init__()
        self.exe_path = exe_path
        self.las_path = las_path

    def run(self):
        cmd = [self.exe_path, self.las_path]
        self.log_signal.emit(f'Running command: {" ".join(cmd)}')
        try:
            result = subprocess.run(cmd, shell=False, capture_output=True, text=True)
            self.log_signal.emit(f'STDOUT: {result.stdout[:5000]}')
            if result.stderr:
                self.log_signal.emit(f'STDERR: {result.stderr[:500]}')
            self.log_signal.emit(f'Return code: {result.returncode}')
            
            if result.returncode != 0:
                self.log_signal.emit('[ERROR] lasinfo failed.')
            else:
                self.log_signal.emit('[SUCCESS] lasinfo completed.')
        except Exception as e:
            self.log_signal.emit(f'[ERROR] Exception running lasinfo: {str(e)}')
        
        self.finished_signal.emit()


class GroundFilterWorker(QThread):
    """Worker thread for GroundFilter processing"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal()

    def __init__(self, exe_path, in_path, out_path, cell_size, gparam, wparam, iterations):
        super().__init__()
        self.exe_path = exe_path
        self.in_path = in_path
        self.out_path = out_path
        self.cell_size = cell_size
        self.gparam = gparam
        self.wparam = wparam
        self.iterations = iterations

    def run(self):
        cmd = [self.exe_path]
        if self.gparam:
            cmd.append(f'/gparam:{self.gparam}')
        if self.wparam:
            cmd.append(f'/wparam:{self.wparam}')
        if self.iterations:
            cmd.append(f'/iterations:{self.iterations}')
        cmd.extend([self.out_path, str(self.cell_size), self.in_path])
        
        self.log_signal.emit(f'Running command: {" ".join(cmd)}')
        try:
            result = subprocess.run(cmd, shell=False, capture_output=True, text=True)
            self.log_signal.emit(f'STDOUT: {result.stdout[:500]}')
            if result.stderr:
                self.log_signal.emit(f'STDERR: {result.stderr[:500]}')
            self.log_signal.emit(f'Return code: {result.returncode}')
            
            if result.returncode == 0:
                self.log_signal.emit('[SUCCESS] Ground points file generation complete.')
            else:
                self.log_signal.emit('[ERROR] GroundFilter failed.')
        except Exception as e:
            self.log_signal.emit(f'[ERROR] Exception running GroundFilter: {str(e)}')
        
        self.finished_signal.emit()


class DTMWorker(QThread):
    """Worker thread for DTM generation"""
    log_signal = Signal(str)
    progress_signal = Signal(int, int)
    finished_signal = Signal()

    def __init__(self, exe_path, out_dtm, cell_size, xyunits, zunits, coordsys, zone, horizdatum, vertdatum, ground_las, extra_params=''):
        super().__init__()
        self.exe_path = exe_path
        self.out_dtm = out_dtm
        self.cell_size = cell_size
        self.xyunits = xyunits
        self.zunits = zunits
        self.coordsys = coordsys
        self.zone = zone
        self.horizdatum = horizdatum
        self.vertdatum = vertdatum
        self.ground_las = ground_las
        self.extra_params = extra_params

    def run(self):
        cmd = [self.exe_path]
        if self.extra_params:
            cmd.extend(self.extra_params.split())
        cmd.extend([
            self.out_dtm,
            str(self.cell_size),
            self.xyunits,
            self.zunits,
            str(self.coordsys),
            str(self.zone),
            str(self.horizdatum),
            str(self.vertdatum),
            self.ground_las
        ])
        
        self.log_signal.emit(f'Running command: {" ".join(cmd)}')
        try:
            result = subprocess.run(cmd, shell=False, capture_output=True, text=True)
            self.log_signal.emit(f'STDOUT: {result.stdout[:500]}')
            if result.stderr:
                self.log_signal.emit(f'STDERR: {result.stderr[:500]}')
            self.log_signal.emit(f'Return code: {result.returncode}')
            
            if result.returncode == 0:
                self.log_signal.emit('[SUCCESS] DTM generation complete.')
            else:
                self.log_signal.emit('[ERROR] DTM generation failed.')
        except Exception as e:
            self.log_signal.emit(f'[ERROR] Exception running GridSurfaceCreate: {str(e)}')
        
        self.finished_signal.emit()


class GroundFilterWidget(QWidget):
    """Compact main widget for GroundFilter functionality"""
    
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.worker = None
        self.dtm_worker = None
        self.lasinfo_worker = None
        
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
        
        # Create tabs for the three functions
        self.tabs = QTabWidget()
        
        # GroundFilter Tab
        gf_tab = self._create_groundfilter_tab()
        self.tabs.addTab(gf_tab, "Ground Filter")
        
        # DTM Generation Tab  
        dtm_tab = self._create_dtm_tab()
        self.tabs.addTab(dtm_tab, "DTM Generation")
        
        # LAS Info Tab
        lasinfo_tab = self._create_lasinfo_tab()
        self.tabs.addTab(lasinfo_tab, "LAS Info")
        
        layout.addWidget(self.tabs)
        
        # Progress bar (shared)
        self.progress = QProgressBar()
        self.progress.setMinimumHeight(20)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Log section (shared)
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
        
        title = QLabel("GroundFilter")
        title.setStyleSheet("font-size: 12px; font-weight: bold;")
        
        subtitle = QLabel("Ground Processing & DTM Tools")
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
    
    def _create_groundfilter_tab(self):
        """Create the GroundFilter tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Configuration section
        config_section = self._create_section("Configuration", [
            self._create_field("GroundFilter.exe", "gf_exe", "GroundFilter.exe", self._browse_gf_exe),
            self._create_field("Input LAS File", "gf_input", "Input LAS file", self._browse_gf_input),
            self._create_field("Output LAS File", "gf_output", "Output LAS file", self._browse_gf_output)
        ])
        layout.addWidget(config_section)
        
        # Parameters section
        params_section = self._create_section("Parameters", [
            self._create_gf_param_fields()
        ])
        layout.addWidget(params_section)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        current_btn = QPushButton('Use Current Layer')
        current_btn.setMinimumHeight(24)
        current_btn.clicked.connect(self._use_current_layer_gf)
        buttons_layout.addWidget(current_btn)
        
        self.gf_run_btn = QPushButton('Run GroundFilter')
        self.gf_run_btn.setMinimumHeight(28)
        self.gf_run_btn.clicked.connect(self._run_groundfilter)
        buttons_layout.addWidget(self.gf_run_btn)
        layout.addLayout(buttons_layout)
        
        return tab
    
    def _create_dtm_tab(self):
        """Create the DTM generation tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Configuration section
        config_section = self._create_section("Configuration", [
            self._create_field("GridSurfaceCreate.exe", "dtm_exe", "GridSurfaceCreate.exe", self._browse_dtm_exe),
            self._create_field("Ground LAS File", "dtm_input", "Ground points LAS file", self._browse_dtm_input),
            self._create_field("Output DTM File", "dtm_output", "Output DTM file", self._browse_dtm_output)
        ])
        layout.addWidget(config_section)
        
        # Parameters section
        params_section = self._create_section("Parameters", [
            self._create_dtm_param_fields()
        ])
        layout.addWidget(params_section)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        current_btn = QPushButton('Use Current Layer')
        current_btn.setMinimumHeight(24)
        current_btn.clicked.connect(self._use_current_layer_dtm)
        buttons_layout.addWidget(current_btn)
        
        self.dtm_run_btn = QPushButton('Generate DTM')
        self.dtm_run_btn.setMinimumHeight(28)
        self.dtm_run_btn.clicked.connect(self._run_dtm)
        buttons_layout.addWidget(self.dtm_run_btn)
        layout.addLayout(buttons_layout)
        
        return tab
    
    def _create_lasinfo_tab(self):
        """Create the LAS info tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Configuration section
        config_section = self._create_section("Configuration", [
            self._create_field("lasinfo.exe", "lasinfo_exe", "lasinfo.exe", self._browse_lasinfo_exe),
            self._create_field("LAS File", "lasinfo_input", "LAS file to analyze", self._browse_lasinfo_input)
        ])
        layout.addWidget(config_section)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        current_btn = QPushButton('Use Current Layer')
        current_btn.setMinimumHeight(24)
        current_btn.clicked.connect(self._use_current_layer_lasinfo)
        buttons_layout.addWidget(current_btn)
        
        self.lasinfo_run_btn = QPushButton('Run LAS Info')
        self.lasinfo_run_btn.setMinimumHeight(28)
        self.lasinfo_run_btn.clicked.connect(self._run_lasinfo)
        buttons_layout.addWidget(self.lasinfo_run_btn)
        layout.addLayout(buttons_layout)
        
        return tab
    
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
    
    def _create_gf_param_fields(self):
        """Create GroundFilter parameter input fields"""
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Row 1: Cell Size and Iterations
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Cell Size"))
        self.gf_cell_size_field = QDoubleSpinBox()
        self.gf_cell_size_field.setDecimals(2)
        self.gf_cell_size_field.setRange(0.01, 1000.0)
        self.gf_cell_size_field.setValue(10.0)
        self.gf_cell_size_field.setMinimumHeight(22)
        self.gf_cell_size_field.valueChanged.connect(lambda v: self.db.save('gf_cell_size', str(v)))
        row1.addWidget(self.gf_cell_size_field)
        
        row1.addWidget(QLabel("Iterations"))
        self.gf_iterations_field = QSpinBox()
        self.gf_iterations_field.setRange(1, 100)
        self.gf_iterations_field.setValue(8)
        self.gf_iterations_field.setMinimumHeight(22)
        self.gf_iterations_field.valueChanged.connect(lambda v: self.db.save('gf_iterations', str(v)))
        row1.addWidget(self.gf_iterations_field)
        layout.addLayout(row1)
        
        # Row 2: Optional parameters
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("gparam (opt)"))
        self.gf_gparam_field = QLineEdit()
        self.gf_gparam_field.setPlaceholderText("e.g. 0")
        self.gf_gparam_field.setMinimumHeight(22)
        self.gf_gparam_field.textChanged.connect(lambda text: self.db.save('gf_gparam', text))
        row2.addWidget(self.gf_gparam_field)
        
        row2.addWidget(QLabel("wparam (opt)"))
        self.gf_wparam_field = QLineEdit()
        self.gf_wparam_field.setPlaceholderText("e.g. 0.5")
        self.gf_wparam_field.setMinimumHeight(22)
        self.gf_wparam_field.textChanged.connect(lambda text: self.db.save('gf_wparam', text))
        row2.addWidget(self.gf_wparam_field)
        layout.addLayout(row2)
        
        return frame
    
    def _create_dtm_param_fields(self):
        """Create DTM parameter input fields"""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Cell Size
        cell_layout = QVBoxLayout()
        cell_layout.addWidget(QLabel("Cell Size"))
        self.dtm_cell_size_field = QDoubleSpinBox()
        self.dtm_cell_size_field.setDecimals(2)
        self.dtm_cell_size_field.setRange(0.01, 1000.0)
        self.dtm_cell_size_field.setValue(10.0)
        self.dtm_cell_size_field.setMinimumHeight(22)
        self.dtm_cell_size_field.valueChanged.connect(lambda v: self.db.save('dtm_cell_size', str(v)))
        cell_layout.addWidget(self.dtm_cell_size_field)
        layout.addLayout(cell_layout)
        
        return frame
    
    def _close_plugin(self):
        """Close the plugin widget"""
        if hasattr(self.plugin, 'dock_widget') and self.plugin.dock_widget:
            self.plugin.dock_widget.hide()
    
    # Browse methods
    def _browse_gf_exe(self):
        """Browse for GroundFilter.exe"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select GroundFilter.exe', '', 'Executables (*.exe)')
        if path:
            self.gf_exe_field.setText(path)
    
    def _browse_gf_input(self):
        """Browse for input LAS file"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select Input LAS File', '', 'LAS Files (*.las *.laz)')
        if path:
            self.gf_input_field.setText(path)
    
    def _browse_gf_output(self):
        """Browse for output LAS file"""
        path, _ = QFileDialog.getSaveFileName(self, 'Select Output LAS File', '', 'LAS Files (*.las)')
        if path:
            self.gf_output_field.setText(path)
    
    def _browse_dtm_exe(self):
        """Browse for GridSurfaceCreate.exe"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select GridSurfaceCreate.exe', '', 'Executables (*.exe)')
        if path:
            self.dtm_exe_field.setText(path)
    
    def _browse_dtm_input(self):
        """Browse for ground LAS file"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select Ground LAS File', '', 'LAS Files (*.las *.laz)')
        if path:
            self.dtm_input_field.setText(path)
    
    def _browse_dtm_output(self):
        """Browse for output DTM file"""
        path, _ = QFileDialog.getSaveFileName(self, 'Select Output DTM File', '', 'DTM Files (*.dtm)')
        if path:
            self.dtm_output_field.setText(path)
    
    def _browse_lasinfo_exe(self):
        """Browse for lasinfo.exe"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select lasinfo.exe', '', 'Executables (*.exe)')
        if path:
            self.lasinfo_exe_field.setText(path)
    
    def _browse_lasinfo_input(self):
        """Browse for LAS file"""
        path, _ = QFileDialog.getOpenFileName(self, 'Select LAS File', '', 'LAS Files (*.las *.laz)')
        if path:
            self.lasinfo_input_field.setText(path)
    
    # Current layer methods
    def _use_current_layer_gf(self):
        """Use current layer for GroundFilter"""
        current_layer = self.plugin.api.get_current_layer()
        if not current_layer:
            QMessageBox.warning(self, 'No Layer', 'No layer is currently selected.')
            return
        
        file_path = current_layer.get('file_path', '')
        if file_path and os.path.exists(file_path):
            self.gf_input_field.setText(file_path)
            self.plugin.api.update_status(f'Using current layer: {os.path.basename(file_path)}')
        else:
            QMessageBox.warning(self, 'No File', 'Current layer has no associated LAS file.')
    
    def _use_current_layer_dtm(self):
        """Use current layer for DTM"""
        current_layer = self.plugin.api.get_current_layer()
        if not current_layer:
            QMessageBox.warning(self, 'No Layer', 'No layer is currently selected.')
            return
        
        file_path = current_layer.get('file_path', '')
        if file_path and os.path.exists(file_path):
            self.dtm_input_field.setText(file_path)
            self.plugin.api.update_status(f'Using current layer: {os.path.basename(file_path)}')
        else:
            QMessageBox.warning(self, 'No File', 'Current layer has no associated LAS file.')
    
    def _use_current_layer_lasinfo(self):
        """Use current layer for LAS info"""
        current_layer = self.plugin.api.get_current_layer()
        if not current_layer:
            QMessageBox.warning(self, 'No Layer', 'No layer is currently selected.')
            return
        
        file_path = current_layer.get('file_path', '')
        if file_path and os.path.exists(file_path):
            self.lasinfo_input_field.setText(file_path)
            self.plugin.api.update_status(f'Using current layer: {os.path.basename(file_path)}')
        else:
            QMessageBox.warning(self, 'No File', 'Current layer has no associated LAS file.')
    
    def _load_settings(self):
        """Load saved settings"""
        self.gf_exe_field.setText(self.db.load('gf_exe'))
        self.gf_input_field.setText(self.db.load('gf_input'))
        self.gf_output_field.setText(self.db.load('gf_output'))
        self.gf_cell_size_field.setValue(float(self.db.load('gf_cell_size', '10.0')))
        self.gf_iterations_field.setValue(int(self.db.load('gf_iterations', '8')))
        self.gf_gparam_field.setText(self.db.load('gf_gparam'))
        self.gf_wparam_field.setText(self.db.load('gf_wparam'))
        
        self.dtm_exe_field.setText(self.db.load('dtm_exe'))
        self.dtm_input_field.setText(self.db.load('dtm_input'))
        self.dtm_output_field.setText(self.db.load('dtm_output'))
        self.dtm_cell_size_field.setValue(float(self.db.load('dtm_cell_size', '10.0')))
        
        self.lasinfo_exe_field.setText(self.db.load('lasinfo_exe'))
        self.lasinfo_input_field.setText(self.db.load('lasinfo_input'))
    
    # Process methods
    def _run_groundfilter(self):
        """Run GroundFilter processing"""
        exe = self.gf_exe_field.text().strip()
        input_file = self.gf_input_field.text().strip()
        output_file = self.gf_output_field.text().strip()
        
        if not all([exe, input_file, output_file]):
            QMessageBox.warning(self, 'Missing Info', 'Please fill all required fields.')
            return
        
        if not os.path.isfile(exe):
            # Try to find GroundFilter.exe automatically
            exe_candidates = [
                os.path.join(os.path.dirname(__file__), '..', '..', 'Fusion', 'GroundFilter.exe'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'Fusion', 'GroundFilter64.exe'),
            ]
            
            found_exe = None
            for candidate in exe_candidates:
                if os.path.isfile(candidate):
                    found_exe = candidate
                    break
            
            if found_exe:
                exe = found_exe
                self.gf_exe_field.setText(exe)
            else:
                QMessageBox.warning(self, 'Invalid Executable', 'GroundFilter.exe not found.')
                return
        
        if not os.path.isfile(input_file):
            QMessageBox.warning(self, 'Invalid Input', 'Input LAS file not found.')
            return
        
        # Start processing
        cell_size = self.gf_cell_size_field.value()
        gparam = self.gf_gparam_field.text().strip()
        wparam = self.gf_wparam_field.text().strip()
        iterations = self.gf_iterations_field.value()
        
        self.gf_run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate
        self.log.clear()
        self.log.append(f'[INFO] Starting GroundFilter processing...')
        
        self.worker = GroundFilterWorker(exe, input_file, output_file, cell_size, gparam, wparam, iterations)
        self.worker.log_signal.connect(self.log.append)
        self.worker.finished_signal.connect(self._on_groundfilter_finished)
        self.worker.start()
    
    def _run_dtm(self):
        """Run DTM generation"""
        exe = self.dtm_exe_field.text().strip()
        input_file = self.dtm_input_field.text().strip()
        output_file = self.dtm_output_field.text().strip()
        
        if not all([exe, input_file, output_file]):
            QMessageBox.warning(self, 'Missing Info', 'Please fill all required fields.')
            return
        
        if not os.path.isfile(exe):
            # Try to find GridSurfaceCreate.exe automatically
            exe_candidates = [
                os.path.join(os.path.dirname(__file__), '..', '..', 'Fusion', 'GridSurfaceCreate.exe'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'Fusion', 'GridSurfaceCreate64.exe'),
            ]
            
            found_exe = None
            for candidate in exe_candidates:
                if os.path.isfile(candidate):
                    found_exe = candidate
                    break
            
            if found_exe:
                exe = found_exe
                self.dtm_exe_field.setText(exe)
            else:
                QMessageBox.warning(self, 'Invalid Executable', 'GridSurfaceCreate.exe not found.')
                return
        
        if not os.path.isfile(input_file):
            QMessageBox.warning(self, 'Invalid Input', 'Ground LAS file not found.')
            return
        
        # Start processing
        cell_size = self.dtm_cell_size_field.value()
        
        self.dtm_run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate
        self.log.clear()
        self.log.append(f'[INFO] Starting DTM generation...')
        
        self.dtm_worker = DTMWorker(exe, output_file, cell_size, 'M', 'M', 0, 0, 0, 0, input_file)
        self.dtm_worker.log_signal.connect(self.log.append)
        self.dtm_worker.finished_signal.connect(self._on_dtm_finished)
        self.dtm_worker.start()
    
    def _run_lasinfo(self):
        """Run LAS info"""
        exe = self.lasinfo_exe_field.text().strip()
        input_file = self.lasinfo_input_field.text().strip()
        
        if not all([exe, input_file]):
            QMessageBox.warning(self, 'Missing Info', 'Please fill all required fields.')
            return
        
        if not os.path.isfile(exe):
            # Try to find lasinfo.exe automatically
            exe_candidates = [
                os.path.join(os.path.dirname(__file__), '..', '..', 'Fusion', 'lasinfo.exe'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'Fusion', 'lasinfo64.exe'),
            ]
            
            found_exe = None
            for candidate in exe_candidates:
                if os.path.isfile(candidate):
                    found_exe = candidate
                    break
            
            if found_exe:
                exe = found_exe
                self.lasinfo_exe_field.setText(exe)
            else:
                QMessageBox.warning(self, 'Invalid Executable', 'lasinfo.exe not found.')
                return
        
        if not os.path.isfile(input_file):
            QMessageBox.warning(self, 'Invalid Input', 'LAS file not found.')
            return
        
        # Start processing
        self.lasinfo_run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate
        self.log.clear()
        self.log.append(f'[INFO] Starting LAS info analysis...')
        
        self.lasinfo_worker = LasInfoWorker(exe, input_file)
        self.lasinfo_worker.log_signal.connect(self.log.append)
        self.lasinfo_worker.finished_signal.connect(self._on_lasinfo_finished)
        self.lasinfo_worker.start()
    
    # Event handlers
    def _on_groundfilter_finished(self):
        """Handle GroundFilter completion"""
        self.gf_run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.log.append('[SUCCESS] GroundFilter processing complete!')
        QMessageBox.information(self, 'Complete', 'GroundFilter processing completed!')
    
    def _on_dtm_finished(self):
        """Handle DTM completion"""
        self.dtm_run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.log.append('[SUCCESS] DTM generation complete!')
        QMessageBox.information(self, 'Complete', 'DTM generation completed!')
    
    def _on_lasinfo_finished(self):
        """Handle LAS info completion"""
        self.lasinfo_run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.log.append('[SUCCESS] LAS info analysis complete!')


class GroundFilterPlugin(BasePlugin):
    def __init__(self, api):
        super().__init__(api)
        self._info = PluginInfo(
            name="GroundFilter",
            version="1.0.0",
            description="Ground filtering, DTM generation, and LAS info utilities using FUSION tools",
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
        self.widget = GroundFilterWidget(self)
        
        # Use BasePlugin's add_dock_widget method (hidden by default)
        self.dock_widget = self.add_dock_widget(
            "GroundFilter", 
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
        self.add_menu_item("Tools", "GroundFilter", self.show_dock_widget)
        
        print(f"[INFO] {self.info.name} plugin activated")
        return True
    
    def show_dock_widget(self):
        """Show dock widget using BasePlugin's replacement logic"""
        return super().show_dock_widget()
    
    def deactivate(self):
        """Deactivate the plugin"""
        if self.widget:
            # Stop any running workers
            if hasattr(self.widget, 'worker') and self.widget.worker:
                self.widget.worker.terminate()
            if hasattr(self.widget, 'dtm_worker') and self.widget.dtm_worker:
                self.widget.dtm_worker.terminate()
            if hasattr(self.widget, 'lasinfo_worker') and self.widget.lasinfo_worker:
                self.widget.lasinfo_worker.terminate()
        
        super().deactivate()
        print(f"[INFO] {self.info.name} plugin deactivated")

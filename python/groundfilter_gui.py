
import sys
import os
import sqlite3
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QMessageBox, QSpinBox, QDoubleSpinBox, QProgressBar, QSizePolicy, QTabWidget, QCheckBox
)
from PyQt5.QtCore import QThread, pyqtSignal


class LasInfoWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

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
            self.log_signal.emit(f'STDERR: {result.stderr[:500]}')
            self.log_signal.emit(f'Return code: {result.returncode}')
            self.finished_signal.emit(result.returncode == 0)
        except Exception as e:
            self.log_signal.emit(f'Error running lasinfo: {e}')
            self.finished_signal.emit(False)

class TIFWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, exe_path, dtm_path):
        super().__init__()
        self.exe_path = exe_path
        self.dtm_path = dtm_path

    def run(self):
        cmd = [self.exe_path, self.dtm_path]
        self.log_signal.emit(f'Running command: {" ".join(cmd)}')
        try:
            result = subprocess.run(cmd, shell=False, capture_output=True, text=True)
            self.log_signal.emit(f'STDOUT: {result.stdout[:500]}')
            self.log_signal.emit(f'STDERR: {result.stderr[:500]}')
            self.log_signal.emit(f'Return code: {result.returncode}')
            if result.returncode == 0:
                self.log_signal.emit('DTM to TIFF conversion complete.')
                self.finished_signal.emit(True)
            else:
                self.log_signal.emit('DTM2TIF failed.')
                self.finished_signal.emit(False)
        except Exception as e:
            self.log_signal.emit(f'Error running DTM2TIF: {e}')
            self.finished_signal.emit(False)
from PyQt5.QtCore import QThread, pyqtSignal

def get_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_settings.db')

def ns_key(key):
    return f'groundfilter_gui:{key}'

def save_setting(key, value):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    c.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', (ns_key(key), value))
    conn.commit()
    conn.close()

def load_setting(key):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    c.execute('SELECT value FROM settings WHERE key=?', (ns_key(key),))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''

class DTMWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, exe_path, ground_las, out_dtm, cell_size, xyunits, zunits, coordsys, zone, horizdatum, vertdatum, extra_params):
        super().__init__()
        self.exe_path = exe_path
        self.ground_las = ground_las
        self.out_dtm = out_dtm
        self.cell_size = cell_size
        self.xyunits = xyunits
        self.zunits = zunits
        self.coordsys = coordsys
        self.zone = zone
        self.horizdatum = horizdatum
        self.vertdatum = vertdatum
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
            self.log_signal.emit(f'STDERR: {result.stderr[:500]}')
            self.log_signal.emit(f'Return code: {result.returncode}')
            if result.returncode == 0:
                self.log_signal.emit('DTM generation complete.')
                self.finished_signal.emit(True)
            else:
                self.log_signal.emit('DTM generation failed.')
                self.finished_signal.emit(False)
        except Exception as e:
            self.log_signal.emit(f'Error running GridSurfaceCreate: {e}')
            self.finished_signal.emit(False)

class GroundFilterWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

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
            self.log_signal.emit(f'STDERR: {result.stderr[:500]}')
            self.log_signal.emit(f'Return code: {result.returncode}')
            if result.returncode == 0:
                self.log_signal.emit('Ground points file generation complete.')
                self.finished_signal.emit(True)
            else:
                self.log_signal.emit('GroundFilter failed.')
                self.finished_signal.emit(False)
        except Exception as e:
            self.log_signal.emit(f'Error running GroundFilter: {e}')
            self.finished_signal.emit(False)



class GroundFilterApp(QWidget):
    def pick_lasinfo_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select LAS file', '', 'LAS Files (*.las);;All Files (*)')
        if path:
            self.lasinfo_las_edit.setText(path)
            save_setting('lasinfo_las_path', path)

    def pick_lasinfo_exe(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select lasinfo.exe', '', 'Executables (*.exe)')
        if path:
            self.lasinfo_exe_edit.setText(path)
            save_setting('lasinfo_exe_path', path)

    def run_lasinfo(self):
        las_path = self.lasinfo_las_edit.text().strip()
        exe_path = self.lasinfo_exe_edit.text().strip()
        save_setting('lasinfo_las_path', las_path)
        save_setting('lasinfo_exe_path', exe_path)
        if not os.path.isfile(las_path):
            QMessageBox.warning(self, 'Missing Input', f'LAS file not found: {las_path}')
            self.lasinfo_log(f'LAS file not found: {las_path}')
            return
        if not exe_path or not os.path.isfile(exe_path):
            QMessageBox.warning(self, 'Missing Executable', f'lasinfo.exe not found: {exe_path}')
            self.lasinfo_log(f'lasinfo.exe not found: {exe_path}')
            return
        self.lasinfo_run_btn.setEnabled(False)
        self.lasinfo_progress.setVisible(True)
        self.lasinfo_log('Starting lasinfo...')
        self.lasinfo_worker = LasInfoWorker(exe_path, las_path)
        self.lasinfo_worker.log_signal.connect(self.lasinfo_log)
        self.lasinfo_worker.finished_signal.connect(self.on_lasinfo_finished)
        self.lasinfo_worker.start()

    def lasinfo_log(self, msg):
        self.lasinfo_log_output.append(msg)
        print('[LASINFO]', msg)

    def on_lasinfo_finished(self, success):
        self.lasinfo_run_btn.setEnabled(True)
        self.lasinfo_progress.setVisible(False)
        if success:
            self.lasinfo_log('lasinfo finished successfully.')
        else:
            self.lasinfo_log('lasinfo finished with errors.')
    def pick_dtm_tif_exe_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select DTM2TIF.exe', '', 'Executables (*.exe)')
        if path:
            self.dtm_tif_exe_edit.setText(path)
            save_setting('dtm_tif_exe_path', path)
    def pick_dtm_ground_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select Ground Points LAS', '', 'LAS Files (*.las);;All Files (*)')
        if path:
            self.dtm_ground_edit.setText(path)
            save_setting('dtm_ground_las', path)
    def __init__(self):
        super().__init__()
        self.setWindowTitle('GroundFilter & DTM Generator')
        self.resize(750, 500)
        self.worker = None
        self.dtm_worker = None
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.tabs = QTabWidget()
        # --- LAS Info Tab ---
        self.lasinfo_tab = QWidget()
        self.lasinfo_layout = QVBoxLayout()
        self.lasinfo_las_edit = QLineEdit()
        lasinfo_las_btn = QPushButton('Browse...')
        lasinfo_las_btn.clicked.connect(self.pick_lasinfo_file)
        self.lasinfo_layout.addLayout(self._row('LAS file:', self.lasinfo_las_edit, lasinfo_las_btn))
        self.lasinfo_exe_edit = QLineEdit()
        lasinfo_exe_btn = QPushButton('Browse...')
        lasinfo_exe_btn.clicked.connect(self.pick_lasinfo_exe)
        self.lasinfo_layout.addLayout(self._row('lasinfo.exe:', self.lasinfo_exe_edit, lasinfo_exe_btn))
        self.lasinfo_run_btn = QPushButton('Run lasinfo')
        self.lasinfo_run_btn.clicked.connect(self.run_lasinfo)
        self.lasinfo_layout.addWidget(self.lasinfo_run_btn)
        self.lasinfo_progress = QProgressBar()
        self.lasinfo_progress.setMinimum(0)
        self.lasinfo_progress.setMaximum(0)
        self.lasinfo_progress.setVisible(False)
        self.lasinfo_progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lasinfo_layout.addWidget(self.lasinfo_progress)
        self.lasinfo_log_output = QTextEdit()
        self.lasinfo_log_output.setReadOnly(True)
        self.lasinfo_log_output.setMinimumHeight(100)
        self.lasinfo_layout.addWidget(QLabel('Log Output:'))
        self.lasinfo_layout.addWidget(self.lasinfo_log_output)
        self.lasinfo_tab.setLayout(self.lasinfo_layout)

        # --- GroundFilter Tab ---
        self.gf_tab = QWidget()
        self.gf_layout = QVBoxLayout()
        self.in_edit = QLineEdit()
        in_btn = QPushButton('Browse...')
        in_btn.clicked.connect(self.pick_input_file)
        self.gf_layout.addLayout(self._row('Input LAS:', self.in_edit, in_btn))
        self.out_edit = QLineEdit()
        out_btn = QPushButton('Browse...')
        out_btn.clicked.connect(self.pick_output_file)
        self.gf_layout.addLayout(self._row('Output LAS:', self.out_edit, out_btn))
        self.exe_edit = QLineEdit()
        exe_btn = QPushButton('Browse...')
        exe_btn.clicked.connect(self.pick_exe_file)
        self.gf_layout.addLayout(self._row('GroundFilter.exe:', self.exe_edit, exe_btn))
        self.cellsize_edit = QDoubleSpinBox()
        self.cellsize_edit.setDecimals(2)
        self.cellsize_edit.setRange(0.01, 1000.0)
        self.cellsize_edit.setValue(10.0)
        self.gf_layout.addLayout(self._row('Cell Size:', self.cellsize_edit, None))
        self.gparam_edit = QLineEdit()
        self.gparam_edit.setPlaceholderText('e.g. 0')
        self.gf_layout.addLayout(self._row('gparam (optional):', self.gparam_edit, None))
        self.wparam_edit = QLineEdit()
        self.wparam_edit.setPlaceholderText('e.g. 0.5')
        self.gf_layout.addLayout(self._row('wparam (optional):', self.wparam_edit, None))
        self.iter_edit = QSpinBox()
        self.iter_edit.setRange(1, 100)
        self.iter_edit.setValue(8)
        self.gf_layout.addLayout(self._row('iterations (optional):', self.iter_edit, None))
        self.run_btn = QPushButton('Run GroundFilter')
        self.run_btn.clicked.connect(self.run_process)
        self.gf_layout.addWidget(self.run_btn)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.gf_layout.addWidget(self.progress_bar)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(100)
        self.gf_layout.addWidget(QLabel('Log Output:'))
        self.gf_layout.addWidget(self.log_output)
        self.gf_tab.setLayout(self.gf_layout)

        # --- DTM Generation Tab ---
        self.dtm_tab = QWidget()
        self.dtm_layout = QVBoxLayout()
        self.dtm_ground_edit = QLineEdit()
        dtm_ground_btn = QPushButton('Browse...')
        dtm_ground_btn.clicked.connect(self.pick_dtm_ground_file)
        self.dtm_layout.addLayout(self._row('Ground Points LAS:', self.dtm_ground_edit, dtm_ground_btn))
        self.dtm_out_edit = QLineEdit()
        dtm_out_btn = QPushButton('Browse...')
        dtm_out_btn.clicked.connect(self.pick_dtm_output_file)
        self.dtm_layout.addLayout(self._row('Output DTM:', self.dtm_out_edit, dtm_out_btn))
        self.dtm_tif_checkbox = QCheckBox('Also generate GeoTIFF (.tif) from DTM')
        self.dtm_tif_checkbox.stateChanged.connect(lambda: save_setting('dtm_tif_checked', str(self.dtm_tif_checkbox.isChecked())))
        self.dtm_layout.addWidget(self.dtm_tif_checkbox)
        self.dtm_tif_exe_edit = QLineEdit()
        dtm_tif_exe_btn = QPushButton('Browse...')
        dtm_tif_exe_btn.clicked.connect(self.pick_dtm_tif_exe_file)
        self.dtm_layout.addLayout(self._row('DTM2TIF.exe:', self.dtm_tif_exe_edit, dtm_tif_exe_btn))
        self.dtm_exe_edit = QLineEdit()
        dtm_exe_btn = QPushButton('Browse...')
        dtm_exe_btn.clicked.connect(self.pick_dtm_exe_file)
        self.dtm_layout.addLayout(self._row('GridSurfaceCreate.exe:', self.dtm_exe_edit, dtm_exe_btn))
        self.dtm_cellsize_edit = QDoubleSpinBox()
        self.dtm_cellsize_edit.setDecimals(2)
        self.dtm_cellsize_edit.setRange(0.01, 1000.0)
        self.dtm_cellsize_edit.setValue(10.0)
        self.dtm_layout.addLayout(self._row('Cell Size:', self.dtm_cellsize_edit, None))
        # XY units
        self.dtm_xyunits_edit = QLineEdit()
        self.dtm_xyunits_edit.setText('M')
        self.dtm_layout.addLayout(self._row('XY Units (M/F):', self.dtm_xyunits_edit, None))
        # Z units
        self.dtm_zunits_edit = QLineEdit()
        self.dtm_zunits_edit.setText('M')
        self.dtm_layout.addLayout(self._row('Z Units (M/F):', self.dtm_zunits_edit, None))
        # Coordinate system
        self.dtm_coordsys_edit = QSpinBox()
        self.dtm_coordsys_edit.setRange(0, 2)
        self.dtm_coordsys_edit.setValue(1)  # 1 = UTM
        self.dtm_layout.addLayout(self._row('CoordSys (0=Unknown,1=UTM,2=State Plane):', self.dtm_coordsys_edit, None))
        # Zone
        self.dtm_zone_edit = QSpinBox()
        self.dtm_zone_edit.setRange(0, 60)
        self.dtm_zone_edit.setValue(20)
        self.dtm_layout.addLayout(self._row('Zone:', self.dtm_zone_edit, None))
        # Horizontal datum
        self.dtm_horizdatum_edit = QSpinBox()
        self.dtm_horizdatum_edit.setRange(0, 2)
        self.dtm_horizdatum_edit.setValue(2)  # 2 = NAD83
        self.dtm_layout.addLayout(self._row('HorizDatum (0=Unknown,1=NAD27,2=NAD83):', self.dtm_horizdatum_edit, None))
        # Vertical datum
        self.dtm_vertdatum_edit = QSpinBox()
        self.dtm_vertdatum_edit.setRange(0, 3)
        self.dtm_vertdatum_edit.setValue(2)  # 2 = NAVD88
        self.dtm_vertdatum_edit.setToolTip(
            'FUSION only supports: 0=Unknown, 1=NGVD29, 2=NAVD88, 3=GRS80.\n'
            'If your vertical datum is CGVD2013, select 0 (Unknown) and document the actual datum elsewhere.'
        )
        self.dtm_layout.addLayout(self._row('VertDatum (0=Unknown,1=NGVD29,2=NAVD88,3=GRS80):', self.dtm_vertdatum_edit, None))
        self.dtm_extra_edit = QLineEdit()
        self.dtm_extra_edit.setPlaceholderText('Extra params (optional)')
        self.dtm_layout.addLayout(self._row('Extra Params:', self.dtm_extra_edit, None))
        self.dtm_run_btn = QPushButton('Run DTM Generation')
        self.dtm_run_btn.clicked.connect(self.run_dtm_process)
        self.dtm_layout.addWidget(self.dtm_run_btn)
        self.dtm_progress_bar = QProgressBar()
        self.dtm_progress_bar.setMinimum(0)
        self.dtm_progress_bar.setMaximum(0)
        self.dtm_progress_bar.setVisible(False)
        self.dtm_progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.dtm_layout.addWidget(self.dtm_progress_bar)
        self.dtm_log_output = QTextEdit()
        self.dtm_log_output.setReadOnly(True)
        self.dtm_log_output.setMinimumHeight(100)
        self.dtm_layout.addWidget(QLabel('Log Output:'))
        self.dtm_layout.addWidget(self.dtm_log_output)
        self.dtm_tab.setLayout(self.dtm_layout)

        self.tabs.addTab(self.gf_tab, 'GroundFilter')
        self.tabs.addTab(self.dtm_tab, 'DTM Generation')
        self.tabs.addTab(self.lasinfo_tab, 'LAS Info')
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)
    def pick_dtm_output_file(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Select Output DTM', '', 'DTM Files (*.dtm);;All Files (*)')
        if path:
            self.dtm_out_edit.setText(path)
            save_setting('dtm_output_dtm', path)

        # ...existing code for tab and layout setup...
            self.dtm_out_edit.setText(path)
            save_setting('dtm_output_dtm', path)

    def pick_dtm_exe_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select GridSurfaceCreate.exe', '', 'Executables (*.exe)')
        if path:
            self.dtm_exe_edit.setText(path)
            save_setting('dtm_exe_path', path)

    def run_dtm_process(self):
        ground_las = self.dtm_ground_edit.text().strip()
        out_dtm = self.dtm_out_edit.text().strip()
        exe_path = self.dtm_exe_edit.text().strip()
        cell_size = self.dtm_cellsize_edit.value()
        # (units, utm_zone, datum are obsolete; use new CRS fields below)
        extra_params = self.dtm_extra_edit.text().strip()
        tif_checked = self.dtm_tif_checkbox.isChecked()
        tif_exe_path = self.dtm_tif_exe_edit.text().strip()
        # Get CRS parameters from widgets
        xyunits = self.dtm_xyunits_edit.text().strip() or 'M'
        zunits = self.dtm_zunits_edit.text().strip() or 'M'
        coordsys = self.dtm_coordsys_edit.value()
        zone = self.dtm_zone_edit.value()
        horizdatum = self.dtm_horizdatum_edit.value()
        vertdatum = self.dtm_vertdatum_edit.value()
        # Save settings
        save_setting('dtm_ground_las', ground_las)
        save_setting('dtm_output_dtm', out_dtm)
        save_setting('dtm_exe_path', exe_path)
        save_setting('dtm_cell_size', str(cell_size))
        save_setting('dtm_xyunits', xyunits)
        save_setting('dtm_zunits', zunits)
        save_setting('dtm_coordsys', str(coordsys))
        save_setting('dtm_zone', str(zone))
        save_setting('dtm_horizdatum', str(horizdatum))
        save_setting('dtm_vertdatum', str(vertdatum))
        save_setting('dtm_extra', extra_params)
        save_setting('dtm_tif_checked', str(tif_checked))
        save_setting('dtm_tif_exe_path', tif_exe_path)
        # Check ground points file
        if not os.path.isfile(ground_las):
            QMessageBox.warning(self, 'Missing Input', f'Ground points LAS file not found: {ground_las}')
            self.dtm_log('Ground points LAS file not found: ' + ground_las)
            return
        if not exe_path or not os.path.isfile(exe_path):
            QMessageBox.warning(self, 'Missing Executable', f'GridSurfaceCreate.exe not found: {exe_path}')
            self.dtm_log('GridSurfaceCreate.exe not found: ' + exe_path)
            return
        if not out_dtm:
            QMessageBox.warning(self, 'Missing Output', 'Please specify an output DTM file.')
            self.dtm_log('No output DTM file specified.')
            return
        if tif_checked and (not tif_exe_path or not os.path.isfile(tif_exe_path)):
            QMessageBox.warning(self, 'Missing Executable', f'DTM2TIF.exe not found: {tif_exe_path}')
            self.dtm_log('DTM2TIF.exe not found: ' + tif_exe_path)
            return
        self.dtm_run_btn.setEnabled(False)
        self.dtm_progress_bar.setVisible(True)
        self.dtm_log('Starting DTM generation process...')
        # Get CRS parameters from widgets
        xyunits = self.dtm_xyunits_edit.text().strip() or 'M'
        zunits = self.dtm_zunits_edit.text().strip() or 'M'
        coordsys = self.dtm_coordsys_edit.value()
        zone = self.dtm_zone_edit.value()
        horizdatum = self.dtm_horizdatum_edit.value()
        vertdatum = self.dtm_vertdatum_edit.value()
        self.dtm_worker = DTMWorker(
            exe_path, ground_las, out_dtm, cell_size, xyunits, zunits, coordsys, zone, horizdatum, vertdatum, extra_params
        )
        self.dtm_worker.log_signal.connect(self.dtm_log)
        self.dtm_worker.finished_signal.connect(lambda success: self.on_dtm_worker_finished(success, tif_checked, tif_exe_path, out_dtm))
        self.dtm_worker.start()

    def dtm_log(self, msg):
        self.dtm_log_output.append(msg)
        print('[DTM]', msg)

    def on_dtm_worker_finished(self, success, tif_checked, tif_exe_path, out_dtm):
        if tif_checked and success:
            self.dtm_log('Starting DTM to TIFF conversion...')
            self.dtm_progress_bar.setVisible(True)
            self.tif_worker = TIFWorker(tif_exe_path, out_dtm)
            self.tif_worker.log_signal.connect(self.dtm_log)
            self.tif_worker.finished_signal.connect(self.on_tif_worker_finished)
            self.tif_worker.start()
        else:
            self.dtm_run_btn.setEnabled(True)
            self.dtm_progress_bar.setVisible(False)
            if success:
                self.dtm_log('DTM process finished successfully.')
            else:
                self.dtm_log('DTM process finished with errors.')

    def on_tif_worker_finished(self, success):
        self.dtm_run_btn.setEnabled(True)
        self.dtm_progress_bar.setVisible(False)
        if success:
            self.dtm_log('DTM to TIFF process finished successfully.')
        else:
            self.dtm_log('DTM to TIFF process finished with errors.')

    def _row(self, label, edit, btn):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(edit)
        if btn:
            row.addWidget(btn)
        return row

    def pick_input_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select Input LAS', '', 'LAS Files (*.las);;All Files (*)')
        if path:
            self.in_edit.setText(path)
            save_setting('input_las', path)

    def pick_output_file(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Select Output LAS', '', 'LAS Files (*.las);;All Files (*)')
        if path:
            self.out_edit.setText(path)
            save_setting('output_las', path)

    def pick_exe_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select GroundFilter.exe', '', 'Executables (*.exe)')
        if path:
            self.exe_edit.setText(path)
            save_setting('exe_path', path)

    def load_settings(self):
        # DTM tab - GeoTIFF
        self.dtm_tif_checkbox.setChecked(load_setting('dtm_tif_checked') == 'True')
        self.dtm_tif_exe_edit.setText(load_setting('dtm_tif_exe_path'))
        # GroundFilter tab
        self.in_edit.setText(load_setting('input_las'))
        self.out_edit.setText(load_setting('output_las'))
        self.exe_edit.setText(load_setting('exe_path'))
        try:
            self.cellsize_edit.setValue(float(load_setting('cell_size') or 10.0))
        except Exception:
            self.cellsize_edit.setValue(10.0)
        self.gparam_edit.setText(load_setting('gparam'))
        self.wparam_edit.setText(load_setting('wparam'))
        try:
            self.iter_edit.setValue(int(load_setting('iterations') or 8))
        except Exception:
            self.iter_edit.setValue(8)
        # DTM tab
        self.dtm_ground_edit.setText(load_setting('dtm_ground_las'))
        self.dtm_out_edit.setText(load_setting('dtm_output_dtm'))
        self.dtm_exe_edit.setText(load_setting('dtm_exe_path'))
        try:
            self.dtm_cellsize_edit.setValue(float(load_setting('dtm_cell_size') or 10.0))
        except Exception:
            self.dtm_cellsize_edit.setValue(10.0)
        self.dtm_xyunits_edit.setText(load_setting('dtm_xyunits') or 'M')
        self.dtm_zunits_edit.setText(load_setting('dtm_zunits') or 'M')
        try:
            self.dtm_coordsys_edit.setValue(int(load_setting('dtm_coordsys') or 1))
        except Exception:
            self.dtm_coordsys_edit.setValue(1)
        try:
            self.dtm_zone_edit.setValue(int(load_setting('dtm_zone') or 20))
        except Exception:
            self.dtm_zone_edit.setValue(20)
        try:
            self.dtm_horizdatum_edit.setValue(int(load_setting('dtm_horizdatum') or 2))
        except Exception:
            self.dtm_horizdatum_edit.setValue(2)
        try:
            self.dtm_vertdatum_edit.setValue(int(load_setting('dtm_vertdatum') or 2))
        except Exception:
            self.dtm_vertdatum_edit.setValue(2)
        self.dtm_extra_edit.setText(load_setting('dtm_extra'))
        # LAS Info tab
        if hasattr(self, 'lasinfo_las_edit'):
            self.lasinfo_las_edit.setText(load_setting('lasinfo_las_path'))
        if hasattr(self, 'lasinfo_exe_edit'):
            self.lasinfo_exe_edit.setText(load_setting('lasinfo_exe_path'))

    def log(self, msg):
        self.log_output.append(msg)
        print(msg)

    def run_process(self):
        in_path = self.in_edit.text().strip()
        out_path = self.out_edit.text().strip()
        exe_path = self.exe_edit.text().strip()
        cell_size = self.cellsize_edit.value()
        gparam = self.gparam_edit.text().strip()
        wparam = self.wparam_edit.text().strip()
        iterations = self.iter_edit.value()
        # Save settings
        save_setting('input_las', in_path)
        save_setting('output_las', out_path)
        save_setting('exe_path', exe_path)
        save_setting('cell_size', str(cell_size))
        save_setting('gparam', gparam)
        save_setting('wparam', wparam)
        save_setting('iterations', str(iterations))
        # Check input file
        if not os.path.isfile(in_path):
            QMessageBox.warning(self, 'Missing Input', f'Input LAS file not found: {in_path}')
            self.log(f'Input LAS file not found: {in_path}')
            return
        if not exe_path or not os.path.isfile(exe_path):
            QMessageBox.warning(self, 'Missing Executable', f'GroundFilter.exe not found: {exe_path}')
            self.log(f'GroundFilter.exe not found: {exe_path}')
            return
        if not out_path:
            QMessageBox.warning(self, 'Missing Output', 'Please specify an output LAS file.')
            self.log('No output LAS file specified.')
            return
        # Disable run button and show progress bar
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log('Starting GroundFilter process...')
        # Start worker thread
        self.worker = GroundFilterWorker(
            exe_path, in_path, out_path, cell_size, gparam, wparam, iterations
        )
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.start()

    def on_worker_finished(self, success):
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if success:
            self.log('Process finished successfully.')
        else:
            self.log('Process finished with errors.')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = GroundFilterApp()
    win.show()
    sys.exit(app.exec_())

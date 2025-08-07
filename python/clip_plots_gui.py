import sys
import shapefile  # pyshp
import os
import sqlite3
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox
)

def get_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_settings.db')

def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    conn.commit()
    conn.close()

def save_setting(key, value):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def load_setting(key):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key=?', (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ''

class ClipPlotsApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Clip Plots - PolyClipData GUI')
        self.resize(600, 300)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        # PolyClipData.exe
        self.exe_edit = QLineEdit()
        exe_btn = QPushButton('Browse...')
        exe_btn.clicked.connect(self.pick_exe)
        layout.addLayout(self._row('PolyClipData.exe:', self.exe_edit, exe_btn))
        # Shapefile
        self.shp_edit = QLineEdit()
        shp_btn = QPushButton('Browse...')
        shp_btn.clicked.connect(self.pick_shapefile)
        layout.addLayout(self._row('Shapefile:', self.shp_edit, shp_btn))
        from PySide6.QtWidgets import QComboBox, QCheckBox
        # Checkbox for multifile
        self.multifile_checkbox = QCheckBox('Save as multiple files (one per polygon)')
        self.multifile_checkbox.setChecked(True)
        self.multifile_checkbox.stateChanged.connect(self._on_multifile_changed)
        layout.addWidget(self.multifile_checkbox)
        # Field selection (dropdown)
        self.field_combo = QComboBox()
        self.field_combo.setEnabled(False)
        layout.addLayout(self._row('Field for Output:', self.field_combo, QLabel('')))
        # LAS input file
        self.las_edit = QLineEdit()
        las_btn = QPushButton('Browse...')
        las_btn.clicked.connect(self.pick_las_file)
        layout.addLayout(self._row('LAS File:', self.las_edit, las_btn))
        # Output prefix
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText('clipped')
        layout.addLayout(self._row('Output Prefix:', self.prefix_edit, QLabel('')))
        # Output folder
        self.out_edit = QLineEdit()
        out_btn = QPushButton('Browse...')
        out_btn.clicked.connect(self.pick_out_folder)
        layout.addLayout(self._row('Output Folder:', self.out_edit, out_btn))
        # Run button
        run_btn = QPushButton('Run PolyClipData')
        run_btn.clicked.connect(self.run_polyclip)
        layout.addWidget(run_btn)
        # Log output
        from PySide6.QtWidgets import QTextEdit
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(120)
        layout.addWidget(QLabel('PolyClipData Log:'))
        layout.addWidget(self.log_output)
        self.setLayout(layout)

    def _on_multifile_changed(self):
        # Enable field selection only if multifile is checked
        self.field_combo.setEnabled(self.multifile_checkbox.isChecked())

    def _row(self, label, edit, btn):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(edit)
        row.addWidget(btn)
        return row

    def pick_exe(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select PolyClipData.exe', '', 'Executables (*.exe)')
        if path:
            self.exe_edit.setText(path)
            save_setting('exe', path)

    def pick_shapefile(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select Shapefile', '', 'Shapefiles (*.shp)')
        if path:
            self.shp_edit.setText(path)
            save_setting('shapefile', path)
            # Read fields from shapefile
            try:
                sf = shapefile.Reader(path)
                fields = [f[0] for f in sf.fields[1:]]  # skip DeletionFlag
                self.field_combo.clear()
                self.field_combo.addItems(fields)
                self.field_combo.setEnabled(True)
            except Exception as e:
                print('[ERROR] Could not read shapefile fields:', e)
                self.field_combo.clear()
                self.field_combo.setEnabled(False)

    def pick_las_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select LAS File', '', 'LAS Files (*.las)')
        if path:
            self.las_edit.setText(path)
            save_setting('las_file', path)

    def pick_out_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if path:
            self.out_edit.setText(path)
            save_setting('out_folder', path)

    def load_settings(self):
        self.exe_edit.setText(load_setting('exe'))
        self.shp_edit.setText(load_setting('shapefile'))
        self.las_edit.setText(load_setting('las_file'))
        self.out_edit.setText(load_setting('out_folder'))
        # Try to load fields if shapefile is set
        shp_path = self.shp_edit.text().strip()
        if shp_path and os.path.isfile(shp_path):
            try:
                sf = shapefile.Reader(shp_path)
                fields = [f[0] for f in sf.fields[1:]]
                self.field_combo.clear()
                self.field_combo.addItems(fields)
                self.field_combo.setEnabled(self.multifile_checkbox.isChecked())
            except Exception as e:
                print('[ERROR] Could not read shapefile fields:', e)
                self.field_combo.clear()
                self.field_combo.setEnabled(False)
        else:
            self.field_combo.clear()
            self.field_combo.setEnabled(False)

    def run_polyclip(self):
        from PySide6.QtCore import QProcess
        exe = self.exe_edit.text().strip()
        shp = self.shp_edit.text().strip()
        las_file = self.las_edit.text().strip()
        out_dir = self.out_edit.text().strip()
        multifile = self.multifile_checkbox.isChecked()
        field_idx = self.field_combo.currentIndex() + 1 if multifile and self.field_combo.isEnabled() else None
        prefix = self.prefix_edit.text().strip() or 'clipped'
        if not all([exe, shp, las_file, out_dir]):
            msg = 'Please select all paths.'
            print('[ERROR]', msg)
            QMessageBox.warning(self, 'Missing Info', msg)
            return
        if multifile and (field_idx is None or field_idx < 1):
            msg = 'Please select a field for multifile output.'
            print('[ERROR]', msg)
            QMessageBox.warning(self, 'Missing Info', msg)
            return
        if not os.path.isfile(las_file):
            msg = 'Selected LAS file does not exist.'
            print('[ERROR]', msg)
            QMessageBox.warning(self, 'No LAS File', msg)
            return
        if multifile:
            out_base = os.path.join(out_dir, prefix)
            # Get field values for renaming after process
            try:
                sf = shapefile.Reader(shp)
                field_name = self.field_combo.currentText()
                field_values = [str(rec[sf.fields[1:].index([f for f in sf.fields[1:] if f[0]==field_name][0])]) for rec in sf.records()]
            except Exception as e:
                print('[ERROR] Could not read field values:', e)
                QMessageBox.warning(self, 'Error', f'Could not read field values: {e}')
                return
            self._pending_rename = (out_base, field_values, prefix)
            cmd = [exe, '/verbose', '/multifile', f'/shape:{field_idx},*', shp, out_base, las_file]
        else:
            las_base = os.path.basename(las_file)
            out_file = os.path.join(out_dir, f'{prefix}_{las_base}')
            self._pending_rename = None
            cmd = [exe, '/verbose', shp, out_file, las_file]
        self.log_output.clear()
        self.log_output.append('[DEBUG] Running command: ' + ' '.join(cmd))
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_process_output)
        self.process.readyReadStandardError.connect(self._on_process_output)
        self.process.finished.connect(self._on_process_finished)
        self.process.start(cmd[0], cmd[1:])

    def _on_process_output(self):
        from PySide6.QtWidgets import QApplication
        data = self.process.readAllStandardOutput().data().decode(errors='replace')
        if data:
            self.log_output.moveCursor(self.log_output.textCursor().End)
            self.log_output.insertPlainText(data)
            self.log_output.moveCursor(self.log_output.textCursor().End)
            QApplication.processEvents()  # Force GUI update

    def _on_process_finished(self, exitCode, exitStatus):
        import glob
        import shutil
        if exitCode == 0:
            # If multifile, rename output files to use prefix + field values
            if getattr(self, '_pending_rename', None):
                out_base, field_values, prefix = self._pending_rename
                las_files = sorted(glob.glob(os.path.join(out_base + '*')))
                if len(las_files) == len(field_values):
                    for src, val in zip(las_files, field_values):
                        ext = os.path.splitext(src)[1]
                        dst = os.path.join(os.path.dirname(src), f'{prefix}_{val}{ext}')
                        try:
                            shutil.move(src, dst)
                        except Exception as e:
                            self.log_output.append(f'\n[WARN] Could not rename {src} to {dst}: {e}')
                else:
                    self.log_output.append(f'\n[WARN] Output file count does not match field value count.')
            self.log_output.append('\n[SUCCESS] PolyClipData completed successfully.')
            QMessageBox.information(self, 'Done', 'PolyClipData completed successfully.')
        else:
            self.log_output.append(f'\n[ERROR] PolyClipData failed with exit code {exitCode}.')
            QMessageBox.warning(self, 'Error', f'PolyClipData failed with exit code {exitCode}.')

if __name__ == '__main__':
    init_db()
    app = QApplication(sys.argv)
    win = ClipPlotsApp()
    win.show()
    sys.exit(app.exec_())

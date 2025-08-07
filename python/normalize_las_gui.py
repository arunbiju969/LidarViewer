import sys
import os
import re
import sqlite3
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit, QListWidget, QMessageBox
)

def get_db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_settings.db')

def ns_key(key):
    return f'normalize_las_gui:{key}'

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

class NormalizeLasApp(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('LAS Rename & Normalize GUI')
        self.resize(700, 500)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        # Input folder
        self.in_edit = QLineEdit()
        in_btn = QPushButton('Browse...')
        in_btn.clicked.connect(self.pick_input_folder)
        layout.addLayout(self._row('Input Folder:', self.in_edit, in_btn))
        # Output folder
        self.out_edit = QLineEdit()
        out_btn = QPushButton('Browse...')
        out_btn.clicked.connect(self.pick_output_folder)
        layout.addLayout(self._row('Output Folder:', self.out_edit, out_btn))
        # Ground DTM file
        self.ground_edit = QLineEdit()
        ground_btn = QPushButton('Browse...')
        ground_btn.clicked.connect(self.pick_ground_file)
        layout.addLayout(self._row('Ground DTM:', self.ground_edit, ground_btn))
        # clipdata64.exe
        self.clipdata_edit = QLineEdit()
        clipdata_btn = QPushButton('Browse...')
        clipdata_btn.clicked.connect(self.pick_clipdata)
        layout.addLayout(self._row('clipdata64.exe:', self.clipdata_edit, clipdata_btn))
        # lasinfo64.exe
        self.lasinfo_edit = QLineEdit()
        lasinfo_btn = QPushButton('Browse...')
        lasinfo_btn.clicked.connect(self.pick_lasinfo)
        layout.addLayout(self._row('lasinfo64.exe:', self.lasinfo_edit, lasinfo_btn))
        # File list
        self.file_list = QListWidget()
        layout.addWidget(QLabel('LAS Files to Process:'))
        layout.addWidget(self.file_list)
        # Run button
        run_btn = QPushButton('Normalize LAS Files')
        run_btn.clicked.connect(self.run_process)
        layout.addWidget(run_btn)
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(120)
        layout.addWidget(QLabel('Log Output:'))
        layout.addWidget(self.log_output)
        self.setLayout(layout)

    def pick_ground_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select Ground DTM', '', 'DTM Files (*.dtm);;All Files (*)')
        if path:
            self.ground_edit.setText(path)
            save_setting('ground_dtm', path)
    def log(self, msg):
        self.log_output.append(msg)
        print(msg)

    def _row(self, label, edit, btn):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(edit)
        row.addWidget(btn)
        return row

    def pick_input_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Select Input Folder')
        if path:
            self.in_edit.setText(path)
            save_setting('las_input_folder', path)
            self.refresh_file_list()

    def pick_output_folder(self):
        path = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if path:
            self.out_edit.setText(path)
            save_setting('las_output_folder', path)

    def pick_clipdata(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select clipdata64.exe', '', 'Executables (*.exe)')
        if path:
            self.clipdata_edit.setText(path)
            save_setting('clipdata_path', path)

    def pick_lasinfo(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Select lasinfo64.exe', '', 'Executables (*.exe)')
        if path:
            self.lasinfo_edit.setText(path)
            save_setting('lasinfo_path', path)

    def load_settings(self):
        self.in_edit.setText(load_setting('las_input_folder'))
        self.out_edit.setText(load_setting('las_output_folder'))
        self.clipdata_edit.setText(load_setting('clipdata_path'))
        self.lasinfo_edit.setText(load_setting('lasinfo_path'))
        self.ground_edit.setText(load_setting('ground_dtm'))
        self.refresh_file_list()

    def refresh_file_list(self):
        self.file_list.clear()
        folder = self.in_edit.text().strip()
        if folder and os.path.isdir(folder):
            files = [f for f in os.listdir(folder) if f.lower().endswith('.las')]
            self.file_list.addItems(files)

    def run_process(self):
        import subprocess
        import json
        in_dir = self.in_edit.text().strip()
        out_dir = self.out_edit.text().strip()
        clipdata_path = self.clipdata_edit.text().strip()
        lasinfo_path = self.lasinfo_edit.text().strip()
        if not all([in_dir, out_dir, clipdata_path, lasinfo_path]):
            QMessageBox.warning(self, 'Missing Info', 'Please select all required paths.')
            return
        if not os.path.isdir(in_dir) or not os.path.isdir(out_dir):
            QMessageBox.warning(self, 'Invalid Folder', 'Input or output folder does not exist.')
            return
        las_files = [f for f in os.listdir(in_dir) if f.lower().endswith('.las')]
        self.log(f'LAS files to be normalized: {las_files}')
        # Prepare normalized output folder
        normalized_dir = os.path.join(out_dir, 'normalized')
        if not os.path.exists(normalized_dir):
            os.makedirs(normalized_dir)
        ground_dtm = self.ground_edit.text().strip()
        if not ground_dtm or not os.path.isfile(ground_dtm):
            QMessageBox.warning(self, 'Missing Ground DTM', 'Please select a valid ground DTM file.')
            return
        # Process each LAS file
        for las_name in las_files:
            las_path = os.path.join(in_dir, las_name)
            base, ext = os.path.splitext(las_name)
            out_name = f'{base}_normalized{ext}'
            out_path = os.path.join(normalized_dir, out_name)
            self.log(f'---')
            self.log(f'Preparing to normalize: {las_name}')
            self.log(f'  LAS path: {las_path} Exists: {os.path.exists(las_path)}')
            self.log(f'  Output path: {out_path} Will be created in: {os.path.dirname(out_path)}')
            self.log(f'  Ground DTM path: {ground_dtm} Exists: {os.path.exists(ground_dtm)}')
            self.log(f'  ClipData path: {clipdata_path} Exists: {os.path.exists(clipdata_path)}')
            self.log(f'  lasinfo64 path: {lasinfo_path} Exists: {os.path.exists(lasinfo_path)}')
            # Get bounding box using lasinfo64.exe
            lasinfo_cmd = [lasinfo_path, '-i', las_path, '-json']
            self.log(f'  Running lasinfo64.exe command: {" ".join(lasinfo_cmd)}')
            lasinfo_result = subprocess.run(lasinfo_cmd, shell=True, capture_output=True, text=True)
            self.log(f'  lasinfo64.exe Return code: {lasinfo_result.returncode}')
            min_x = min_y = max_x = max_y = None
            try:
                info = json.loads(lasinfo_result.stderr)
                header = info['lasinfo'][0]['las_header_entries']
                min_x = str(header['min']['x'])
                min_y = str(header['min']['y'])
                max_x = str(header['max']['x'])
                max_y = str(header['max']['y'])
                self.log(f'  Extracted bounding box: min_x={min_x}, min_y={min_y}, max_x={max_x}, max_y={max_y}')
            except Exception as e:
                self.log(f'Error parsing JSON output from lasinfo64.exe for {las_name}: {e}')
                self.log(f'lasinfo64.exe STDERR: {lasinfo_result.stderr}')
                self.log(f'lasinfo64.exe STDOUT: {lasinfo_result.stdout}')
            if not all([min_x, min_y, max_x, max_y]):
                self.log(f'Could not extract bounding box for {las_name}. Skipping.')
                continue
            self.log(f'  Bounding box: {min_x} {min_y} {max_x} {max_y}')
            # Run clipdata64.exe with bounding box
            cmd = [clipdata_path, '/height', f'/dtm:{ground_dtm}', las_path, out_path, min_x, min_y, max_x, max_y]
            self.log(f'  Running clipdata64.exe command: {" ".join(cmd)}')
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            self.log(f'  clipdata64.exe STDOUT: {result.stdout[:500]}')
            self.log(f'  clipdata64.exe STDERR: {result.stderr}')
            self.log(f'  clipdata64.exe Return code: {result.returncode}')
            if result.returncode != 0:
                self.log(f'ClipData failed for {las_name} with error code {result.returncode}.')
            # Check if output file was created
            if os.path.exists(out_path):
                self.log(f'  Output file created: {out_path}')
            else:
                self.log(f'  Output file NOT created: {out_path}')
        self.log('All files renamed and normalized.')
        # Verify LAS files in normalized directory
        self.log('Verifying LAS files in normalized directory using lasinfo64.exe...')
        for fname in os.listdir(normalized_dir):
            fpath = os.path.join(normalized_dir, fname)
            if not fname.lower().endswith('.las'):
                self.log(f'Skipping non-LAS file: {fname}')
                continue
            lasinfo_cmd = [lasinfo_path, '-i', fpath]
            self.log(f'Running lasinfo64.exe on {fname}...')
            result = subprocess.run(lasinfo_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.log(f'Valid LAS file: {fname}\n{result.stdout[:500]}')
            else:
                self.log(f'Invalid LAS file: {fname} | Return code: {result.returncode}')
                self.log(f'lasinfo64.exe STDERR: {result.stderr}')
        self.log('LAS file verification complete.')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = NormalizeLasApp()
    win.show()
    sys.exit(app.exec_())

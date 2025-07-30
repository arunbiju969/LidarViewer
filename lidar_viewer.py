import pyvista as pv
import numpy as np
import os
import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QGroupBox, QFormLayout, QComboBox
)
from splash.splash_loader import create_splash
from PySide6.QtCore import Qt
from pyvistaqt import QtInteractor



from sidebar.sidebar_widget import SidebarWidget
from viewer.pointcloud_viewer import PointCloudViewer
from fileio.las_loader import load_las_file, save_last_file, load_last_file
from layers.layer_db import save_layer_settings, load_layer_settings, generate_layer_id

print("[INFO] Starting lidar_viewer.py")
class MainWindow(QMainWindow):
    def _on_point_size_changed(self, value):
        print(f"[DEBUG] Point size changed to: {value}")
        self.viewer.set_point_size(value)
        # Save to DB
        if hasattr(self, '_current_layer_id') and self._current_layer_id and hasattr(self, '_current_file_path') and self._current_file_path:
            print(f"[DB] Saving sidebar settings to DB for layer {self._current_layer_id}: {self._get_sidebar_settings()}")
            save_layer_settings(self._current_layer_id, self._current_file_path, self._get_sidebar_settings())
            # Reload settings from DB and apply
            settings = load_layer_settings(self._current_layer_id)
            print(f"[DB] Reloaded sidebar settings from DB after point size change for layer {self._current_layer_id}: {settings}")
            if settings:
                print(f"[PLOTTER] Redrawing plotter using DB values after point size change for layer {self._current_layer_id}")
                self._set_sidebar_settings(settings)
                self._on_color_by_changed()
        else:
            # Re-apply color mapping so color and point size are both respected
            self._on_color_by_changed()
    def _on_projection_changed(self, index=None):
        # 0: Parallel, 1: Perspective
        if hasattr(self.viewer, 'plotter') and hasattr(self.viewer.plotter, 'camera') and self.viewer.plotter.camera is not None:
            if self.sidebar.projection_box.currentIndex() == 0:
                self.viewer.plotter.camera.SetParallelProjection(True)
            else:
                self.viewer.plotter.camera.SetParallelProjection(False)
            self.viewer.plotter.update()
        else:
            print("[WARN] Viewer plotter or camera not available for projection update.")
    def show_metadata_dialog(self, text, title="LAS Metadata"):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit(dialog)
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        layout.addWidget(text_edit)
        btn_close = QPushButton("Close", dialog)
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)
        dialog.setLayout(layout)
        dialog.resize(800, 600)
        dialog.exec()
    def _on_custom_color_changed(self, *args, **kwargs):
        print(f"[DEBUG] _on_custom_color_changed called with args={args}, kwargs={kwargs}")
        current_text = self.sidebar.color_controls.colormap_box.currentText()
        print(f"[DEBUG] Dropdown before: '{current_text}'")
        if current_text != "Custom":
            idx = self.sidebar.color_controls.colormap_box.findText("Custom")
            print(f"[DEBUG] Index for 'Custom' in dropdown: {idx}")
            if idx != -1:
                print(f"[DEBUG] Setting colormap dropdown to 'Custom' (was '{current_text}')")
                self.sidebar.color_controls.colormap_box.setCurrentIndex(idx)
                print(f"[DEBUG] Dropdown after set: '{self.sidebar.color_controls.colormap_box.currentText()}'")
                print("[DEBUG] Forcing _on_color_by_changed after setting dropdown to 'Custom'")
                self._on_color_by_changed()
            else:
                print("[DEBUG] 'Custom' not found in dropdown options!")
        else:
            print("[DEBUG] Colormap already 'Custom', updating coloring now")
            self._on_color_by_changed()
    def _on_color_by_changed(self, index=None):
        import matplotlib.colors as mcolors
        import matplotlib.pyplot as plt
        from fileio.las_loader import get_normalized_scalars
        # Get the selected dimension name
        dim_name = self.sidebar.color_controls.dimension_box.currentText()
        colormap = self.sidebar.color_controls.colormap_box.currentText()
        # Defensive: skip if no file loaded or invalid selection
        if not hasattr(self, '_las') or dim_name not in self._las:
            self.viewer._colormap = colormap
            self.viewer.display_point_cloud(self._points)
            return
        # Use loader utility to get normalized scalars
        norm_scalars = get_normalized_scalars(self._las, dim_name)

        # Handle custom colormap
        if colormap == "Custom":
            # Get user-selected colors directly from the pickers for immediate update
            start = self.sidebar.color_controls.color_start
            mid = self.sidebar.color_controls.color_mid
            end = self.sidebar.color_controls.color_end
            print(f"[DEBUG] Custom color changed: start={start}, mid={mid}, end={end}")
            # Create a custom colormap
            cmap = mcolors.LinearSegmentedColormap.from_list(
                "custom_gradient", [start, mid, end]
            )
            self.viewer.display_point_cloud(self._points, scalars=norm_scalars, cmap=cmap)
        else:
            self.viewer._colormap = colormap
            self.viewer.display_point_cloud(self._points, scalars=norm_scalars)
        # Save current sidebar settings to DB for this layer
        if hasattr(self, '_current_layer_id') and self._current_layer_id and hasattr(self, '_current_file_path') and self._current_file_path:
            print(f"[DB] Saving sidebar settings to DB for layer {self._current_layer_id}: {self._get_sidebar_settings()}")
            save_layer_settings(self._current_layer_id, self._current_file_path, self._get_sidebar_settings())
            # Reload settings from DB and apply
            settings = load_layer_settings(self._current_layer_id)
            print(f"[DB] Reloaded sidebar settings from DB after color/colormap change for layer {self._current_layer_id}: {settings}")
            if settings:
                print(f"[PLOTTER] Redrawing plotter using DB values after color/colormap change for layer {self._current_layer_id}")
                self._set_sidebar_settings(settings)
                # Redraw plotter using DB settings (avoid infinite loop by not calling _on_color_by_changed again)
    SETTINGS_FILE = "settings.json"


    def __init__(self, las_data=None, default_file=None):
        print(f"[DEBUG] MainWindow.__init__ id(self)={id(self)}")
        print("[INFO] Initializing MainWindow UI...")
        super().__init__()
        self.setWindowTitle("LiDAR Point Cloud Viewer")

        self._layers = {}  # uuid -> dict with file_path, points, actor, visible
        self.sidebar = SidebarWidget()
        self.sidebar.setObjectName("sidebar")
        # Connect layer manager's layer_toggled signal to this window's handler
        self.sidebar.layer_manager.layer_toggled.connect(self._on_layer_toggled)
        # Menu bar style is now set in _update_theme() for theme support
        print(f"[DEBUG] SidebarWidget created: {self.sidebar}")
        # Set callback for custom color pickers
        self.sidebar.color_controls.on_custom_color_set = self._on_custom_color_changed
        # Set callback for point size slider
        self.sidebar.point_size_controls.on_point_size_changed = self._on_point_size_changed
        # Connect sidebar open file button to open_file
        self.sidebar.button.clicked.connect(self.open_file)
        self.viewer = PointCloudViewer()
        self.viewer.setObjectName("viewer")
        # Set initial point size in viewer (after viewer is created)
        self.viewer.set_point_size(self.sidebar.point_size_controls.get_point_size())
        print("[INFO] Sidebar and Viewer widgets created.")

        self._current_file_path = None  # Track currently loaded file
        self._current_layer_id = None   # Track currently loaded layer UUID
        self._metadata_action = None    # Reference to metadata menu action

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.viewer, stretch=1)
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        print("[INFO] Main layout and central widget set.")

        self._create_menu_bar()
        print("[INFO] Menu bar created.")

        # Set dark mode as default
        self.sidebar.theme_box.setCurrentText("Dark")
        self.sidebar.theme_box.currentIndexChanged.connect(self._update_theme)
        self._update_theme()
        self.viewer.set_theme("Dark")
        print("[INFO] Theme initialized.")

        # Connect color by and colormap dropdowns to coloring logic
        self.sidebar.color_controls.dimension_box.currentIndexChanged.connect(self._on_color_by_changed)
        self.sidebar.color_controls.colormap_box.currentIndexChanged.connect(self._on_color_by_changed)
        # Connect projection box to projection handler
        self.sidebar.projection_box.currentIndexChanged.connect(self._on_projection_changed)
        # Ensure projection is set at startup
        self._on_projection_changed()

        if las_data is not None and default_file is not None:
            from fileio.las_loader import load_point_cloud_data
            print(f"[INFO] Loading default file: {default_file}")
            data = load_point_cloud_data(default_file)
            self._las = data["las"]
            self._cloud = data["cloud"]
            self._points = data["points"]
            self.viewer.display_point_cloud(self._points)
            print(f"[INFO] Default file loaded: {default_file} ({self._points.shape[0]} points)")
            self.sidebar.set_status(f"Loaded: {os.path.basename(default_file)} ({self._points.shape[0]} points)")
            self.sidebar.update_file_info(os.path.basename(default_file), self._points.shape[0])
            self.sidebar.update_dimensions(data["dims"])
            self.sidebar.color_controls.dimension_box.currentIndexChanged.connect(self._on_color_by_changed)
            self.sidebar.color_controls.colormap_box.currentIndexChanged.connect(self._on_color_by_changed)
            self._current_file_path = default_file
            self._current_layer_id = generate_layer_id()
            if self._metadata_action:
                self._metadata_action.setEnabled(True)
            self._on_projection_changed()
            self._on_color_by_changed()
        else:
            print("[INFO] No default file loaded.")
            self.sidebar.set_status("No default file loaded.")
            self._current_file_path = None
            self._current_layer_id = None
            if self._metadata_action:
                self._metadata_action.setEnabled(False)



    def _update_theme(self):
        print(f"[INFO] Theme changed to: {self.sidebar.theme_box.currentText()}")
        theme = self.sidebar.theme_box.currentText()
        from theme.theme_manager import apply_theme
        self.viewer.set_theme(theme)
        # Delegate all theme and menu bar/menu style logic to theme_manager
        apply_theme(theme, main_window=self)
        # Redraw plotter if available
        if hasattr(self.viewer, 'plotter'):
            self.viewer.plotter.update()

    def _create_view_toolbar(self):
        from PySide6.QtWidgets import QToolBar
        from PySide6.QtGui import QAction
        toolbar = QToolBar("View Toolbar")
        self.addToolBar(toolbar)

        # Define view actions, now call viewer methods
        view_actions = [
            ("Top", self.viewer.set_top_view),
            ("Front", self.viewer.set_front_view),
            ("Left", self.viewer.set_left_view),
            ("Right", self.viewer.set_right_view),
            ("Bottom", self.viewer.set_bottom_view),
        ]
        for name, handler in view_actions:
            action = QAction(name, self)
            action.triggered.connect(handler)
            toolbar.addAction(action)


    def _update_projection(self):
        # 0: Parallel, 1: Perspective
        if hasattr(self.plotter, 'camera') and self.plotter.camera is not None:
            if self.projection_box.currentIndex() == 0:
                self.plotter.camera.SetParallelProjection(True)
            else:
                self.plotter.camera.SetParallelProjection(False)
            self.plotter.update()
        last_file = self._load_last_file()
        if last_file and os.path.exists(last_file):
            self.load_and_display(last_file)

    def _create_menu_bar(self):
        menubar = self.menuBar()
        # File menu
        file_menu = menubar.addMenu("File")
        open_action = file_menu.addAction("Open LAS/LAZ File...")
        open_action.triggered.connect(self.open_file)
        # Show LAS Metadata action
        metadata_action = file_menu.addAction("Show LAS Metadata")
        metadata_action.setEnabled(False)
        metadata_action.triggered.connect(self._show_las_metadata)
        self._metadata_action = metadata_action
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        # Import menu (placeholder for future import options)
        import_menu = menubar.addMenu("Import")
        import_las_action = import_menu.addAction("Import LAS/LAZ File...")
        import_las_action.triggered.connect(self.open_file)

    def _show_las_metadata(self):
        if self._current_file_path:
            from fileio.las_loader import get_las_metadata_summary
            print(f"[INFO] Showing LAS metadata for: {self._current_file_path}")
            summary = get_las_metadata_summary(self._current_file_path)
            self.show_metadata_dialog(summary)
        else:
            self.show_metadata_dialog("No LAS/LAZ file loaded. Cannot show metadata.", title="No File Loaded")

    def open_file(self):
        print("[INFO] User triggered file open dialog.")
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a LAS or LAZ file", "", "LAS/LAZ Files (*.las *.laz)")
        if file_path:
            print(f"[INFO] File selected: {file_path}")
            save_last_file(self.SETTINGS_FILE, file_path)
            self.load_and_display(file_path)

    def load_and_display(self, file_path):
        from fileio.las_loader import load_point_cloud_data
        print(f"[INFO] Loading and displaying file: {file_path}")
        self.sidebar.set_status(f"Loading: {os.path.basename(file_path)} ... Please wait.")
        QApplication.processEvents()
        try:
            print(f"[INFO] Started loading: {file_path}")
            data = load_point_cloud_data(file_path)
            print(f"[INFO] File loaded: {file_path}")
            self._las = data["las"]
            self._cloud = data["cloud"]
            self._points = data["points"]
            self._current_layer_id = generate_layer_id()
            self._current_file_path = file_path
            # Add to layers dict
            self._layers[self._current_layer_id] = {
                'file_path': file_path,
                'points': self._points,
                'visible': True,
                'actor': None  # Will be set below
            }
            settings = load_layer_settings(self._current_layer_id)
            if settings:
                print(f"[INFO] Loaded sidebar settings from DB for layer {self._current_layer_id}")
                self._set_sidebar_settings(settings)
            # Display all visible layers
            self._update_all_layers_in_viewer()
            print(f"[INFO] Point cloud displayed for file: {file_path}")
            self._on_projection_changed()
            self.viewer.plotter.add_axes()
            self.viewer.plotter.reset_camera()
            print(f"[INFO] File loaded and displayed: {file_path} ({self._points.shape[0]} points)")
            status_msg = f"Loaded: {os.path.basename(file_path)} ({self._points.shape[0]} points)"
            self.sidebar.update_file_info(os.path.basename(file_path), self._points.shape[0])
            self.sidebar.update_dimensions(data["dims"])
            self.sidebar.color_controls.dimension_box.currentIndexChanged.connect(self._on_color_by_changed)
            self.sidebar.color_controls.colormap_box.currentIndexChanged.connect(self._on_color_by_changed)
            if self._metadata_action:
                self._metadata_action.setEnabled(True)
            self._on_color_by_changed()
            save_layer_settings(self._current_layer_id, self._current_file_path, self._get_sidebar_settings())
            # Update the layer manager with all layers, checked state reflects visibility
            all_layers = [(uuid, l['file_path']) for uuid, l in self._layers.items()]
            checked_uuids = set(uuid for uuid, l in self._layers.items() if l['visible'])
            self.sidebar.update_layers(all_layers, current_uuid=self._current_layer_id, checked_uuids=checked_uuids)
        except Exception as e:
            print(f"[ERROR] Failed to load file: {file_path}: {e}")
            status_msg = f"Failed to load: {os.path.basename(file_path)}"
        finally:
            self.sidebar.set_status(status_msg)
            QApplication.processEvents()

    def _update_all_layers_in_viewer(self):
        print(f"[DEBUG] _update_all_layers_in_viewer: id(self)={id(self)}")
        # Remove all actors
        if hasattr(self.viewer, 'plotter'):
            print("[DEBUG] _update_all_layers_in_viewer: clearing plotter")
            self.viewer.plotter.clear()
        # Add all visible layers
        for uuid, layer in self._layers.items():
            if layer['visible']:
                # Add to plotter and store actor
                print("[DEBUG] _update_all_layers_in_viewer: adding visible layers")
                print(f"[DEBUG] Layer {uuid}: visible={layer['visible']}")
                print(f"[DEBUG] Calling display_point_cloud for layer {uuid}")
                actor = self.viewer.display_point_cloud(layer['points'], return_actor=True)
                self._layers[uuid]['actor'] = actor
            else:
                self._layers[uuid]['actor'] = None

    def _on_layer_toggled(self, uuid, checked):
        print(f"[DEBUG] _on_layer_toggled: id(self)={id(self)}, uuid={uuid}, checked={checked}")
        print(f"[DEBUG] _on_layer_toggled: self._layers.keys()={list(self._layers.keys())}")
        if uuid in self._layers:
            self._layers[uuid]['visible'] = checked
            try:
                if checked:
                    # Restore sidebar settings for this layer and update viewer
                    settings = load_layer_settings(uuid)
                    if settings:
                        print(f"[DEBUG] Restoring sidebar settings for layer {uuid}")
                        self._set_sidebar_settings(settings)
                    self._current_layer_id = uuid
                    self._current_file_path = self._layers[uuid]['file_path']
                    # Redraw plotter for this layer with restored settings
                    self._on_color_by_changed()
                else:
                    # Just update the plotter to remove the layer
                    print("[DEBUG] Toggling layer OFF, updating all layers in viewer")
                    self._update_all_layers_in_viewer()
            except Exception as e:
                print(f"[ERROR] Exception in _on_layer_toggled: {e}")
        else:
            print(f"[ERROR] UUID {uuid} not found in self._layers!")

    def _get_sidebar_settings(self):
        color_controls = self.sidebar.color_controls
        point_size_controls = self.sidebar.point_size_controls
        return {
            'dimension': color_controls.dimension_box.currentText(),
            'colormap': color_controls.colormap_box.currentText(),
            'color_start': getattr(color_controls, 'color_start', None),
            'color_mid': getattr(color_controls, 'color_mid', None),
            'color_end': getattr(color_controls, 'color_end', None),
            'point_size': point_size_controls.get_point_size() if hasattr(point_size_controls, 'get_point_size') else None,
        }

    def _set_sidebar_settings(self, settings):
        print(f"[DB->SIDEBAR] Applying settings from DB to sidebar: {settings}")
        color_controls = self.sidebar.color_controls
        point_size_controls = self.sidebar.point_size_controls
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



def main():
    print("[INFO] Application starting...")
    app = QApplication(sys.argv)
    print("[INFO] Initializing main window (no default file)...")
    window = MainWindow()
    window.show()
    from PySide6.QtCore import QTimer
    def show_and_raise():
        window.showMaximized()
        window.raise_()
        window.activateWindow()
    QTimer.singleShot(0, show_and_raise)
    print("[INFO] Main window shown. Application running.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

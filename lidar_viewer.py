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
    def plot_all_layers(self):
        """
        Central function to clear and redraw all visible layers in the plotter.
        Handles all point plotting, coloring, and point size updates.
        """
        print("[PLOTTER] plot_all_layers: clearing plotter and redrawing all visible layers")
        if hasattr(self.viewer, 'plotter'):
            self.viewer.plotter.clear()
        from fileio.las_loader import get_normalized_scalars
        for uuid, layer in self._layers.items():
            actor = layer.get('actor', None)
            if actor is not None and hasattr(self.viewer, 'plotter'):
                try:
                    self.viewer.plotter.remove_actor(actor)
                except Exception as e:
                    print(f"[WARN] Could not remove actor for layer {uuid}: {e}")
            if layer['visible']:
                settings = load_layer_settings(uuid)
                las = layer.get('las', None)
                dim_name = settings.get('dimension') if settings else None
                colormap = settings.get('colormap') if settings else None
                # Handle custom colormap
                if colormap == "Custom":
                    try:
                        from matplotlib.colors import LinearSegmentedColormap
                        color_start = settings.get('color_start', '#0000ff') or '#0000ff'
                        color_mid = settings.get('color_mid', '#00ff00') or '#00ff00'
                        color_end = settings.get('color_end', '#ff0000') or '#ff0000'
                        custom_cmap = LinearSegmentedColormap.from_list(
                            'custom_cmap', [color_start, color_mid, color_end]
                        )
                        colormap = custom_cmap
                    except Exception as e:
                        print(f"[WARN] Failed to create custom colormap, falling back to 'viridis': {e}")
                        colormap = 'viridis'
                scalars = None
                if las is not None and dim_name and dim_name in las:
                    scalars = get_normalized_scalars(las, dim_name)
                actor = self.viewer.display_point_cloud(
                    layer['points'],
                    scalars=scalars,
                    cmap=colormap,
                    return_actor=True,
                    show_scalar_bar=False
                )
                self._layers[uuid]['actor'] = actor
                point_size = settings.get('point_size') if settings else None
                if point_size is not None and hasattr(self.viewer, 'set_point_size'):
                    self.viewer.set_point_size(point_size, actor=actor)
        # Remove scalar bar/legend if present
        if hasattr(self.viewer, 'plotter'):
            try:
                self.viewer.plotter.remove_scalar_bar()
            except Exception as e:
                print(f"[WARN] Could not remove scalar bar: {e}")
            self.viewer.plotter.update()
        actors_present = {uuid: l['actor'] is not None for uuid, l in self._layers.items()}
        print(f"[PLOTTER] Actors present after plot_all_layers: {actors_present}")
    def _on_point_size_changed(self, value):
        print(f"[DEBUG] Point size changed to: {value}")
        # Always save to DB
        if hasattr(self, '_current_layer_id') and self._current_layer_id and hasattr(self, '_current_file_path') and self._current_file_path:
            print(f"[DB] Saving sidebar settings to DB for layer {self._current_layer_id}: {self._get_sidebar_settings()}")
            save_layer_settings(self._current_layer_id, self._current_file_path, self._get_sidebar_settings())
        # Only update the actor for the current layer
        if hasattr(self, '_current_layer_id') and self._current_layer_id in self._layers:
            actor = self._layers[self._current_layer_id].get('actor', None)
            if actor is not None and hasattr(self.viewer, 'set_point_size'):
                self.viewer.set_point_size(value, actor=actor)
                if hasattr(self.viewer, 'plotter'):
                    self.viewer.plotter.update()
            else:
                print(f"[WARN] No actor found for current layer {self._current_layer_id}, redrawing layer.")
                self._redraw_current_layer()

    def _redraw_current_layer(self):
        # Remove and re-add only the current layer's actor
        if not (hasattr(self, '_current_layer_id') and self._current_layer_id in self._layers):
            print("[WARN] _redraw_current_layer: No current layer to redraw.")
            return
        uuid = self._current_layer_id
        layer = self._layers[uuid]
        if hasattr(self.viewer, 'plotter'):
            actor = layer.get('actor', None)
            if actor is not None:
                try:
                    self.viewer.plotter.remove_actor(actor)
                except Exception as e:
                    print(f"[WARN] Could not remove actor for layer {uuid}: {e}")
        settings = load_layer_settings(uuid)
        las = layer.get('las', None)
        dim_name = settings.get('dimension') if settings else None
        colormap = settings.get('colormap') if settings else None
        point_size = settings.get('point_size') if settings else None
        scalars = None
        if las is not None and dim_name and dim_name in las:
            from fileio.las_loader import get_normalized_scalars
            scalars = get_normalized_scalars(las, dim_name)
        # Handle custom colormap
        if colormap == "Custom":
            try:
                from matplotlib.colors import LinearSegmentedColormap
                color_start = settings.get('color_start', '#0000ff') or '#0000ff'
                color_mid = settings.get('color_mid', '#00ff00') or '#00ff00'
                color_end = settings.get('color_end', '#ff0000') or '#ff0000'
                custom_cmap = LinearSegmentedColormap.from_list(
                    'custom_cmap', [color_start, color_mid, color_end]
                )
                colormap = custom_cmap
            except Exception as e:
                print(f"[WARN] Failed to create custom colormap, falling back to 'viridis': {e}")
                colormap = 'viridis'
        actor = self.viewer.display_point_cloud(
            layer['points'],
            scalars=scalars,
            cmap=colormap,
            return_actor=True,
            show_scalar_bar=False
        )
        self._layers[uuid]['actor'] = actor
        if point_size is not None and hasattr(self.viewer, 'set_point_size'):
            self.viewer.set_point_size(point_size, actor=actor)
        if hasattr(self.viewer, 'plotter'):
            self.viewer.plotter.update()
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
        print("[DEBUG] _on_color_by_changed called")
        # Always save to DB
        if hasattr(self, '_current_layer_id') and self._current_layer_id and hasattr(self, '_current_file_path') and self._current_file_path:
            print(f"[DB] Saving sidebar settings to DB for layer {self._current_layer_id}: {self._get_sidebar_settings()}")
            save_layer_settings(self._current_layer_id, self._current_file_path, self._get_sidebar_settings())
        # Only redraw the current layer
        self._redraw_current_layer()
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
        # Connect layer_selected signal to handler
        self.sidebar.layer_manager.layer_selected.connect(self._on_layer_selected)
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

        # Connect color by and colormap dropdowns to coloring logic (disconnect first to avoid duplicates)
        try:
            self.sidebar.color_controls.dimension_box.currentIndexChanged.disconnect()
        except Exception:
            pass
        try:
            self.sidebar.color_controls.colormap_box.currentIndexChanged.disconnect()
        except Exception:
            pass
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
            # Disconnect before reconnecting to avoid duplicate slot calls
            try:
                self.sidebar.color_controls.dimension_box.currentIndexChanged.disconnect()
            except Exception:
                pass
            try:
                self.sidebar.color_controls.colormap_box.currentIndexChanged.disconnect()
            except Exception:
                pass
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
    
    def _on_layer_selected(self, uuid):
        print(f"[DEBUG] _on_layer_selected called with uuid={uuid}")
        if uuid not in self._layers:
            print(f"[ERROR] _on_layer_selected: UUID {uuid} not found in self._layers!")
            return
        self._current_layer_id = uuid
        self._current_file_path = self._layers[uuid]['file_path']

        print(f"[DEBUG] Updated _current_layer_id: {self._current_layer_id}, _current_file_path: {self._current_file_path}")
        settings = load_layer_settings(uuid)

        print(f"[DEBUG] Loaded settings from DB for uuid={uuid}: {settings}")
        if settings:
            self._set_sidebar_settings(settings)
            print(f"[DEBUG] Applied settings to sidebar for uuid={uuid}")
        else:
            print(f"[WARN] No settings found in DB for uuid={uuid}")



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
            # Add to layers dict, now also store las per layer
            self._layers[self._current_layer_id] = {
                'file_path': file_path,
                'points': self._points,
                'las': self._las,
                'visible': True,
                'actor': None  # Will be set below
            }
            settings = load_layer_settings(self._current_layer_id)
            if settings:
                print(f"[INFO] Loaded sidebar settings from DB for layer {self._current_layer_id}")
                self._set_sidebar_settings(settings)
            # Display all visible layers using the unified plotter
            self.plot_all_layers()
            print(f"[INFO] Point cloud displayed for file: {file_path}")
            self._on_projection_changed()
            self.viewer.plotter.add_axes()
            self.viewer.plotter.reset_camera()
            print(f"[INFO] File loaded and displayed: {file_path} ({self._points.shape[0]} points)")
            status_msg = f"Loaded: {os.path.basename(file_path)} ({self._points.shape[0]} points)"
            self.sidebar.update_file_info(os.path.basename(file_path), self._points.shape[0])
            self.sidebar.update_dimensions(data["dims"])
            # Disconnect before reconnecting to avoid duplicate slot calls
            try:
                self.sidebar.color_controls.dimension_box.currentIndexChanged.disconnect()
            except Exception:
                pass
            try:
                self.sidebar.color_controls.colormap_box.currentIndexChanged.disconnect()
            except Exception:
                pass
            self.sidebar.color_controls.dimension_box.currentIndexChanged.connect(self._on_color_by_changed)
            self.sidebar.color_controls.colormap_box.currentIndexChanged.connect(self._on_color_by_changed)
            if self._metadata_action:
                self._metadata_action.setEnabled(True)
            self.plot_all_layers()
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
        # Deprecated: replaced by plot_all_layers()
        print("[DEBUG] _update_all_layers_in_viewer is deprecated. Use plot_all_layers instead.")
        self.plot_all_layers()

    def _on_layer_toggled(self, uuid, checked):
        print(f"[DEBUG] _on_layer_toggled: id(self)={id(self)}, uuid={uuid}, checked={checked}")
        print(f"[DEBUG] _on_layer_toggled: self._layers.keys()={list(self._layers.keys())}")
        if uuid in self._layers:
            self._layers[uuid]['visible'] = checked
            try:
                # Always update the plotter to show all visible layers
                self._update_all_layers_in_viewer()
                if checked:
                    # Restore sidebar settings for this layer (active layer logic)
                    settings = load_layer_settings(uuid)
                    if settings:
                        print(f"[DEBUG] Restoring sidebar settings for layer {uuid}")
                        self._set_sidebar_settings(settings)
                    self._current_layer_id = uuid
                    self._current_file_path = self._layers[uuid]['file_path']
                else:
                    print("[DEBUG] Toggling layer OFF, updated all layers in viewer")
                    # Optionally, update sidebar to next visible layer if only one remains
                    visible_uuids = [u for u, l in self._layers.items() if l['visible']]
                    if len(visible_uuids) == 1:
                        next_uuid = visible_uuids[0]
                        print(f"[DEBUG] Restoring sidebar settings for only remaining visible layer {next_uuid}")
                        settings = load_layer_settings(next_uuid)
                        if settings:
                            self._set_sidebar_settings(settings)
                            self._current_layer_id = next_uuid
                            self._current_file_path = self._layers[next_uuid]['file_path']
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
        # Block signals for all widgets while updating
        widgets = [
            color_controls.dimension_box,
            color_controls.colormap_box,
            getattr(point_size_controls, 'slider', None),
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
        finally:
            for w in widgets:
                if w is not None:
                    w.blockSignals(False)

        # After applying sidebar settings, update the plotter's actor point size and force redraw
        point_size = settings.get('point_size', None)
        actor = None
        if hasattr(self, '_current_layer_id') and self._current_layer_id in self._layers:
            actor = self._layers[self._current_layer_id].get('actor', None)
        if point_size is not None and actor is not None and hasattr(self.viewer, 'set_point_size'):
            print(f"[DEBUG] Forcing plotter to update actor id={id(actor)} to point size: {point_size} after DB->sidebar sync")
            self.viewer.set_point_size(point_size, actor=actor)
            if hasattr(self.viewer, 'plotter'):
                self.viewer.plotter.update()
        print("[DEBUG] Sidebar settings applied from DB and plotter updated.")



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

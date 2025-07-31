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
    def _create_view_toolbar(self):
        from viewer.view_toolbar import ViewToolbar
        toolbar = ViewToolbar(self.viewer, parent=self)
        self.addToolBar(toolbar)
    def _show_bounding_box_for_current_layer(self):
        """
        Display a bounding box for the currently selected layer in the viewer.
        Removes any previous bounding box actor.
        """
        import pyvista as pv
        current_layer_id = self.layer_manager.get_current_layer_id()
        if not (current_layer_id and current_layer_id in self.layer_manager.layers):
            return
        layer = self.layer_manager.layers[current_layer_id]
        points = layer.get('points', None)
        if points is None or points.shape[0] == 0:
            return
        # Remove previous bounding box actor if present
        if hasattr(self, '_bbox_actor') and self._bbox_actor is not None:
            try:
                self.viewer.plotter.remove_actor(self._bbox_actor)
            except Exception:
                pass
            self._bbox_actor = None
        # Compute bounds: (xmin, xmax, ymin, ymax, zmin, zmax)
        xmin, ymin, zmin = points.min(axis=0)
        xmax, ymax, zmax = points.max(axis=0)
        bounds = (xmin, xmax, ymin, ymax, zmin, zmax)
        # Create a box mesh for the bounds
        box = pv.Box(bounds)
        # Add the box mesh to the plotter
        self._bbox_actor = self.viewer.plotter.add_mesh(
            box, color='red', opacity=0.3, style='wireframe', line_width=2, name='bounding_box', pickable=False
        )
        self.viewer.plotter.update()

    def plot_all_layers(self):
        self.layer_manager.plot_all_layers(self.viewer, self.sidebar)
    def _on_point_size_changed(self, value):
        print(f"[DEBUG] Point size changed to: {value}")
        # Always save to DB
        current_layer_id = self.layer_manager.get_current_layer_id()
        current_file_path = self.layer_manager.get_current_file_path()
        if current_layer_id and current_file_path:
            print(f"[DB] Saving sidebar settings to DB for layer {current_layer_id}: {self.sidebar.get_sidebar_settings()}")
            save_layer_settings(current_layer_id, current_file_path, self.sidebar.get_sidebar_settings())
        # Only update the actor for the current layer
        if current_layer_id in self.layer_manager.layers:
            actor = self.layer_manager.layers[current_layer_id].get('actor', None)
            if actor is not None and hasattr(self.viewer, 'set_point_size'):
                self.viewer.set_point_size(value, actor=actor)
                if hasattr(self.viewer, 'plotter'):
                    self.viewer.plotter.update()
            else:
                print(f"[WARN] No actor found for current layer {current_layer_id}, redrawing layer.")
                self._redraw_current_layer()

    def _redraw_current_layer(self):
        self.layer_manager.redraw_current_layer(self.viewer)
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
        current_layer_id = self.layer_manager.get_current_layer_id()
        current_file_path = self.layer_manager.get_current_file_path()
        if current_layer_id and current_file_path:
            print(f"[DB] Saving sidebar settings to DB for layer {current_layer_id}: {self.sidebar.get_sidebar_settings()}")
            save_layer_settings(current_layer_id, current_file_path, self.sidebar.get_sidebar_settings())
        # Only redraw the current layer
        self._redraw_current_layer()
    SETTINGS_FILE = "settings.json"


    def __init__(self, las_data=None, default_file=None):
        print(f"[DEBUG] MainWindow.__init__ id(self)={id(self)}")
        print("[INFO] Initializing MainWindow UI...")
        super().__init__()
        self.setWindowTitle("LiDAR Point Cloud Viewer")

        from layers.layer_db import LayerManager
        self.layer_manager = LayerManager()
        self.sidebar = SidebarWidget()
        self.sidebar.setObjectName("sidebar")
        # Connect layer manager's layer_toggled signal to this window's handler
        self.sidebar.layer_manager.layer_toggled.connect(self._on_layer_toggled)
        # Connect layer_selected signal to handler
        self.sidebar.layer_manager.layer_selected.connect(self._on_layer_selected)
        # Connect add/remove signals to actual logic
        self.sidebar.layer_manager.layer_added.connect(self._on_layer_added)
        self.sidebar.layer_manager.layer_removed.connect(self._on_layer_removed_debug)
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
        # self._current_file_path and self._current_layer_id are now managed by LayerManager
        self._metadata_action = None    # Reference to metadata menu action
        from viewer.view_toolbar import ViewToolbar
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.sidebar)
        # Create a vertical layout for toolbar + viewer
        viewer_vlayout = QVBoxLayout()
        self.view_toolbar = ViewToolbar(self.viewer, parent=self)
        # Add toolbar with alignment left, no stretch
        viewer_vlayout.addWidget(self.view_toolbar, alignment=Qt.AlignLeft)
        viewer_vlayout.addWidget(self.viewer, stretch=1)
        main_layout.addLayout(viewer_vlayout, stretch=1)
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
            self.layer_manager.set_current_layer(generate_layer_id(), file_path=default_file)
            if self._metadata_action:
                self._metadata_action.setEnabled(True)
            self._on_projection_changed()
            self._on_color_by_changed()
        else:
            print("[INFO] No default file loaded.")
            self.sidebar.set_status("No default file loaded.")
            self.layer_manager.set_current_layer(None)
            if self._metadata_action:
                self._metadata_action.setEnabled(False)
    
    def _on_layer_selected(self, uuid):
        print(f"[DEBUG] _on_layer_selected called with uuid={uuid}")
        if uuid not in self.layer_manager.layers:
            print(f"[ERROR] _on_layer_selected: UUID {uuid} not found in self.layer_manager.layers!")
            return
        self.layer_manager.set_current_layer(uuid)
        print(f"[DEBUG] Updated _current_layer_id: {self.layer_manager.get_current_layer_id()}, _current_file_path: {self.layer_manager.get_current_file_path()}")
        settings = load_layer_settings(uuid)

        print(f"[DEBUG] Loaded settings from DB for uuid={uuid}: {settings}")
        if settings:
            self.sidebar.set_sidebar_settings(settings)
            print(f"[DEBUG] Applied settings to sidebar for uuid={uuid}")
        else:
            print(f"[WARN] No settings found in DB for uuid={uuid}")

        # Show bounding box for the selected layer
        self._show_bounding_box_for_current_layer()
    

    def _on_layer_added(self):
        print("[DEBUG] _on_layer_added: Add button pressed, opening file dialog...")
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a LAS or LAZ file to add as a new layer", "", "LAS/LAZ Files (*.las *.laz)")
        if not file_path:
            print("[DEBUG] _on_layer_added: No file selected.")
            return
        print(f"[DEBUG] _on_layer_added: File selected: {file_path}")
        from fileio.las_loader import load_point_cloud_data
        try:
            data = load_point_cloud_data(file_path)
            points = data["points"]
            las = data["las"]
            cloud = data["cloud"]
            uuid = generate_layer_id()
            self.layer_manager.add_layer(uuid, file_path, points, las, visible=True, actor=None)
            # Save and apply default sidebar settings for new layer
            default_settings = self.sidebar.get_sidebar_settings()
            save_layer_settings(uuid, file_path, default_settings)
            self.sidebar.set_sidebar_settings(default_settings)
            # Update sidebar and plotter
            self.plot_all_layers()
            # After actor is created, re-apply sidebar settings to ensure plotter updates new actor
            self.sidebar.set_sidebar_settings(default_settings)
            # Ensure plotter camera and axes are updated for new layer
            if hasattr(self.viewer, 'plotter'):
                try:
                    self.viewer.plotter.add_axes()
                except Exception as e:
                    print(f"[WARN] Could not add axes: {e}")
                try:
                    self.viewer.plotter.reset_camera()
                except Exception as e:
                    print(f"[WARN] Could not reset camera: {e}")
            all_layers = [(u, l['file_path']) for u, l in self.layer_manager.layers.items()]
            checked_uuids = set(u for u, l in self.layer_manager.layers.items() if l['visible'])
            self.sidebar.update_layers(all_layers, current_uuid=uuid, checked_uuids=checked_uuids)
            self.sidebar.set_status(f"Added: {os.path.basename(file_path)} ({points.shape[0]} points)")
            self.sidebar.update_file_info(os.path.basename(file_path), points.shape[0])
            self.sidebar.update_dimensions(data["dims"])
            print(f"[INFO] Added new layer: {file_path} ({points.shape[0]} points)")
        except Exception as e:
            print(f"[ERROR] Failed to add new layer from file: {file_path}: {e}")
            self.sidebar.set_status(f"Failed to add: {os.path.basename(file_path)}")

    def _on_layer_removed_debug(self, uuid):
        print(f"[DEBUG] layer_removed signal received from LayerManagerWidget (Remove button pressed), uuid={uuid}")
        if uuid not in self.layer_manager.layers:
            print(f"[ERROR] _on_layer_removed_debug: UUID {uuid} not found in layers!")
            return
        # Remove the actor from the viewer if present
        actor = self.layer_manager.layers[uuid].get('actor', None)
        if actor and hasattr(self.viewer, 'plotter'):
            try:
                self.viewer.plotter.remove_actor(actor)
            except Exception as e:
                print(f"[WARN] Could not remove actor for layer {uuid}: {e}")
        # Remove the layer from LayerManager
        del self.layer_manager.layers[uuid]
        # If the removed layer was current, update current selection
        if self.layer_manager.get_current_layer_id() == uuid:
            remaining = list(self.layer_manager.layers.keys())
            if remaining:
                new_current = remaining[0]
                self.layer_manager.set_current_layer(new_current)
                # Update sidebar settings for new current layer
                settings = load_layer_settings(new_current)
                if settings:
                    self.sidebar.set_sidebar_settings(settings)
                # Show bounding box for new current layer
                self._show_bounding_box_for_current_layer()
            else:
                self.layer_manager.set_current_layer(None)
                # Clear viewer and sidebar info
                if hasattr(self.viewer, 'clear'):
                    self.viewer.clear()
                self.sidebar.set_status("No layers loaded.")
                self.sidebar.update_file_info("", 0)
                self.sidebar.update_dimensions([])
                # Remove bounding box if present
                if hasattr(self, '_bbox_actor') and self._bbox_actor is not None:
                    try:
                        self.viewer.plotter.remove_actor(self._bbox_actor)
                    except Exception:
                        pass
                    self._bbox_actor = None
        # Update the sidebar's layer list
        all_layers = [(u, l['file_path']) for u, l in self.layer_manager.layers.items()]
        checked_uuids = set(u for u, l in self.layer_manager.layers.items() if l['visible'])
        self.sidebar.update_layers(all_layers, current_uuid=self.layer_manager.get_current_layer_id(), checked_uuids=checked_uuids)
        # Redraw all layers
        self.plot_all_layers()
        print(f"[INFO] Removed layer: {uuid}")



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
            new_layer_id = generate_layer_id()
            self.layer_manager.add_layer(new_layer_id, file_path, self._points, self._las, visible=True, actor=None)
            settings = load_layer_settings(new_layer_id)
            if settings:
                print(f"[INFO] Loaded sidebar settings from DB for layer {new_layer_id}")
                self.sidebar.set_sidebar_settings(settings)
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
            save_layer_settings(new_layer_id, file_path, self.sidebar.get_sidebar_settings())
            # Update the layer manager with all layers, checked state reflects visibility
            all_layers = [(uuid, l['file_path']) for uuid, l in self.layer_manager.layers.items()]
            checked_uuids = set(uuid for uuid, l in self.layer_manager.layers.items() if l['visible'])
            self.sidebar.update_layers(all_layers, current_uuid=new_layer_id, checked_uuids=checked_uuids)
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
        print(f"[DEBUG] _on_layer_toggled: self.layer_manager.layers.keys()={list(self.layer_manager.layers.keys())}")
        if uuid in self.layer_manager.layers:
            self.layer_manager.set_layer_visible(uuid, checked)
            try:
                # Always update the plotter to show all visible layers
                self._update_all_layers_in_viewer()
                if checked:
                    # Restore sidebar settings for this layer (active layer logic)
                    settings = load_layer_settings(uuid)
                    if settings:
                        print(f"[DEBUG] Restoring sidebar settings for layer {uuid}")
                        self.sidebar.set_sidebar_settings(settings)
                    self.layer_manager.set_current_layer(uuid)
                    # Show bounding box for the toggled-on layer
                    self._show_bounding_box_for_current_layer()
                else:
                    print("[DEBUG] Toggling layer OFF, updated all layers in viewer")
                    # Optionally, update sidebar to next visible layer if only one remains
                    visible_uuids = [u for u, l in self.layer_manager.layers.items() if l['visible']]
                    if len(visible_uuids) == 1:
                        next_uuid = visible_uuids[0]
                        print(f"[DEBUG] Restoring sidebar settings for only remaining visible layer {next_uuid}")
                        settings = load_layer_settings(next_uuid)
                        if settings:
                            self.sidebar.set_sidebar_settings(settings)
                            self.layer_manager.set_current_layer(next_uuid)
                            # Show bounding box for the only remaining visible layer
                            self._show_bounding_box_for_current_layer()
                    else:
                        # If no visible layers, remove bounding box
                        if hasattr(self, '_bbox_actor') and self._bbox_actor is not None:
                            try:
                                self.viewer.plotter.remove_actor(self._bbox_actor)
                            except Exception:
                                pass
                            self._bbox_actor = None
            except Exception as e:
                print(f"[ERROR] Exception in _on_layer_toggled: {e}")
        else:
            print(f"[ERROR] UUID {uuid} not found in self.layer_manager.layers!")




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

import os
import sys
import numpy as np
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
    
    def _show_point_picking_status(self, enabled):
        """Show or hide the point picking status indicator"""
        if enabled:
            self.point_picking_status_label.show()
        else:
            self.point_picking_status_label.hide()
    
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
        # Integrate point picking (enabled by default)
        from point_picking.point_picker import PointPicker
        self.point_picker = PointPicker(self.viewer)
        
        # Initialize height profile components
        from profile_line.line_drawer import LineDrawer
        from profile_line.profile_calculator import ProfileCalculator
        from profile_line.profile_viewer import ProfileViewer
        
        self.line_drawer = LineDrawer(self.viewer)
        self.profile_calculator = ProfileCalculator()
        self.profile_viewer = ProfileViewer(self)
        
        # Connect profile viewer to calculator for recalculation
        self.profile_viewer.set_profile_calculator(self.profile_calculator)
        
        # Set callback for line completion
        self.line_drawer.on_line_completed_callback = self._on_profile_line_completed
        # self._current_file_path and self._current_layer_id are now managed by LayerManager
        self._metadata_action = None    # Reference to metadata menu action
        from viewer.view_toolbar import ViewToolbar
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.sidebar)
        # Create a vertical layout for toolbar + viewer
        viewer_vlayout = QVBoxLayout()
        self.view_toolbar = ViewToolbar(self.viewer, main_window=self, parent=self)
        # Add toolbar with alignment left, no stretch
        viewer_vlayout.addWidget(self.view_toolbar, alignment=Qt.AlignLeft)
        
        # Create a container for the viewer with status overlay
        viewer_container = QWidget()
        viewer_container_layout = QVBoxLayout(viewer_container)
        viewer_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create status label for point picking (initially hidden)
        from PySide6.QtWidgets import QLabel
        self.point_picking_status_label = QLabel("Point Picking Enabled")
        self.point_picking_status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(61, 174, 233, 200);
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                margin: 10px;
            }
        """)
        self.point_picking_status_label.setAlignment(Qt.AlignCenter)
        self.point_picking_status_label.hide()
        
        # Create status label for height profile (initially hidden)
        self.height_profile_status_label = QLabel("Height Profile Mode: Click two points")
        self.height_profile_status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(233, 174, 61, 200);
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                margin: 10px;
            }
        """)
        self.height_profile_status_label.setAlignment(Qt.AlignCenter)
        self.height_profile_status_label.hide()
        
        # Add status labels and viewer to container
        viewer_container_layout.addWidget(self.point_picking_status_label)
        viewer_container_layout.addWidget(self.height_profile_status_label)
        viewer_container_layout.addWidget(self.viewer, stretch=1)
        
        viewer_vlayout.addWidget(viewer_container, stretch=1)
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
            if hasattr(self, '_export_layer_action'):
                self._export_layer_action.setEnabled(True)
            self._on_projection_changed()
            self._on_color_by_changed()
        else:
            print("[INFO] No default file loaded.")
            self.sidebar.set_status("No default file loaded.")
            self.layer_manager.set_current_layer(None)
            if self._metadata_action:
                self._metadata_action.setEnabled(False)
            if hasattr(self, '_export_layer_action'):
                self._export_layer_action.setEnabled(False)
    
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
        
        file_menu.addSeparator()
        
        # Export submenu
        export_menu = file_menu.addMenu("Export")
        export_layer_action = export_menu.addAction("Export Current Layer as LAZ...")
        export_layer_action.triggered.connect(self._export_current_layer)
        export_layer_action.setEnabled(False)
        self._export_layer_action = export_layer_action
        
        file_menu.addSeparator()
        
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
            if hasattr(self, '_export_layer_action'):
                self._export_layer_action.setEnabled(True)
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

    def _toggle_bounding_box_for_current_layer(self, enabled):
        """Show or hide the bounding box for the current layer."""
        if enabled:
            self._show_bounding_box_for_current_layer()
        else:
            # Remove previous bounding box actor if present
            if hasattr(self, '_bbox_actor') and self._bbox_actor is not None:
                try:
                    self.viewer.plotter.remove_actor(self._bbox_actor)
                except Exception:
                    pass
                self._bbox_actor = None
            if hasattr(self.viewer, 'plotter'):
                self.viewer.plotter.update()

    def _toggle_height_profile_mode(self, enabled):
        """Enable/disable height profile drawing mode"""
        if enabled:
            self.line_drawer.start_line_drawing()
            self._show_height_profile_status(True)
            print("[INFO] Height profile mode enabled. Click two points to draw a line.")
        else:
            # When disabling, clear any existing line and fully stop the mode
            self.line_drawer.stop_line_drawing()
            # Also clear any existing completed line
            if hasattr(self.line_drawer, 'line_actor') and self.line_drawer.line_actor:
                self.line_drawer.clear_completed_line()
            self._show_height_profile_status(False)
            print("[INFO] Height profile mode disabled.")

    def _show_height_profile_status(self, enabled):
        """Show or hide height profile status indicator"""
        if enabled:
            self.height_profile_status_label.show()
        else:
            self.height_profile_status_label.hide()

    def _on_profile_line_completed(self, start_point, end_point):
        """Called when user completes drawing a line"""
        print(f"[INFO] Profile line completed: {start_point} -> {end_point}")
        
        # Get current layer points
        current_layer_id = self.layer_manager.get_current_layer_id()
        if not current_layer_id or current_layer_id not in self.layer_manager.layers:
            print("[WARN] No current layer available for profile calculation")
            return
            
        layer = self.layer_manager.layers[current_layer_id]
        points = layer.get('points', None)
        
        if points is None or points.shape[0] == 0:
            print("[WARN] No points available in current layer")
            return
        
        # Calculate profile
        try:
            print("[INFO] Starting height profile calculation...")
            profile_data = self.profile_calculator.calculate_profile(
                points, start_point, end_point, num_samples=100, tolerance=1.0
            )
            
            # Display profile in viewer
            self.profile_viewer.display_profile(profile_data, points, start_point, end_point)
            self.profile_viewer.show()
            self.profile_viewer.raise_()
            self.profile_viewer.activateWindow()
            
            # Display results summary in console
            self._display_profile_results(profile_data)
            
        except Exception as e:
            print(f"[ERROR] Failed to calculate profile: {e}")
            import traceback
            traceback.print_exc()
        
        # Disable height profile mode but KEEP the line visible
        # Don't change the button state here - let the user manually cancel if they want
        self.line_drawer.is_drawing = False
        self.line_drawer._disable_picking()
        self._show_height_profile_status(False)
        print("[INFO] Line drawing completed. Profile calculated!")
        
    def _import_cross_section_layer(self, temp_file_path, point_count):
        """Import cross-section as a new layer"""
        try:
            from fileio.las_loader import load_point_cloud_data
            
            print(f"[INFO] Importing cross-section layer from: {temp_file_path}")
            
            # Load the temporary LAZ file
            data = load_point_cloud_data(temp_file_path)
            points = data["points"]
            las = data["las"]
            
            # Generate new layer ID
            uuid = generate_layer_id()
            
            # Create descriptive name
            import os
            base_name = "CrossSection"
            if hasattr(self, 'layer_manager'):
                current_layer_id = self.layer_manager.get_current_layer_id()
                if current_layer_id and current_layer_id in self.layer_manager.layers:
                    original_file = self.layer_manager.layers[current_layer_id].get('file_path', '')
                    if original_file:
                        base_name = f"CrossSection_{os.path.splitext(os.path.basename(original_file))[0]}"
            
            layer_name = f"{base_name}_{point_count}pts"
            
            # Add layer to manager
            self.layer_manager.add_layer(uuid, layer_name, points, las, visible=True, actor=None)
            
            # Save default settings for new layer
            default_settings = self.sidebar.get_sidebar_settings()
            # Set a different color for cross-section
            default_settings['colormap'] = 'plasma'  # Different colormap
            save_layer_settings(uuid, layer_name, default_settings)
            
            # Update display
            self.plot_all_layers()
            
            # Update sidebar
            all_layers = [(u, l['file_path']) for u, l in self.layer_manager.layers.items()]
            checked_uuids = set(u for u, l in self.layer_manager.layers.items() if l['visible'])
            self.sidebar.update_layers(all_layers, current_uuid=uuid, checked_uuids=checked_uuids)
            
            # Update sidebar info
            self.sidebar.set_status(f"Cross-section layer created: {point_count} points")
            self.sidebar.update_file_info(layer_name, point_count)
            self.sidebar.update_dimensions(data["dims"])
            
            # Apply settings to new layer
            self.sidebar.set_sidebar_settings(default_settings)
            
            print(f"[INFO] Cross-section layer imported successfully: {layer_name}")
            
            # Clean up temporary file
            try:
                os.remove(temp_file_path)
                print(f"[INFO] Temporary file cleaned up: {temp_file_path}")
            except:
                print(f"[WARN] Could not clean up temporary file: {temp_file_path}")
                
        except Exception as e:
            print(f"[ERROR] Failed to import cross-section layer: {e}")
            import traceback
            traceback.print_exc()
    
    def _export_current_layer(self):
        """Export current layer as LAZ file"""
        current_layer_id = self.layer_manager.get_current_layer_id()
        if not current_layer_id or current_layer_id not in self.layer_manager.layers:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Layer", "No current layer available for export.")
            return
            
        layer = self.layer_manager.layers[current_layer_id]
        points = layer.get('points', None)
        las_data = layer.get('las', None)
        file_path = layer.get('file_path', 'unknown')
        
        if points is None or points.shape[0] == 0:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Data", "Current layer has no points to export.")
            return
        
        # Get output file path
        from PySide6.QtWidgets import QFileDialog
        import os
        
        default_name = f"exported_{os.path.splitext(os.path.basename(file_path))[0]}.laz"
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Export Layer as LAZ", default_name, 
            "LAZ Files (*.laz);;LAS Files (*.las);;All Files (*)"
        )
        
        if not output_path:
            return
            
        try:
            from fileio.las_exporter import export_points_to_laz
            
            # Create all point indices for full export
            point_indices = np.arange(len(points))
            
            success = export_points_to_laz(
                points, output_path, las_data, point_indices, preserve_all_dimensions=True
            )
            
            if success:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Export Successful", 
                                      f"Layer exported successfully:\n{output_path}\n\n"
                                      f"Points: {len(points):,}")
                print(f"[INFO] Layer exported: {output_path} ({len(points)} points)")
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Export Failed", 
                                   f"Failed to export layer to:\n{output_path}")
                
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Export Error", 
                               f"Error during export:\n{str(e)}")
            print(f"[ERROR] Export failed: {e}")
            import traceback
            traceback.print_exc()
        
    def _display_profile_results(self, profile_data):
        """Display profile calculation results summary in console"""
        summary = profile_data.get('summary', {})
        
        print(f"[INFO] Profile Summary:")
        print(f"  - Total length: {profile_data['total_length']:.2f} m")
        print(f"  - Valid samples: {summary.get('valid_samples', 0)}")
        print(f"  - Coverage: {summary.get('coverage_percentage', 0):.1f}%")
        print(f"  - Elevation range: {summary.get('elevation_range', 0):.2f} m")
        print(f"  - Min elevation: {summary.get('min_elevation', 0):.2f} m")
        print(f"  - Max elevation: {summary.get('max_elevation', 0):.2f} m")
        print(f"  - Mean elevation: {summary.get('mean_elevation', 0):.2f} m")
        print(f"  - Total elevation change: {summary.get('total_elevation_change', 0):.2f} m")
        
        # Print the first few data points for verification
        print(f"[INFO] First 5 profile points:")
        for i in range(min(5, len(profile_data['distances']))):
            dist = profile_data['distances'][i]
            mean_h = profile_data['mean_heights'][i]
            min_h = profile_data['min_heights'][i]
            max_h = profile_data['max_heights'][i]
            count = profile_data['point_counts'][i]
            
            if not np.isnan(mean_h):
                print(f"  {dist:6.1f}m: {mean_h:7.2f}m (min: {min_h:7.2f}, max: {max_h:7.2f}, pts: {count})")
            else:
                print(f"  {dist:6.1f}m: No data")




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

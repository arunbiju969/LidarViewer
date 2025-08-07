from PySide6.QtWidgets import QToolBar
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt

class ViewToolbar(QToolBar):
    def __init__(self, viewer, main_window=None, parent=None):
        from PySide6.QtWidgets import QSizePolicy
        super().__init__("View Toolbar", parent)
        self.viewer = viewer
        self.main_window = main_window
        self._add_view_actions()
        # Make toolbar expand horizontally
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # Set focus policies to prevent blue border
        self.setFocusPolicy(Qt.NoFocus)

    def _add_view_actions(self):
        view_actions = [
            ("Top", self.viewer.set_top_view),
            ("Bottom", self.viewer.set_bottom_view),
            ("Left", self.viewer.set_left_view),
            ("Right", self.viewer.set_right_view),
            ("Front", self.viewer.set_front_view),
            ("Back", self.viewer.set_back_view),
        ]
        for i, (name, handler) in enumerate(view_actions):
            action = QAction(name, self)
            action.triggered.connect(handler)
            self.addAction(action)
            if i < len(view_actions) - 1:
                self.addSeparator()
        # Add separator before point picking toggle
        self.addSeparator()
        
        # Add point picking toggle action
        self.point_picking_action = QAction("Enable Point Picking", self)
        self.point_picking_action.triggered.connect(self._toggle_point_picking)
        self.addAction(self.point_picking_action)
        
        # Add separator before bounding box toggle
        self.addSeparator()
        
        # Add bounding box toggle action
        self.bounding_box_action = QAction("Show Bounding Box", self)
        self.bounding_box_action.setCheckable(True)
        self.bounding_box_action.setChecked(False)
        self.bounding_box_action.triggered.connect(self._toggle_bounding_box)
        self.addAction(self.bounding_box_action)
        
        # Add separator before height profile toggle
        self.addSeparator()
        
        # Add height profile toggle action
        self.height_profile_action = QAction("Height Profile", self)
        self.height_profile_action.setCheckable(True)
        self.height_profile_action.setChecked(False)
        self.height_profile_action.triggered.connect(self._toggle_height_profile)
        self.addAction(self.height_profile_action)

    def _toggle_point_picking(self):
        print("[DEBUG] Point picking toggle triggered.")
        if hasattr(self.main_window, 'point_picker'):
            current_state = self.main_window.point_picker.is_enabled()
            new_state = not current_state
            self.main_window.point_picker.set_enabled(new_state)
            
            # Update button text and status
            if new_state:
                self.point_picking_action.setText("Disable Point Picking")
                self.main_window._show_point_picking_status(True)
            else:
                self.point_picking_action.setText("Enable Point Picking")
                self.main_window._show_point_picking_status(False)
        else:
            print("[WARN] Point picker not available.")

    def _toggle_bounding_box(self):
        print("[DEBUG] Bounding box toggle triggered.")
        if hasattr(self.main_window, '_toggle_bounding_box_for_current_layer'):
            new_state = self.bounding_box_action.isChecked()
            self.main_window._toggle_bounding_box_for_current_layer(new_state)
            if new_state:
                self.bounding_box_action.setText("Hide Bounding Box")
            else:
                self.bounding_box_action.setText("Show Bounding Box")
        else:
            print("[WARN] MainWindow missing _toggle_bounding_box_for_current_layer method.")

    def _toggle_height_profile(self):
        print("[DEBUG] Height profile toggle triggered.")
        if hasattr(self.main_window, '_toggle_height_profile_mode'):
            new_state = self.height_profile_action.isChecked()
            self.main_window._toggle_height_profile_mode(new_state)
            if new_state:
                self.height_profile_action.setText("Cancel Profile")
            else:
                self.height_profile_action.setText("Height Profile")
        else:
            print("[WARN] MainWindow missing _toggle_height_profile_mode method.")

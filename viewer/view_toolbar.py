from PySide6.QtWidgets import QToolBar
from PySide6.QtGui import QAction

class ViewToolbar(QToolBar):
    def __init__(self, viewer, main_window=None, parent=None):
        from PySide6.QtWidgets import QSizePolicy
        super().__init__("View Toolbar", parent)
        self.viewer = viewer
        self.main_window = main_window
        self._add_view_actions()
        # Make toolbar expand horizontally
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

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
        # Add point picking toggle button
        from PySide6.QtWidgets import QPushButton
        self.point_picking_btn = QPushButton("Enable Point Picking")
        self.point_picking_btn.setCheckable(True)
        self.point_picking_btn.setChecked(False)
        self.point_picking_btn.clicked.connect(self._toggle_point_picking)
        self.addWidget(self.point_picking_btn)

    def _toggle_point_picking(self):
        print(f"[DEBUG] Point picking button clicked. Checked={self.point_picking_btn.isChecked()}")
        # Access MainWindow's point_picker via reference
        if hasattr(self.main_window, 'point_picker'):
            enabled = self.point_picking_btn.isChecked()
            self.main_window.point_picker.set_enabled(enabled)
            self.point_picking_btn.setText(
                "Disable Point Picking" if enabled else "Enable Point Picking"
            )
        # Apply dark mode hover style (blue highlight)
        self.setStyleSheet("""
        QToolBar QPushButton {
            background: transparent;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
        }
        QToolBar QPushButton:hover {
            background: #3daee9;
            color: white;
        }
        QToolBar {
            background: #232629;
        }
        """)

import os
from PySide6.QtGui import QPalette, QColor
import pyvista as pv
from PySide6.QtWidgets import QApplication

def apply_theme(theme_name, main_window=None):
    app = QApplication.instance()
    if theme_name == "Dark":
        # Set Qt modern dark grey palette
        dark_palette = app.palette()
        dark_palette.setColor(QPalette.Window, QColor("#232629"))
        dark_palette.setColor(QPalette.WindowText, QColor("#d3dae3"))
        dark_palette.setColor(QPalette.Base, QColor("#2e2e2e"))
        dark_palette.setColor(QPalette.AlternateBase, QColor("#232629"))
        dark_palette.setColor(QPalette.ToolTipBase, QColor("#232629"))
        dark_palette.setColor(QPalette.ToolTipText, QColor("#d3dae3"))
        dark_palette.setColor(QPalette.Text, QColor("#d3dae3"))
        dark_palette.setColor(QPalette.Button, QColor("#232629"))
        dark_palette.setColor(QPalette.ButtonText, QColor("#d3dae3"))
        dark_palette.setColor(QPalette.BrightText, QColor("#ff0000"))
        dark_palette.setColor(QPalette.Highlight, QColor("#3daee9"))
        dark_palette.setColor(QPalette.HighlightedText, QColor("#232629"))
        app.setPalette(dark_palette)
        # Load dark QSS from external file
        qss_path = os.path.join(os.path.dirname(__file__), "dark.qss")
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                dark_qss = f.read()
            app.setStyleSheet(dark_qss)
        except Exception:
            app.setStyleSheet("")
        # Set menu bar and menu style for dark theme
        menu_style = """
            QMenuBar {
                background: #232629;
                color: #f8f8f8;
                border: none;
            }
            QMenuBar::item {
                background: transparent;
                color: #f8f8f8;
                padding: 6px 18px;
                margin: 0 2px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background: #3daee9;
                color: #232629;
            }
            QMenu {
                background: #232629;
                color: #f8f8f8;
                border: 1px solid #444;
            }
            QMenu::item:selected {
                background: #3daee9;
                color: #232629;
            }
        """
        if main_window:
            main_window.setStyleSheet(menu_style)
        pv.set_plot_theme("dark")
    else:
        app.setPalette(app.style().standardPalette())
        app.setStyleSheet("")
        # Set menu bar and menu style for light theme
        menu_style = """
            QMenuBar {
                background: #f8f8f8;
                color: #232629;
                border: none;
            }
            QMenuBar::item {
                background: transparent;
                color: #232629;
                padding: 6px 18px;
                margin: 0 2px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background: #3daee9;
                color: #fff;
            }
            QMenu {
                background: #fff;
                color: #232629;
                border: 1px solid #bbb;
            }
            QMenu::item:selected {
                background: #3daee9;
                color: #fff;
            }
        """
        if main_window:
            main_window.setStyleSheet(menu_style)
        pv.set_plot_theme("document")

import os
from PySide6.QtGui import QPalette, QColor
import pyvista as pv
from PySide6.QtWidgets import QApplication

def apply_theme(theme_name):
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
        pv.set_plot_theme("dark")
    else:
        app.setPalette(app.style().standardPalette())
        app.setStyleSheet("")
        pv.set_plot_theme("document")

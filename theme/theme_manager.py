import os
from PySide6.QtGui import QPalette, QColor
import pyvista as pv
from PySide6.QtWidgets import QApplication


class UnifiedThemeManager:
    """Unified theme manager for consistent styling across the application"""
    
    @staticmethod
    def get_enhanced_button_style(is_dark=True):
        """Get enhanced button styling for both light and dark themes"""
        if is_dark:
            return """
                QPushButton {
                    background-color: #2e2e2e;
                    border: 2px solid #3daee9;
                    border-radius: 6px;
                    padding: 8px 12px;
                    color: white;
                    font-weight: bold;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    border-color: #5cbef0;
                }
                QPushButton:pressed {
                    background-color: #3daee9;
                    border-color: #2a9dd4;
                    color: #232629;
                }
                QPushButton:disabled {
                    background-color: #1a1a1a;
                    border-color: #444;
                    color: #666;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #f0f0f0;
                    border: 2px solid #3daee9;
                    border-radius: 6px;
                    padding: 8px 12px;
                    color: #333;
                    font-weight: bold;
                    min-height: 20px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                    border-color: #5cbef0;
                }
                QPushButton:pressed {
                    background-color: #3daee9;
                    border-color: #2a9dd4;
                    color: white;
                }
                QPushButton:disabled {
                    background-color: #f8f8f8;
                    border-color: #ccc;
                    color: #999;
                }
            """
    
    @staticmethod
    def get_enhanced_combobox_style(is_dark=True):
        """Get enhanced combobox styling for both light and dark themes"""
        if is_dark:
            return """
                QComboBox {
                    background-color: #2e2e2e;
                    border: 2px solid #3daee9;
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: white;
                    min-height: 20px;
                }
                QComboBox:hover {
                    border-color: #5cbef0;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 20px;
                    border-left-width: 1px;
                    border-left-color: #3daee9;
                    border-left-style: solid;
                    border-top-right-radius: 4px;
                    border-bottom-right-radius: 4px;
                    background-color: #3daee9;
                }
                QComboBox::down-arrow {
                    width: 0;
                    height: 0;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid white;
                }
                QComboBox QAbstractItemView {
                    background-color: #2e2e2e;
                    border: 1px solid #3daee9;
                    color: white;
                    selection-background-color: #3daee9;
                }
            """
        else:
            return """
                QComboBox {
                    background-color: #fff;
                    border: 2px solid #3daee9;
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: #333;
                    min-height: 20px;
                }
                QComboBox:hover {
                    border-color: #5cbef0;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 20px;
                    border-left-width: 1px;
                    border-left-color: #3daee9;
                    border-left-style: solid;
                    border-top-right-radius: 4px;
                    border-bottom-right-radius: 4px;
                    background-color: #3daee9;
                }
                QComboBox::down-arrow {
                    width: 0;
                    height: 0;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid white;
                }
                QComboBox QAbstractItemView {
                    background-color: #fff;
                    border: 1px solid #3daee9;
                    color: #333;
                    selection-background-color: #3daee9;
                    selection-color: white;
                }
            """
    
    @staticmethod
    def get_enhanced_groupbox_style(is_dark=True):
        """Get enhanced group box styling for both light and dark themes"""
        if is_dark:
            return """
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #3daee9;
                    border-radius: 8px;
                    margin: 6px 0px;
                    padding-top: 8px;
                    background-color: #181a1b;
                    color: white;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 8px 0 8px;
                    background-color: #181a1b;
                    color: white;
                }
            """
        else:
            return """
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #3daee9;
                    border-radius: 8px;
                    margin: 6px 0px;
                    padding-top: 8px;
                    background-color: #f8f8f8;
                    color: #333;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 8px 0 8px;
                    background-color: #f8f8f8;
                    color: #3daee9;
                }
            """
    
    @staticmethod
    def get_enhanced_listwidget_style(is_dark=True):
        """Get enhanced list widget styling for both light and dark themes"""
        if is_dark:
            return """
                QListWidget {
                    background-color: #2e2e2e;
                    border: 2px solid #3daee9;
                    border-radius: 4px;
                    color: white;
                    selection-background-color: #3daee9;
                    selection-color: white;
                }
                QListWidget::item {
                    padding: 4px;
                    border-bottom: 1px solid #444;
                }
                QListWidget::item:hover {
                    background-color: #3a3a3a;
                }
                QListWidget::item:selected {
                    background-color: #3daee9;
                }
            """
        else:
            return """
                QListWidget {
                    background-color: #fff;
                    border: 2px solid #3daee9;
                    border-radius: 4px;
                    color: #333;
                    selection-background-color: #3daee9;
                    selection-color: white;
                }
                QListWidget::item {
                    padding: 4px;
                    border-bottom: 1px solid #ddd;
                }
                QListWidget::item:hover {
                    background-color: #f0f0f0;
                }
                QListWidget::item:selected {
                    background-color: #3daee9;
                    color: white;
                }
            """
    
    @staticmethod
    def get_enhanced_slider_style(is_dark=True):
        """Get enhanced slider styling for both light and dark themes"""
        if is_dark:
            return """
                QSlider::groove:horizontal {
                    border: 1px solid #3daee9;
                    height: 6px;
                    background: #2e2e2e;
                    margin: 2px 0;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #3daee9;
                    border: 1px solid #3daee9;
                    width: 16px;
                    margin: -6px 0;
                    border-radius: 8px;
                }
                QSlider::handle:horizontal:hover {
                    background: #5cbef0;
                }
                QSlider::sub-page:horizontal {
                    background: #3daee9;
                    border: 1px solid #3daee9;
                    height: 6px;
                    border-radius: 3px;
                }
            """
        else:
            return """
                QSlider::groove:horizontal {
                    border: 1px solid #3daee9;
                    height: 6px;
                    background: #f0f0f0;
                    margin: 2px 0;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #3daee9;
                    border: 1px solid #3daee9;
                    width: 16px;
                    margin: -6px 0;
                    border-radius: 8px;
                }
                QSlider::handle:horizontal:hover {
                    background: #5cbef0;
                }
                QSlider::sub-page:horizontal {
                    background: #3daee9;
                    border: 1px solid #3daee9;
                    height: 6px;
                    border-radius: 3px;
                }
            """
    
    @staticmethod
    def get_sidebar_style(is_dark=True):
        """Get sidebar container styling for both light and dark themes"""
        if is_dark:
            return """
                #sidebar { 
                    min-width: 260px; 
                    max-width: 260px; 
                    width: 260px; 
                    border: 2px solid #3daee9; 
                    border-radius: 8px; 
                    background: #181a1b;
                }
            """
        else:
            return """
                #sidebar { 
                    min-width: 260px; 
                    max-width: 260px; 
                    width: 260px; 
                    border: 2px solid #3daee9; 
                    border-radius: 8px; 
                    background: #f8f8f8;
                }
            """
    
    @staticmethod
    def get_dock_widget_style(is_dark=True):
        """Get dock widget styling for both light and dark themes"""
        if is_dark:
            return """
                QDockWidget {
                    margin-left: 8px;
                    margin-right: 8px;
                    background-color: #181a1b;
                    color: white;
                    border: 2px solid #3daee9;
                    border-radius: 8px;
                }
                QDockWidget::title {
                    background-color: #3daee9;
                    color: white;
                    padding: 4px;
                    text-align: center;
                    font-weight: bold;
                }
            """
        else:
            return """
                QDockWidget {
                    margin-left: 8px;
                    margin-right: 8px;
                    background-color: #f8f8f8;
                    color: #333;
                    border: 2px solid #3daee9;
                    border-radius: 8px;
                }
                QDockWidget::title {
                    background-color: #3daee9;
                    color: white;
                    padding: 4px;
                    text-align: center;
                    font-weight: bold;
                }
            """
    
    @staticmethod
    def is_dark_theme():
        """Check if the current theme is dark"""
        try:
            app = QApplication.instance()
            if app:
                # Try to get the main window and check its theme
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'sidebar') and hasattr(widget.sidebar, 'theme_box'):
                        current_theme = widget.sidebar.theme_box.currentText()
                        return current_theme.lower() == "dark"
        except Exception as e:
            print(f"[DEBUG] UnifiedTheme: Theme detection failed: {e}")
        
        # Default to light theme if detection fails
        return False


def apply_theme(theme_name, main_window=None):
    """Apply theme to the application using QSS files"""
    app = QApplication.instance()
    if app is None:
        return
    
    is_dark = theme_name.lower() == "dark"
    
    if is_dark:
        # Set dark palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(35, 38, 41))  # #232629
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))  # white
        palette.setColor(QPalette.Base, QColor(24, 26, 27))  # #181a1b 
        palette.setColor(QPalette.AlternateBase, QColor(46, 46, 46))  # #2e2e2e
        palette.setColor(QPalette.ToolTipBase, QColor(0, 0, 0))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(46, 46, 46))  # #2e2e2e
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(61, 174, 233))  # #3daee9
        palette.setColor(QPalette.Highlight, QColor(61, 174, 233))  # #3daee9
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)
        
        # Load dark theme stylesheet
        qss_file_path = os.path.join(os.path.dirname(__file__), "dark.qss")
        pv.set_plot_theme("dark")
        
    else:  # Light theme
        # Set light palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))  # #f0f0f0
        palette.setColor(QPalette.WindowText, QColor(0, 0, 0))  # black
        palette.setColor(QPalette.Base, QColor(255, 255, 255))  # white 
        palette.setColor(QPalette.AlternateBase, QColor(248, 248, 248))  # #f8f8f8
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 220))
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.Button, QColor(240, 240, 240))  # #f0f0f0
        palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(61, 174, 233))  # #3daee9
        palette.setColor(QPalette.Highlight, QColor(61, 174, 233))  # #3daee9
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        app.setPalette(palette)
        
        # Load light theme stylesheet
        qss_file_path = os.path.join(os.path.dirname(__file__), "light.qss")
        pv.set_plot_theme("default")
    
    # Apply the stylesheet from file
    if os.path.exists(qss_file_path):
        with open(qss_file_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
        print(f"[DEBUG] UnifiedTheme: Loaded stylesheet from {qss_file_path}")
    else:
        print(f"[WARN] UnifiedTheme: QSS file not found: {qss_file_path}")
        app.setStyleSheet("")
    
    # Store theme for later use
    if main_window and hasattr(main_window, 'current_theme'):
        main_window.current_theme = theme_name.lower()
    
    print(f"[DEBUG] UnifiedTheme: Applied {theme_name} theme with QSS file")

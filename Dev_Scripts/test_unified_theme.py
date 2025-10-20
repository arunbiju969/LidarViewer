#!/usr/bin/env python3
"""Test script for unified theme manager"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QComboBox, QGroupBox, QLabel
from PyQt6.QtCore import Qt
from theme.theme_manager import apply_theme, UnifiedThemeManager


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unified Theme Manager Test")
        self.setGeometry(100, 100, 400, 300)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add theme selection
        theme_combo = QComboBox()
        theme_combo.addItems(["Light", "Dark"])
        theme_combo.currentTextChanged.connect(self.change_theme)
        layout.addWidget(QLabel("Theme:"))
        layout.addWidget(theme_combo)
        
        # Add test components
        group = QGroupBox("Test Group")
        group_layout = QVBoxLayout(group)
        
        button1 = QPushButton("Test Button 1")
        button2 = QPushButton("Test Button 2")
        combo = QComboBox()
        combo.addItems(["Option 1", "Option 2", "Option 3"])
        
        group_layout.addWidget(button1)
        group_layout.addWidget(button2)
        group_layout.addWidget(combo)
        
        layout.addWidget(group)
        
        # Apply initial theme
        apply_theme("Dark", self)
        
    def change_theme(self, theme_name):
        print(f"[DEBUG] Changing theme to: {theme_name}")
        apply_theme(theme_name, self)


def main():
    app = QApplication(sys.argv)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

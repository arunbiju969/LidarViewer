#!/usr/bin/env python3
"""
Simple PyQt6 test application to verify Qt6 installation
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt

class TestApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('PyQt6 Test App')
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        title_label = QLabel('PyQt6 Test Application')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        status_label = QLabel('If you can see this window, PyQt6 is working!')
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_label)

        button = QPushButton('Click me!')
        button.clicked.connect(self.on_button_click)
        layout.addWidget(button)

        self.click_count_label = QLabel('Button clicked: 0 times')
        self.click_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.click_count_label)

        self.setLayout(layout)

    def on_button_click(self):
        current_text = self.click_count_label.text()
        count = int(current_text.split(':')[1].strip().split()[0])
        count += 1
        self.click_count_label.setText(f'Button clicked: {count} times')

def main():
    print("Starting PyQt6 test application...")
    app = QApplication(sys.argv)

    window = TestApp()
    window.show()

    print("PyQt6 application started successfully!")
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
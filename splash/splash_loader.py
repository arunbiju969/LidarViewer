from PySide6.QtWidgets import QSplashScreen, QProgressBar, QLabel
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QRect

def create_splash():
    splash_pix = QPixmap(500, 200)
    splash_pix.fill(QColor("#232629"))
    painter = QPainter(splash_pix)
    painter.setPen(QColor("#3daee9"))
    font = QFont()
    font.setPointSize(16)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRect(0, 60, 500, 40), Qt.AlignCenter, "Loading point cloud...")
    painter.end()

    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    progress_bar = QProgressBar(splash)
    progress_bar.setGeometry(50, 140, 400, 25)
    progress_bar.setRange(0, 100)
    progress_bar.setValue(0)
    progress_bar.setStyleSheet("QProgressBar { background-color: #2e2e2e; color: #d3dae3; border: 1px solid #3daee9; } QProgressBar::chunk { background-color: #3daee9; }")
    progress_bar.show()
    return splash, progress_bar

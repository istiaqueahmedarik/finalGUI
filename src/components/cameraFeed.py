from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt
import cv2
import numpy as np

PREVIEW_WIDTH = 480
PREVIEW_HEIGHT = 360
FULLSCREEN_WIDTH = 1920
FULLSCREEN_HEIGHT = 1000

class CameraFeed(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel("Waiting for stream...")
        self.label.setFixedSize(PREVIEW_WIDTH, PREVIEW_HEIGHT)

        self.fullscreen_btn = QPushButton("Full Screen")
        self.fullscreen_btn.clicked.connect(self.show_fullscreen)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.fullscreen_btn)
        self.setLayout(layout)

        self.fullscreen_window = None
        self.fullscreen_label = None
        self.last_pixmap = None

    def update_image(self, img_bytes):
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is not None:
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_img.shape
            bytes_per_line = ch * w
            qt_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_img)
            self.last_pixmap = pixmap
            self.label.setPixmap(pixmap.scaled(PREVIEW_WIDTH, PREVIEW_HEIGHT, Qt.AspectRatioMode.KeepAspectRatio))
            if self.fullscreen_label is not None:
                self.fullscreen_label.setPixmap(pixmap.scaled(FULLSCREEN_WIDTH, FULLSCREEN_HEIGHT, Qt.AspectRatioMode.KeepAspectRatio))

    def show_fullscreen(self):
        if self.fullscreen_window is None:
            self.fullscreen_window = QWidget()
            self.fullscreen_window.setWindowTitle("Camera Feed - Full Screen")

            layout = QVBoxLayout(self.fullscreen_window)

            self.fullscreen_label = QLabel(self.fullscreen_window)
            self.fullscreen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if self.last_pixmap is not None:
                self.fullscreen_label.setPixmap(self.last_pixmap.scaled(FULLSCREEN_WIDTH, FULLSCREEN_HEIGHT, Qt.AspectRatioMode.KeepAspectRatio))
            else:
                self.fullscreen_label.setText("No image received yet.")

            layout.addWidget(self.fullscreen_label)
            layout.addStretch()

            back_btn = QPushButton("Back")
            back_btn.setFixedWidth(200)
            back_btn.clicked.connect(self.exit_fullscreen)
            layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

            self.fullscreen_window.setLayout(layout)
            self.fullscreen_window.showFullScreen()
        else:
            self.fullscreen_window.showFullScreen()

    def exit_fullscreen(self):
        if self.fullscreen_window is not None:
            self.fullscreen_window.close()
            self.fullscreen_window = None
            self.fullscreen_label = None
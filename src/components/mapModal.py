from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt


class MapModal(QDialog):
    def __init__(self, map_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enlarged Map View")

        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        layout = QVBoxLayout(self)

        self.image_label = QLabel()
        pixmap = QPixmap(map_path)
        large_pixmap = pixmap.scaled(600, 600,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
        self.image_label.setPixmap(large_pixmap)
        layout.addWidget(self.image_label)
        # Allow clicking the enlarged map to close the modal
        self.image_label.mousePressEvent = self.close_on_click

    def close_on_click(self, event):
        self.accept()
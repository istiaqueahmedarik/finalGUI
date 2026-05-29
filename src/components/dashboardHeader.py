from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel


class DashboardHeader(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)  # 'self' makes the layout belong to this widget

        # Add your modern buttons
        self.label = QLabel("Mongol Barota")

        self.layout.addWidget(self.label)

        self.setStyleSheet("font-size: 24px; font-weight: bold;")

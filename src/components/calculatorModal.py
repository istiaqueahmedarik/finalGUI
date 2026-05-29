from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox
from PyQt6.QtCore import pyqtSignal

class CalculatorModal(QDialog):
    calculated = pyqtSignal(str, str)  # Emits (latitude_dd, longitude_dd)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Coordinate Calculator")
        self.setMinimumWidth(300)

        self.layout = QVBoxLayout(self)

        # Latitude Section
        self.layout.addWidget(QLabel("<b>Latitude (DMS)</b>"))
        lat_layout = QHBoxLayout()
        self.lat_deg = QLineEdit()
        self.lat_deg.setPlaceholderText("Deg")
        self.lat_min = QLineEdit()
        self.lat_min.setPlaceholderText("Min")
        self.lat_sec = QLineEdit()
        self.lat_sec.setPlaceholderText("Sec")
        self.lat_dir = QComboBox()
        self.lat_dir.addItems(["N", "S"])
        
        lat_layout.addWidget(self.lat_deg)
        lat_layout.addWidget(self.lat_min)
        lat_layout.addWidget(self.lat_sec)
        lat_layout.addWidget(self.lat_dir)
        self.layout.addLayout(lat_layout)

        # Longitude Section
        self.layout.addWidget(QLabel("<b>Longitude (DMS)</b>"))
        lon_layout = QHBoxLayout()
        self.lon_deg = QLineEdit()
        self.lon_deg.setPlaceholderText("Deg")
        self.lon_min = QLineEdit()
        self.lon_min.setPlaceholderText("Min")
        self.lon_sec = QLineEdit()
        self.lon_sec.setPlaceholderText("Sec")
        self.lon_dir = QComboBox()
        self.lon_dir.addItems(["E", "W"])

        lon_layout.addWidget(self.lon_deg)
        lon_layout.addWidget(self.lon_min)
        lon_layout.addWidget(self.lon_sec)
        lon_layout.addWidget(self.lon_dir)
        self.layout.addLayout(lon_layout)

        # Result Section
        self.layout.addWidget(QLabel("<b>Result (Decimal Degrees)</b>"))
        self.result_label = QLabel("Lat: -- \nLon: --")
        self.layout.addWidget(self.result_label)

        # Buttons
        btn_layout = QHBoxLayout()
        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.clicked.connect(self.calculate)
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_values)
        self.apply_btn.setEnabled(False)

        btn_layout.addWidget(self.calc_btn)
        btn_layout.addWidget(self.apply_btn)
        self.layout.addLayout(btn_layout)

        self.calculated_lat = ""
        self.calculated_lon = ""

    def calculate(self):
        try:
            # Lat
            lat_d = float(self.lat_deg.text() or 0)
            lat_m = float(self.lat_min.text() or 0)
            lat_s = float(self.lat_sec.text() or 0)
            lat_dd = lat_d + (lat_m / 60.0) + (lat_s / 3600.0)
            if self.lat_dir.currentText() == "S":
                lat_dd = -lat_dd

            # Lon
            lon_d = float(self.lon_deg.text() or 0)
            lon_m = float(self.lon_min.text() or 0)
            lon_s = float(self.lon_sec.text() or 0)
            lon_dd = lon_d + (lon_m / 60.0) + (lon_s / 3600.0)
            if self.lon_dir.currentText() == "W":
                lon_dd = -lon_dd

            self.calculated_lat = f"{lat_dd:.6f}"
            self.calculated_lon = f"{lon_dd:.6f}"
            
            self.result_label.setText(f"Lat: {self.calculated_lat}\nLon: {self.calculated_lon}")
            self.apply_btn.setEnabled(True)

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numeric values.")

    def apply_values(self):
        if self.calculated_lat and self.calculated_lon:
            self.calculated.emit(self.calculated_lat, self.calculated_lon)
            self.accept()

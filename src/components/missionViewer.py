from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from utility.send_udp_data import send_udp_data


class MissionViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.waypoint_data = dict()
        self.data_to_deliver = dict()
        self.layout = QHBoxLayout(self)

        self.waypoint_information = QLabel("Current Selected: #None")
        self.layout.addWidget(self.waypoint_information)

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.send_start_data)

        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.send_pause_data)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.send_stop_data)

        self.layout.addStretch()
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.pause_button)
        self.layout.addWidget(self.start_button)

    def update_mission_viewer(self, waypoint_data):
        self.waypoint_data = waypoint_data
        self.waypoint_information.setText(f"Current Selected: {waypoint_data['wp_id']}")

        print("Received waypoint data ===")
        print(self.waypoint_data)
        print("Received waypoint data ===")

    def send_start_data(self):
        self.data_to_deliver["command"] = "start"
        self.send_data()

    def send_pause_data(self):
        self.data_to_deliver["command"] = "pause"
        self.send_data()

    def send_stop_data(self):
        self.data_to_deliver["command"] = "stop"
        self.send_data()

    def send_data(self):
        starting = {
            "longitude": "123.123",
            "latitude": "123.123",
            "altitude": "123.123",
        }

        ending = {
            "longitude": self.waypoint_data['longitude'],
            "latitude": self.waypoint_data['latitude'],
            "altitude": self.waypoint_data['altitude'],
        }

        self.data_to_deliver["starting"] = starting
        self.data_to_deliver["ending"] = ending
        self.data_to_deliver["type"] = self.waypoint_data['wp_type']
        self.data_to_deliver["control"] = self.waypoint_data['control']

        print("UDP Data Sending ===")
        print(self.data_to_deliver)
        print("UDP Data Sending ===")

        send_udp_data(self.data_to_deliver, "192.168.2.116", 5006) # Orin's IP and port

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from components.waypointInput import WaypointInput
from components.waypointViewer import WaypointViewer
from components.missionViewer import MissionViewer
from components.mapViewer import MapViewer
from components.cameraFeed import CameraFeed
from components.cameraDiscovery import CameraDiscovery

class DashboardUI:
    def __init__(self):
        self.map_viewer = None
        self.header = None
        self.right_panel = None
        self.left_panel = None
        self.viewer_panel = None
        self.mission_control_viewer = None
        self.input_panel = None
        self.camera_feed = None
        self.camera_discovery = None
        self.sidebar_layout = None
        self.main_layout = None

    def setup_ui(self, central_widget):
        self.main_layout = QVBoxLayout(central_widget)

        waypoint_layout = QHBoxLayout()

        self.left_panel = QVBoxLayout()
        self.right_panel = QVBoxLayout()

        self.map_viewer = MapViewer()
        self.input_panel = WaypointInput()
        self.mission_control_viewer = MissionViewer()
        self.viewer_panel = WaypointViewer()
        self.camera_feed = CameraFeed()

        # Start camera discovery
        self.camera_discovery = CameraDiscovery(listen_port=5000)
        self.camera_discovery.cameras_updated.connect(self.camera_feed.update_streams)
        self.camera_discovery.start()
        print("[Dashboard] Camera discovery started")

        # Left panel: Input -> Camera -> Map
        self.left_panel.addWidget(self.input_panel)
        self.left_panel.addWidget(self.camera_feed)
        self.left_panel.addWidget(self.map_viewer)
        self.left_panel.addStretch()

        self.right_panel.addWidget(self.mission_control_viewer)
        self.right_panel.addWidget(self.viewer_panel)

        # Connections
        self.input_panel.submitted.connect(self.viewer_panel.add_waypoint)
        self.viewer_panel.mission_pushed.connect(self.mission_control_viewer.update_mission_viewer)
        # Set destination on mission push
        self.viewer_panel.mission_pushed.connect(lambda _: self.map_viewer.set_destination_to_first_waypoint())
        self.map_viewer.refresh_map.clicked.connect(self.viewer_panel.get_all_mission_data)
        self.viewer_panel.waypoint_data.connect(self.map_viewer.update_map)

        waypoint_layout.addLayout(self.left_panel, 3)
        waypoint_layout.addLayout(self.right_panel, 7)

        self.main_layout.addLayout(waypoint_layout)
    
    def on_gps_received(self, lat, lon):
        """Called when GPS data is received from ReceiverGUI"""
        if self.map_viewer:
            self.map_viewer.update_current_position(lat, lon)
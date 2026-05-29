from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy,
    QPushButton, QGroupBox, QSpinBox, QComboBox
)
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from PyQt6.QtCore import Qt

from components.waypointInput import WaypointInput
from components.waypointViewer import WaypointViewer
from components.missionViewer import MissionViewer
from components.mapViewer import MapViewer
from components.cameraFeed import CameraFeed

from utility.udp_image_receiver import UDPImageReceiver
from utility.teensy_sender import TeensySender
from utility.mission_config_loader import load_mission_coordinates


def circular_pixmap(pixmap, size):
    if pixmap.isNull():
        masked = QPixmap(size, size)
        masked.fill(Qt.GlobalColor.transparent)
        return masked

    img = pixmap.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation
    )

    masked = QPixmap(size, size)
    masked.fill(Qt.GlobalColor.transparent)

    painter = QPainter(masked)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    path = QPainterPath()
    path.addEllipse(0, 0, size, size)

    painter.setClipPath(path)
    painter.drawPixmap(0, 0, img)
    painter.end()

    return masked


class DashboardUI:
    def __init__(self):
        self.map_viewer = None
        self.viewer_panel = None
        self.mission_control_viewer = None
        self.input_panel = None

        self.camera_feed = None
        self.image_receiver = None

        self.main_layout = None
        self.left_panel = None
        self.right_panel = None

        self.current_camera_mode = "aruco"

    def setup_ui(self, central_widget):

        self.main_layout = QVBoxLayout(central_widget)

        # =========================================================
        # HEADER
        # =========================================================

        header_outer_layout = QHBoxLayout()
        header_outer_layout.addStretch()

        header_inner_layout = QHBoxLayout()

        logo_label = QLabel()

        import os
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        logo_path = os.path.join(base_dir, "assets", "logo.png")
        pixmap = QPixmap(logo_path)

        circle_size = 80

        circular = circular_pixmap(pixmap, circle_size)

        logo_label.setPixmap(circular)
        logo_label.setFixedSize(circle_size, circle_size)

        title_label = QLabel("<b>Autonomous Dashboard</b>")

        title_label.setStyleSheet("""
            font-size: 40px;
            font-family: Arial;
            margin-left: 24px;
        """)

        header_inner_layout.addWidget(logo_label)
        header_inner_layout.addWidget(title_label)

        header_outer_layout.addLayout(header_inner_layout)
        header_outer_layout.addStretch()

        self.main_layout.addLayout(header_outer_layout)

        # =========================================================
        # MAIN PANELS
        # =========================================================

        main_panel_layout = QHBoxLayout()

        self.left_panel = QVBoxLayout()
        self.right_panel = QVBoxLayout()

        # =========================================================
        # CORE WIDGETS
        # =========================================================

        self.input_panel = WaypointInput()

        self.camera_feed = CameraFeed()

        mission_lat, mission_lon = load_mission_coordinates()

        self.map_viewer = MapViewer(
            mission_latitude=mission_lat,
            mission_longitude=mission_lon
        )

        self.map_viewer.setMinimumSize(700, 500)

        self.map_viewer.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.mission_control_viewer = MissionViewer()

        self.viewer_panel = WaypointViewer()

        # =========================================================
        # CAMERA TOGGLE
        # =========================================================

        self.camera_selector = QComboBox()

        self.camera_selector.addItem("ArUco Detection")
        self.camera_selector.addItem("Object Detection")

        self.camera_selector.currentIndexChanged.connect(
            self.on_camera_mode_changed
        )

        # =========================================================
        # UDP IMAGE RECEIVER
        # =========================================================

        self.image_receiver = UDPImageReceiver(
            ip='0.0.0.0',
            port=5007
        )

        self.image_receiver.aruco_image_received.connect(
            self.update_aruco_image
        )

        self.image_receiver.object_image_received.connect(
            self.update_object_image
        )

        self.image_receiver.start()

        print("[Dashboard] UDP Receiver Started")

        # =========================================================
        # LEFT PANEL
        # =========================================================

        self.left_panel.addWidget(self.input_panel)

        self.left_panel.addWidget(self.camera_selector)

        self.left_panel.addWidget(self.camera_feed)

        self.left_panel.addStretch()

        # =========================================================
        # RIGHT PANEL
        # =========================================================

        self.right_panel.addWidget(self.mission_control_viewer)

        self.right_panel.addWidget(self.viewer_panel)

        self.right_panel.addWidget(self.map_viewer)

        self.right_panel.addStretch()

        # =========================================================
        # CONNECTIONS
        # =========================================================

        self.input_panel.submitted.connect(
            self.viewer_panel.add_waypoint
        )

        self.viewer_panel.mission_pushed.connect(
            self.mission_control_viewer.update_mission_viewer
        )

        self.viewer_panel.mission_pushed.connect(
            self._on_mission_pushed
        )

        self.map_viewer.refresh_map_btn.clicked.connect(
            self.viewer_panel.get_all_mission_data
        )

        self.viewer_panel.waypoint_data.connect(
            self.map_viewer.update_map
        )

        # =========================================================
        # FINAL LAYOUT
        # =========================================================

        main_panel_layout.addLayout(self.left_panel, 3)

        main_panel_layout.addLayout(self.right_panel, 7)

        self.main_layout.addLayout(main_panel_layout)

    # =============================================================
    # CAMERA MODE SWITCH
    # =============================================================

    def on_camera_mode_changed(self, index):

        if index == 0:
            self.current_camera_mode = "aruco"
            print("Switched to ArUco stream")

        else:
            self.current_camera_mode = "object"
            print("Switched to Object stream")

    # =============================================================
    # IMAGE UPDATE ROUTING
    # =============================================================

    def update_aruco_image(self, image_data):

        if self.current_camera_mode == "aruco":
            self.camera_feed.update_image(image_data)

    def update_object_image(self, image_data):

        if self.current_camera_mode == "object":
            self.camera_feed.update_image(image_data)

    # =============================================================
    # MAP FUNCTIONS
    # =============================================================

    def _on_mission_pushed(self, waypoint_data):

        try:
            lat = float(waypoint_data["latitude"])
            lon = float(waypoint_data["longitude"])

            wp_id = int(
                waypoint_data.get(
                    "wp_id",
                    len(self.map_viewer.waypoints) + 1
                )
            )

            self.map_viewer.add_waypoint(
                lat,
                lon,
                waypoint_id=wp_id
            )

        except (ValueError, KeyError) as e:
            print(f"Could not pin waypoint: {e}")

    def on_udp_data_received(self, data):

        if self.viewer_panel:
            self.viewer_panel.update_status(data)

    def on_gps_received(self, lat, lon):

        if self.map_viewer:
            self.map_viewer.update_current_position(lat, lon)
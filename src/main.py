import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from ui.dashboard_ui import DashboardUI
from utility.listen_to_udp import UDPListener
from utility.path_history_manager import PathHistoryManager
from utility.mbtiles_server import MBTilesServer
from utility.ros_publisher import CliffRosThread

class AppLogic(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Autonomous Dashboard")
        # self.setWindowIcon(QIcon("/home/labiba-ibnat-matin/Downloads/mongol_barota.png"))  
        # self.resize(1200, 1200)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.ui = DashboardUI()
        self.ui.setup_ui(self.central_widget)
        
        # Initialize path history manager
        self.path_manager = PathHistoryManager()
        self.path_manager.start_new_session()
        self.path_manager.add_event("session_start", "Dashboard started, waiting for GPS data")
        print("Path History Manager initialized")
        
        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        # Start offline tile server if MBTiles file or PNG folder exists
        # Look for .mbtiles file OR tiles folder in assets/
        self.tile_server = None
        tiles_sources = [
            "offline_map.mbtiles",
            "map.mbtiles",
            os.path.join(BASE_DIR, "assets", "map.mbtiles"),
            os.path.join(BASE_DIR, "assets", "tiles"),  # PNG folder with z/x/y structure
            os.path.join(os.path.expanduser("~"), ".cache", "dashboard_map.mbtiles"),
        ]
        
        for tiles_source in tiles_sources:
            if os.path.exists(tiles_source):
                # If it's a directory, ensure it has subdirectories (z levels) and not just live_map.png
                if os.path.isdir(tiles_source):
                    subdirs = [d for d in os.listdir(tiles_source) if os.path.isdir(os.path.join(tiles_source, d))]
                    if not subdirs:
                        continue

                try:
                    self.tile_server = MBTilesServer(tiles_source)
                    self.tile_server.start()
                    # Configure map viewer to use offline tiles
                    self.ui.map_viewer.TILE_SOURCE = 'local'
                    self.ui.map_viewer._build_and_load_map()
                    if os.path.isdir(tiles_source):
                        print(f"✓ Offline PNG tiles loaded from {tiles_source}")
                    else:
                        print(f"✓ Offline map loaded from {tiles_source}")
                    break
                except Exception as e:
                    print(f"Failed to load tiles from {tiles_source}: {e}")
                    self.tile_server = None
        
        if not self.tile_server:
            cached_map = os.path.join(BASE_DIR, "assets", "tiles", "live_map.png")
            if os.path.exists(cached_map):
                print(f"✓ Offline cached map found: {cached_map}")
            else:
                print("ℹ No offline map found. Using online OpenStreetMap (requires internet)")
        
        # Start UDP listener to receive GPS from ReceiverGUI
        self.udp_listener = UDPListener(ip="0.0.0.0", port=5005)
        self.udp_listener.gps_data_received.connect(self.on_gps_received, Qt.ConnectionType.QueuedConnection)
        self.udp_listener.data_received.connect(self.on_udp_data, Qt.ConnectionType.QueuedConnection)
        self.udp_listener.start()
        print("UDP Listener started on port 5005")
        
        # Start ROS thread for cliff detection
        self.ros_thread = CliffRosThread()
        self.ros_thread.start()
        
        # Connect cliff checkbox from UI to ROS thread
        self.ui.input_panel.cliff_checkbox.toggled.connect(self.ros_thread.set_cliff_flag)
        
        # Send initial cliff detection state via UDP
        self.ros_thread.set_cliff_flag(self.ui.input_panel.cliff_checkbox.isChecked())
    
    def on_gps_received(self, lat, lon):
        """Handle GPS data received from rover"""
        self.ui.on_gps_received(lat, lon)
        self.path_manager.add_gps_point(lat, lon)

    def on_udp_data(self, data):
        """Route all UDP data to dashboard (for mission status updates)"""
        self.ui.on_udp_data_received(data)
    
    def closeEvent(self, event):
        """Stop UDP listener when closing and save path history"""
        print("Stopping UDP listener...")
        self.udp_listener.stop()
        self.udp_listener.wait()
        
        print("Stopping ROS thread...")
        self.ros_thread.stop()
        self.ros_thread.wait()
        
        # Stop tile server if running
        if self.tile_server:
            self.tile_server.stop()
        
        # Save path history before exiting
        print("Saving path history...")
        self.path_manager.add_event("session_end", "Dashboard closed")
        saved_file = self.path_manager.save_session()
        stats = self.path_manager.get_path_statistics()
        if stats:
            print(f"Session Statistics: {stats}")
        print(f"Path history saved to: {saved_file}")
        
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AppLogic()
    window.show()
    sys.exit(app.exec())
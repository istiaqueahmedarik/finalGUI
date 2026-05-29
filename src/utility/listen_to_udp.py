import socket
import json
from PyQt6.QtCore import QThread, pyqtSignal


class UDPListener(QThread):
    gps_data_received = pyqtSignal(float, float)
    data_received = pyqtSignal(dict)

    def __init__(self, ip="0.0.0.0", port=5005):
        super().__init__()
        self.ip = ip
        self.port = port
        self.running = True
        self.sock = None

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Allow address reuse
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            self.sock.bind((self.ip, self.port))
            self.sock.settimeout(1.0)

            print(f"✓ Listening for UDP on {self.ip}:{self.port}...")

            while self.running:
                try:
                    data, addr = self.sock.recvfrom(1024)
                    decoded_string = data.decode('utf-8').strip()
                    
                    try:
                        decoded_data = json.loads(decoded_string)
                        self.data_received.emit(decoded_data)
                        
                        # Support both 'lat'/'lon' and 'latitude'/'longitude' key formats
                        if ('lat' in decoded_data and 'lon' in decoded_data):
                            lat = float(decoded_data['lat'])
                            lon = float(decoded_data['lon'])
                            self.gps_data_received.emit(lat, lon)
                        elif ('latitude' in decoded_data and 'longitude' in decoded_data):
                            lat = float(decoded_data['latitude'])
                            lon = float(decoded_data['longitude'])
                            self.gps_data_received.emit(lat, lon)
                            
                    except json.JSONDecodeError:
                        if ',' in decoded_string:
                            parts = decoded_string.split(",")
                            if len(parts) == 2:
                                lat = float(parts[0].strip())
                                lon = float(parts[1].strip())
                                self.gps_data_received.emit(lat, lon)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"UDP Error: {e}")

        except OSError as e:
            print(f"Failed to bind to port {self.port}: {e}")
        finally:
            if self.sock:
                self.sock.close()
                print("UDP listener stopped")

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()
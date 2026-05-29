import socket
import json
from PyQt6.QtCore import QThread, pyqtSignal

class CameraDiscovery(QThread):
    cameras_updated = pyqtSignal(list)

    def __init__(self, listen_port=5000):
        super().__init__()
        self.listen_port = listen_port
        self.running = False
        self.sock = None

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.settimeout(1.0)
        
        try:
            self.sock.bind(('', self.listen_port))
            print(f"[Discovery] Listening on UDP port {self.listen_port}")
        except Exception as e:
            print(f"[Discovery] Failed to bind: {e}")
            return

        self.running = True
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
                message = json.loads(data.decode('utf-8'))
                
                # Check if it's a camera broadcast message
                if message.get('t') in ('cam', 'camera_status'):
                    raw_cams = message.get('cams', [])
                    cameras = []
                    
                    for c in raw_cams:
                        rtsp_url = c.get('u') or c.get('rtsp_url')
                        label = c.get('l') or c.get('label') or rtsp_url
                        codec = c.get('c') or c.get('codec', 'H264')
                        
                        if rtsp_url:
                            cameras.append({
                                'rtsp_url': rtsp_url,
                                'label': label,
                                'codec': codec
                            })
                    
                    if cameras:
                        print(f"[Discovery] Found {len(cameras)} camera streams")
                        self.cameras_updated.emit(cameras)
                        
            except socket.timeout:
                continue
            except Exception as e:
                continue

        if self.sock:
            self.sock.close()

    def stop(self):
        self.running = False
        self.wait()
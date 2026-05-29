import socket
import threading

class TeensySender:
    def __init__(self, ip="192.168.1.177", port=8888):
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.lock = threading.Lock()

    def send(self, cmd: str):
        with self.lock:
            try:
                print(f"[TeensySender] Sending '{cmd}' to {self.ip}:{self.port}")
                self.sock.sendto(cmd.encode(), (self.ip, self.port))
            except Exception as e:
                print(f"[TeensySender] send failed: {e}")

    def send_speed(self, value: int):
        self.send(f"SPEED {value}")

    def set_target(self, ip: str, port: int):
        with self.lock:
            self.ip = ip
            self.port = port
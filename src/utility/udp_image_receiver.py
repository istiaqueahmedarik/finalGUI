import socket
import threading

from PyQt6.QtCore import QObject, pyqtSignal


class UDPImageReceiver(QObject):

    aruco_image_received = pyqtSignal(bytes)
    object_image_received = pyqtSignal(bytes)

    def __init__(self, ip='0.0.0.0', port=5007):

        super().__init__()

        self.ip = ip
        self.port = port
        self.running = False

    def start(self):

        self.running = True

        threading.Thread(
            target=self.listen,
            daemon=True
        ).start()

    def listen(self):

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        sock.bind((self.ip, self.port))

        print(f"Listening on {self.ip}:{self.port}")

        while self.running:

            data, addr = sock.recvfrom(65536)

            try:
                header, image_data = data.split(b'|', 1)

                source = header.decode()

                if source == "ARUCO":
                    self.aruco_image_received.emit(image_data)

                elif source == "OBJECT":
                    self.object_image_received.emit(image_data)

            except Exception as e:
                print("UDP decode error:", e)

    def stop(self):

        self.running = False
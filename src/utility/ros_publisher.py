import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool
from PyQt6.QtCore import QThread
import socket

class CliffPublisherNode(Node):
    def __init__(self):
        super().__init__('cliff_flag_publisher')
        self.publisher_ = self.create_publisher(Bool, '/cliff_flag', 10)
        self.timer = self.create_timer(0.1, self.timer_callback) # 10Hz
        self.cliff_detected = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def timer_callback(self):
        msg = Bool()
        msg.data = bool(self.cliff_detected)
        self.publisher_.publish(msg)
        
        # Constantly send UDP packet to 192.168.2.116 on ports 6017 and 5555 at 10Hz
        try:
            udp_msg = "true" if self.cliff_detected else "false"
            data = udp_msg.encode('utf-8')
            self.sock.sendto(data, ("192.168.2.116", 5555))
        except Exception as e:
            pass

    def destroy_node(self):
        try:
            self.sock.close()
        except Exception:
            pass
        super().destroy_node()

class CliffRosThread(QThread):
    def __init__(self):
        super().__init__()
        self.node = None
        self.cliff_detected = False

    def run(self):
        rclpy.init()
        self.node = CliffPublisherNode()
        self.node.cliff_detected = self.cliff_detected
        try:
            rclpy.spin(self.node)
        except Exception as e:
            pass
        finally:
            if rclpy.ok():
                self.node.destroy_node()
                rclpy.shutdown()

    def set_cliff_flag(self, state: bool):
        self.cliff_detected = state
        if self.node is not None:
            self.node.cliff_detected = state
        
        # Send immediate UDP packet to 192.168.2.116:6017 and 192.168.2.116:5555 as 'true' or 'false'
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            msg = "true" if state else "false"
            data = msg.encode('utf-8')
            sock.sendto(data, ("192.168.2.116", 6017))
            sock.sendto(data, ("192.168.2.116", 5555))
            print(f"[UDP] Sent cliff state '{msg}' to 192.168.2.116:6017 and 192.168.2.116:5555")
            sock.close()
        except Exception as e:
            print(f"[UDP] Failed to send cliff state via UDP: {e}")

    def stop(self):
        if self.node:
            self.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

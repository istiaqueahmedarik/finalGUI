import socket
import json


def send_udp_data(data_dict, ip="192.168.2.116", port=5006): #this is orin's ip and orin' port 
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    message = json.dumps(data_dict).encode('utf-8')

    try:
        host_name = socket.gethostname()
        # Resolve the hostname to an IPv4 address
        # Note: This might return the loopback address (127.0.0.1) in some configurations
        host_ip = socket.gethostbyname(host_name)
        print(host_ip)
        sock.sendto(message, (ip, port))
        print(f"Sent: {data_dict} to {ip}:{port}")
    finally:
        sock.close()

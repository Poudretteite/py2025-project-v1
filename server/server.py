import socket
import json
import threading
from datetime import datetime
from logger import Logger

class NetworkServer:
    def __init__(self, port: int, logger: Logger):
        self.port = port
        self.logger = logger

    def start(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind(("0.0.0.0", self.port))
            server_socket.listen()
            print(f"[SERVER] Listening on port {self.port}...")

            while True:
                client_socket, addr = server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client_socket, addr)).start()

    def _handle_client(self, client_socket, addr) -> None:
        with client_socket:
            try:
                raw_data = b""
                while not raw_data.endswith(b"\n"):
                    chunk = client_socket.recv(1024)
                    if not chunk:
                        return
                    raw_data += chunk

                data = json.loads(raw_data.decode("utf-8"))
                self._process_data(data)
                client_socket.sendall(b"ACK\n")
            except Exception as e:
                print(f"[{addr}] Error: {e}")

    def _process_data(self, data: dict) -> None:
        try:
            timestamp = datetime.fromisoformat(data["timestamp"])
            sensor_id = data["sensor_id"]
            value = float(data["value"])
            unit = data["unit"]

            self.logger.log_reading(
                sensor_id=sensor_id,
                timestamp=timestamp,
                value=value,
                unit=unit
            )
        except (KeyError, ValueError) as e:
            print(f"[ERROR] Invalid data format: {e}")

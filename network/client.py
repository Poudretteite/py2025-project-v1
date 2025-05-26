import socket
import json
import time
import logging
from network.config import load_config

class NetworkClient:
    def __init__(self, host=None, port=None, timeout=5.0, retries=3):
        config = load_config()
        self.host = host or config['host']
        self.port = port or config['port']
        self.timeout = timeout or config['timeout']
        self.retries = retries or config['retries']
        self.sock = None
        self.logger = logging.getLogger("NetworkClient")

    def connect(self) -> None:
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            self.logger.info(f"Connected to {self.host}:{self.port}")
        except socket.error as e:
            self.logger.error(f"Connection failed: {e}")
            raise

    def send(self, data: dict) -> bool:
        payload = self._serialize(data)
        for attempt in range(1, self.retries + 1):
            try:
                self.sock.sendall(payload + b'\n')
                self.logger.info(f"Sent: {data}")

                ack = self.sock.recv(1024).decode().strip()
                if ack == "ACK":
                    self.logger.info("Acknowledgment received.")
                    return True
                else:
                    self.logger.error("Invalid ACK response.")
            except socket.error as e:
                self.logger.error(f"Attempt {attempt}: send failed ({e})")
                time.sleep(1)

        return False

    def close(self) -> None:
        if self.sock:
            self.sock.close()
            self.logger.info("Connection closed.")

    def _serialize(self, data: dict) -> bytes:
        return json.dumps(data).encode('utf-8')

    def _deserialize(self, raw: bytes) -> dict:
        return json.loads(raw.decode('utf-8'))
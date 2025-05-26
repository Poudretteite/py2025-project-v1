import unittest
from network.client import NetworkClient

class TestNetworkClient(unittest.TestCase):
    def test_serialize(self):
        client = NetworkClient()
        data = {"sensor_id": "temp1", "value": 23.5}
        serialized = client._serialize(data)
        self.assertEqual(serialized, b'{"sensor_id": "temp1", "value": 23.5}')

    def test_deserialize(self):
        client = NetworkClient()
        raw = b'{"sensor_id": "temp1", "value": 23.5}'
        deserialized = client._deserialize(raw)
        self.assertEqual(deserialized, {"sensor_id": "temp1", "value": 23.5})

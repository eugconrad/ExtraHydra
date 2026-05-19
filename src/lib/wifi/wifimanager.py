import network
import time

from hydra.config import Config
from hydra.utils import get_instance

_MAX_WIFI_ATTEMPTS = const(1000)


class WiFiManager:
    def __init__(self):
        self.nic = None
        self.config = get_instance(Config)
        self.attempts = 0

    def initialize(self):
        try:
            self.nic = network.WLAN(network.STA_IF)
            return True
        except RuntimeError as e:
            print(f"WiFi init error: {e}")
            return False

    def connect(self, wifi_ssid=None, wifi_pass=None):
        if not self.nic:
            if not self.initialize():
                return False

        if not self.nic.isconnected():
            try:
                self.nic.active(True)
                self.nic.connect(
                    wifi_ssid or self.config['wifi_ssid'],
                    wifi_pass or self.config['wifi_pass']
                )

                while not self.nic.isconnected() and self.attempts < _MAX_WIFI_ATTEMPTS:
                    time.sleep_ms(100)
                    self.attempts += 1

                return self.nic.isconnected()
            except Exception as e:
                print(f"WiFi connection error: {e}")
                return False
        return True

    def disconnect(self):
        if self.nic:
            self.nic.disconnect()
            self.nic.active(False)
            return True
        return False

    def is_connected(self):
        return self.nic and self.nic.isconnected()

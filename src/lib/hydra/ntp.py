import ntptime
import machine
import time

from hydra.config import Config
from hydra.utils import get_instance
from lib.wifi import WiFiManager

_MAX_NTP_ATTEMPTS = const(10)


class TimeSync:
    def __init__(self):
        self.wifi = get_instance(WiFiManager)
        self.rtc = machine.RTC()
        self.config = get_instance(Config)
        self.attempts = 0

    def sync_time(self):
        if not self.wifi.initialize():
            return False

        try:
            if not self.wifi.connect():
                return False

            ntptime.settime()
            self.apply_timezone()
            return True

        except Exception as e:
            print(f"NTP sync error: {e}")
            return False
        finally:
            self.wifi.disconnect()

    def apply_timezone(self):
        if self.rtc.datetime()[0] != 2000:
            time_list = list(self.rtc.datetime())
            time_list[4] += self.config["timezone"]
            self.rtc.datetime(tuple(time_list))

    def safe_sync(self):
        while self.attempts < _MAX_NTP_ATTEMPTS:
            if self.sync_time():
                return True
            self.attempts += 1
            time.sleep(1)
        return False

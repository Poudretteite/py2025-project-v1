import random
import time
from datetime import datetime
from typing import Callable, List

class Sensor:
    def __init__(self, sensor_id, name, unit, min_value, max_value, frequency=1):
        """
        Inicjalizacja czujnika.

        :param sensor_id: Unikalny identyfikator czujnika
        :param name: Nazwa lub opis czujnika
        :param unit: Jednostka miary (np. '°C', '%', 'hPa', 'lux')
        :param min_value: Minimalna wartość odczytu
        :param max_value: Maksymalna wartość odczytu
        :param frequency: Częstotliwość odczytów (sekundy)
        """
        self.sensor_id = sensor_id
        self.name = name
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.frequency = frequency
        self.active = True
        self.last_value = None
        self.history = []
        self._callbacks: List[Callable[[str, datetime, float, str], None]] = []

    def register_callback(self, callback: Callable[[str, datetime, float, str], None]) -> None:
        """Rejestruje funkcję callback (np. logger.log_reading)."""
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[str, datetime, float, str], None]) -> None:
        """Usuwa callback z listy."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self, value: float) -> None:
        """Wywołuje wszystkie zarejestrowane callbacki."""
        timestamp = datetime.now()
        for callback in self._callbacks:
            try:
                callback(self.sensor_id, timestamp, value, self.unit)
            except Exception as e:
                print(f"Błąd callbacka: {e}")

    def read_value(self):
        """
        Symuluje pobranie odczytu z czujnika.
        W klasie bazowej zwraca losową wartość z przedziału [min_value, max_value].
        """
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")

        value = random.uniform(self.min_value, self.max_value)
        self.last_value = value
        self.history.append(value)

        self._notify_callbacks(value)  # Powiadomienie loggera/obserwatorów
        return value

    def calibrate(self, calibration_factor):
        """
        Kalibruje ostatni odczyt przez przemnożenie go przez calibration_factor.
        Jeśli nie wykonano jeszcze odczytu, wykonuje go najpierw.
        """
        if self.last_value is None:
            self.read_value()

        self.last_value *= calibration_factor
        return self.last_value

    def get_last_value(self):
        """
        Zwraca ostatnią wygenerowaną wartość, jeśli była wygenerowana.
        """
        if self.last_value is None:
            return self.read_value()
        return self.last_value

    def start(self):
        """
        Włącza czujnik.
        """
        self.active = True

    def stop(self):
        """
        Wyłącza czujnik.
        """
        self.active = False

    def __str__(self):
        return f"Sensor(id={self.sensor_id}, name={self.name}, unit={self.unit})"


class LightSensor(Sensor):
    def __init__(self, sensor_id = "1", name="Light Sensor", unit="lux", min_value=0, max_value=10000, frequency=1, daytime="day"):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)
        self.daytime = daytime

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")

        if self.daytime == "day":
            value = random.uniform(self.max_value/3, self.max_value)
        elif self.daytime == "night":
            value = random.uniform(self.min_value, self.max_value/3)
        else:
            raise Exception("Nieprawidłowy czas dnia.")

        self.last_value = value
        self.history.append(self.last_value)

        super()._notify_callbacks(value)
        return value

class TemperatureSensor(Sensor):
    def __init__(self, sensor_id = "2", name="Temperature Sensor", unit="C", min_value=-20, max_value=50, frequency=1, daytime="day", season="summer"):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)
        self.daytime = daytime
        self.season = season

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")

        if self.season == "spring":
            value = random.uniform(self.min_value-0.6*self.min_value, self.max_value-0.8*self.max_value)
        elif self.season == "summer":
            value = random.uniform(self.min_value-2*self.min_value, self.max_value)
        elif self.season == "autumn":
            value = random.uniform(self.min_value-0.8*self.min_value, self.max_value-0.7*self.max_value)
        elif self.season == "winter":
            value = random.uniform(self.min_value, self.max_value-0.9*self.max_value)
        else:
            raise Exception("Nieprawidłowy sezon.")

        if self.daytime == "day":
            pass
        elif self.daytime == "night":
            value = value - 10
        else:
            raise Exception("Nieprawidłowy czas dnia.")

        self.last_value = value
        self.history.append(self.last_value)

        super()._notify_callbacks(value)
        return value

class HumiditySensor(Sensor):
    def __init__(self, sensor_id = "3", name="Humidity Sensor", unit="%", min_value=0, max_value=100, frequency=1, temperature=25):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)
        self.temperature = temperature

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")

        if self.temperature > -20 and self.temperature <= 10:
            value = random.uniform(self.min_value+self.max_value*0.5, self.max_value*0.8)
        elif self.temperature > 10 and self.temperature <= 25:
            value = random.uniform(self.min_value+self.max_value*0.3, self.max_value*0.6)
        elif self.temperature > 25 and self.temperature <= 40:
            value = random.uniform(self.min_value+self.max_value*0.2, self.max_value*0.4)
        else:
            raise Exception("Nieprawidłowa temperatura.")

        self.last_value = value
        self.history.append(self.last_value)

        super()._notify_callbacks(value)
        return value

class AirQualitySensor(Sensor):
    def __init__(self, sensor_id = "4", name="Air Quality Sensor", unit="AQI", min_value=0, max_value=500, frequency=1):
        super().__init__(sensor_id, name, unit, min_value, max_value, frequency)

    def read_value(self):
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")
        value = random.uniform(self.min_value, self.max_value)
        self.last_value = value

        super()._notify_callbacks(value)
        return value

if __name__ == "__main__":
    sensor = LightSensor(daytime="night")
    while True:
        print(sensor.read_value())
        time.sleep(1)

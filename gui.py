import tkinter as tk
from tkinter import ttk, messagebox
import yaml
from datetime import datetime, timedelta

from sensors import Sensor, LightSensor, TemperatureSensor, HumiditySensor, AirQualitySensor

CONFIG_FILE = "config.yaml"

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Server GUI")
        self.running = False
        self.sensors = []
        self.history = {}

        self.load_config()
        self.build_gui()

    def load_config(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception:
            self.config = {"port": 5000}
        self.port_var = tk.StringVar(value=str(self.config.get("port", 5000)))

    def save_config(self):
        self.config["port"] = int(self.port_var.get())
        with open(CONFIG_FILE, 'w') as f:
            yaml.safe_dump(self.config, f)

    def build_gui(self):
        # Górny panel (start/stop, port)
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(top_frame, text="Port:").pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.port_var, width=6).pack(side=tk.LEFT, padx=5)

        self.start_button = tk.Button(top_frame, text="Start", command=self.start_server)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(top_frame, text="Stop", command=self.stop_server, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)

        # Środkowa część – tabela czujników
        columns = ("sensor", "last_value", "unit", "timestamp", "avg_1h", "avg_12h")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=120)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Dolny panel – status
        self.status_var = tk.StringVar(value="Serwer zatrzymany")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X)

    def start_server(self):
        try:
            port = int(self.port_var.get())
            self.save_config()

            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set(f"Serwer nasłuchuje na porcie {port}...")

            self.init_sensors()
            self.update_loop()
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def stop_server(self):
        self.running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Serwer zatrzymany")

    def init_sensors(self):
        self.sensors = [
            LightSensor(daytime="night"),
            TemperatureSensor(season="summer"),
            HumiditySensor(temperature=25),
            AirQualitySensor()
        ]
        for sensor in self.sensors:
            sensor.start()
            sensor.register_callback(self.log_reading)
            self.history[sensor.sensor_id] = []

    def log_reading(self, sensor_id, timestamp, value, unit):
        if sensor_id not in self.history:
            self.history[sensor_id] = []
        self.history[sensor_id].append((timestamp, value))
        # Ogranicz rozmiar historii do ostatnich 12h
        self.history[sensor_id] = [
            (ts, val) for ts, val in self.history[sensor_id]
            if ts > datetime.now() - timedelta(hours=12)
        ]

    def update_loop(self):
        if not self.running:
            return

        for sensor in self.sensors:
            try:
                sensor.read_value()
            except Exception as e:
                self.status_var.set(f"Błąd: {str(e)}")

        self.update_table()
        self.root.after(3000, self.update_loop)

    def calculate_average(self, sensor_id, hours):
        now = datetime.now()
        values = [
            val for ts, val in self.history.get(sensor_id, [])
            if ts > now - timedelta(hours=hours)
        ]
        if not values:
            return "-"
        return f"{sum(values)/len(values):.2f}"

    def update_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for sensor in self.sensors:
            sensor_id = sensor.sensor_id
            value = sensor.get_last_value()
            unit = sensor.unit
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            avg_1h = self.calculate_average(sensor_id, 1)
            avg_12h = self.calculate_average(sensor_id, 12)

            self.tree.insert("", "end", values=(
                sensor_id,
                f"{value:.2f}",
                unit,
                timestamp,
                avg_1h,
                avg_12h
            ))


if __name__ == "__main__":
    root = tk.Tk()
    gui = ServerGUI(root)
    root.mainloop()

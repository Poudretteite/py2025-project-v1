import tkinter as tk
from tkinter import ttk, messagebox
import yaml
from datetime import datetime, timedelta
from server.server import NetworkServer  # Your existing server class
from logger import Logger  # Your logging class

# Import or define your sensor classes (simulated sensors)
from sensors import Sensor, LightSensor, TemperatureSensor, HumiditySensor, AirQualitySensor

CONFIG_FILE = "config.yaml"

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Network Server GUI")
        self.running = False
        self.sensors = []
        self.history = {}
        self.network_server = None
        self.logger = Logger("config.json")

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
        # Top panel (start/stop, port)
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(top_frame, text="Port:").pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.port_var, width=6).pack(side=tk.LEFT, padx=5)

        self.start_button = tk.Button(top_frame, text="Start", command=self.start_server)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(top_frame, text="Stop", command=self.stop_server, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)

        # Middle part – sensor table
        columns = ("sensor", "last_value", "unit", "timestamp", "avg_1h", "avg_12h")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=10)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=120)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Bottom panel – status bar
        self.status_var = tk.StringVar(value="Server stopped")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X)

    def start_server(self):
        try:
            port = int(self.port_var.get())
            self.save_config()

            # Stop existing server if any
            if self.network_server is not None:
                self.network_server.stop()

            # Create and start network server with callback
            self.network_server = NetworkServer(port=port, on_data_received=self.on_data_received)
            self.network_server.start()

            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set(f"Server listening on port {port}...")

            # Initialize simulated sensors (optional, can be skipped)
            self.init_sensors()

            # Start GUI update loop
            self.update_loop()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def stop_server(self):
        self.running = False
        if self.network_server:
            self.network_server.stop()
            self.network_server = None

        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Server stopped")

    def init_sensors(self):
        # Optional simulated sensors (can comment out if using only network data)
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

        cutoff = datetime.now() - timedelta(hours=12)
        self.history[sensor_id] = [(ts, val) for ts, val in self.history[sensor_id] if ts > cutoff]

        self.logger.log_reading(sensor_id, timestamp, value, unit)

    def on_data_received(self, data):
        # Called from NetworkServer thread — use root.after for thread safety
        def handle():
            try:
                timestamp = datetime.fromisoformat(data["timestamp"])
                sensor_id = data["sensor_id"]
                value = float(data["value"])
                unit = data["unit"]

                # Log the reading
                self.logger.log_reading(sensor_id, timestamp, value, unit)

                # Update history for averages
                if sensor_id not in self.history:
                    self.history[sensor_id] = []
                self.history[sensor_id].append((timestamp, value))
                cutoff = datetime.now() - timedelta(hours=12)
                self.history[sensor_id] = [(ts, val) for ts, val in self.history[sensor_id] if ts > cutoff]

                # Update simulated sensor last value if exists
                for sensor in self.sensors:
                    if sensor.sensor_id == sensor_id:
                        sensor._last_value = value

                self.update_table()

            except Exception as e:
                print(f"Error processing incoming data: {e}")

        self.root.after(0, handle)

    def update_loop(self):
        if not self.running:
            return

        for sensor in self.sensors:
            try:
                sensor.read_value()
            except Exception as e:
                self.status_var.set(f"Error: {str(e)}")

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
        # Clear table
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Insert rows
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

    def on_closing(self):
        self.running = False
        if self.network_server:
            self.network_server.stop()
        self.logger.stop()  # Make sure logs are flushed and file closed
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    gui = ServerGUI(root)
    root.protocol("WM_DELETE_WINDOW", gui.on_closing)  # Proper cleanup on close
    root.mainloop()

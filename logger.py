import os
import json
import csv
from datetime import datetime, timedelta
from typing import Dict, Iterator, Optional
import zipfile
import glob


class Logger:
    def __init__(self, config_path: str):
        """
        Inicjalizuje logger na podstawie pliku JSON.
        :param config_path: Ścieżka do pliku konfiguracyjnego (.json)
        """
        # Wczytanie konfiguracji
        with open(config_path) as f:
            config = json.load(f)

        self.log_dir = config["log_dir"]
        self.filename_pattern = config["filename_pattern"]
        self.buffer_size = config["buffer_size"]
        self.rotate_every_hours = config.get("rotate_every_hours", 24)
        self.max_size_mb = config.get("max_size_mb", 10)
        self.rotate_after_lines = config.get("rotate_after_lines", 100000)
        self.retention_days = config.get("retention_days", 30)

        # Utworzenie katalogów jeśli nie istnieją
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(os.path.join(self.log_dir, "archive"), exist_ok=True)

        # Inicjalizacja bufora i stanu
        self.buffer = []
        self.current_file = None
        self.current_writer = None
        self.current_filename = None
        self.last_rotation_time = None
        self.line_count = 0

        # Otwarcie pliku
        self.start()

    def start(self) -> None:
        """
        Otwiera nowy plik CSV do logowania. Jeśli plik jest nowy, zapisuje nagłówek.
        """
        # Generowanie nazwy pliku na podstawie wzorca
        self.current_filename = datetime.now().strftime(self.filename_pattern)
        filepath = os.path.join(self.log_dir, self.current_filename)

        # Sprawdzenie czy plik istnieje (czy trzeba dodać nagłówek)
        file_exists = os.path.exists(filepath)

        # Otwarcie pliku w trybie append
        self.current_file = open(filepath, 'a', newline='')
        self.current_writer = csv.writer(self.current_file)

        # Jeśli plik nie istniał, dodaj nagłówek
        if not file_exists:
            self.current_writer.writerow(["timestamp", "sensor_id", "value", "unit"])
            self.line_count = 0

        # Ustawienie czasu ostatniej rotacji
        self.last_rotation_time = datetime.now()

    def stop(self) -> None:
        """
        Wymusza zapis bufora i zamyka bieżący plik.
        """
        if self.buffer:
            self._flush_buffer()

        if self.current_file:
            self.current_file.close()
            self.current_file = None
            self.current_writer = None

    def log_reading(
            self,
            sensor_id: str,
            timestamp: datetime,
            value: float,
            unit: str
    ) -> None:
        """
        Dodaje wpis do bufora i ewentualnie wykonuje rotację pliku.
        """
        # Dodanie wpisu do bufora
        self.buffer.append((timestamp, sensor_id, value, unit))

        # Sprawdzenie czy trzeba wywołać flush
        if len(self.buffer) >= self.buffer_size:
            self._flush_buffer()

        # Sprawdzenie warunków rotacji
        self._check_rotation()

    def read_logs(
            self,
            start: datetime,
            end: datetime,
            sensor_id: Optional[str] = None
    ) -> Iterator[Dict]:
        """
        Pobiera wpisy z logów zadanego zakresu i opcjonalnie konkretnego czujnika.
        """
        # Przeszukanie bieżących plików CSV
        for csv_file in glob.glob(os.path.join(self.log_dir, "*.csv")):
            yield from self._read_log_file(csv_file, start, end, sensor_id)

        # Przeszukanie archiwalnych plików ZIP
        for zip_file in glob.glob(os.path.join(self.log_dir, "archive", "*.zip")):
            yield from self._read_zip_file(zip_file, start, end, sensor_id)

    def _flush_buffer(self) -> None:
        """Zapisuje zawartość bufora do pliku."""
        if not self.buffer or not self.current_writer:
            return

        for entry in self.buffer:
            self.current_writer.writerow(entry)
            self.line_count += 1

        self.current_file.flush()
        self.buffer.clear()

    def _check_rotation(self) -> None:
        """Sprawdza warunki rotacji i wykonuje ją jeśli potrzeba."""
        if not self.current_file:
            return

        current_time = datetime.now()
        need_rotation = False

        # Sprawdzenie warunków rotacji
        if self.rotate_every_hours and self.last_rotation_time:
            hours_since_last_rotation = (current_time - self.last_rotation_time).total_seconds() / 3600
            if hours_since_last_rotation >= self.rotate_every_hours:
                need_rotation = True

        if self.max_size_mb:
            file_size_mb = os.path.getsize(self.current_file.name) / (1024 * 1024)
            if file_size_mb >= self.max_size_mb:
                need_rotation = True

        if self.rotate_after_lines and self.line_count >= self.rotate_after_lines:
            need_rotation = True

        if need_rotation:
            self._rotate()

    def _rotate(self) -> None:
        """Wykonuje rotację pliku logu."""
        self.stop()
        self._archive_current_file()
        self._clean_old_archives()
        self.start()

    def _archive_current_file(self) -> None:
        """Archiwizuje bieżący plik logu."""
        if not self.current_filename:
            return

        source_path = os.path.join(self.log_dir, self.current_filename)
        if not os.path.exists(source_path):
            return

        # Utworzenie nazwy archiwum (z datą utworzenia)
        creation_time = datetime.fromtimestamp(os.path.getctime(source_path))
        archive_name = f"{creation_time.strftime('%Y%m%d_%H%M%S')}_{self.current_filename}.zip"
        archive_path = os.path.join(self.log_dir, "archive", archive_name)

        # Kompresja do ZIP
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(source_path, arcname=self.current_filename)

        # Usunięcie oryginalnego pliku
        os.remove(source_path)

    def _clean_old_archives(self) -> None:
        """Usuwa archiwa starsze niż retention_days dni."""
        archive_dir = os.path.join(self.log_dir, "archive")
        cutoff_time = datetime.now() - timedelta(days=self.retention_days)

        for archive in glob.glob(os.path.join(archive_dir, "*.zip")):
            creation_time = datetime.fromtimestamp(os.path.getctime(archive))
            if creation_time < cutoff_time:
                os.remove(archive)

    def _read_log_file(
            self,
            filepath: str,
            start: datetime,
            end: datetime,
            sensor_id: Optional[str] = None
    ) -> Iterator[Dict]:
        """Odczytuje wpisy z pojedynczego pliku CSV."""
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Pominięcie nagłówka

            for row in reader:
                if len(row) != 4:
                    continue

                try:
                    timestamp = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f")
                    row_sensor_id = row[1]
                    value = float(row[2])
                    unit = row[3]

                    # Filtrowanie wyników
                    if start <= timestamp <= end:
                        if sensor_id is None or row_sensor_id == sensor_id:
                            yield {
                                "timestamp": timestamp,
                                "sensor_id": row_sensor_id,
                                "value": value,
                                "unit": unit
                            }
                except (ValueError, IndexError):
                    continue

    def _read_zip_file(
            self,
            filepath: str,
            start: datetime,
            end: datetime,
            sensor_id: Optional[str] = None
    ) -> Iterator[Dict]:
        """Odczytuje wpisy z pojedynczego pliku ZIP."""
        with zipfile.ZipFile(filepath, 'r') as zipf:
            # Zakładamy, że w ZIPie jest tylko jeden plik
            for filename in zipf.namelist():
                if not filename.endswith('.csv'):
                    continue

                with zipf.open(filename) as f:
                    # Konwersja do tekstu
                    content = f.read().decode('utf-8').splitlines()
                    reader = csv.reader(content)
                    next(reader)  # Pominięcie nagłówka

                    for row in reader:
                        if len(row) != 4:
                            continue

                        try:
                            timestamp = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S.%f")
                            row_sensor_id = row[1]
                            value = float(row[2])
                            unit = row[3]

                            # Filtrowanie wyników
                            if start <= timestamp <= end:
                                if sensor_id is None or row_sensor_id == sensor_id:
                                    yield {
                                        "timestamp": timestamp,
                                        "sensor_id": row_sensor_id,
                                        "value": value,
                                        "unit": unit
                                    }
                        except (ValueError, IndexError):
                            continue
import json

class Logger:
    def __int__(self, config_path: str):
        self.config_path = config_path

        with open(self.config_path, "r") as f:
            self.config = json.load(f)

        

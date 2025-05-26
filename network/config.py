import yaml
import os
print("Current working directory:", os.getcwd())

def load_config(path: str = None) -> dict:
    if path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, 'config.yaml')
    print("Loading config from:", path)
    with open(path, 'r') as f:
        return yaml.safe_load(f)
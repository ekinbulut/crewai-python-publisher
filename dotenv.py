import os

def load_dotenv(dotenv_path: str = '.env', override: bool = False) -> bool:
    """Simple dotenv loader. Reads key=value lines into os.environ."""
    try:
        with open(dotenv_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, value = line.split('=', 1)
                if override or key not in os.environ:
                    os.environ[key] = value
        return True
    except FileNotFoundError:
        return False

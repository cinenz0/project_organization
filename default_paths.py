from pathlib import Path

CONFIG_FILE = 'path.txt'

def get_default_path():
    try:
        with open(CONFIG_FILE) as f:
            default_path = f.readline().strip()
            if default_path == r'\\n':
                raise FileNotFoundError
            return Path(default_path)
    except FileNotFoundError:
        return Path.home() / 'Desktop'

def get_default_path_dst():
    try:
        with open(CONFIG_FILE) as dst:
            lines = dst.readlines()
            dst_path = lines[1]
            print(Path(dst_path))
            return Path(dst_path)
    except (FileNotFoundError, IndexError):
        return Path.home() / 'Desktop'
    

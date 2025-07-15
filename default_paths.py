from pathlib import Path
import json

SRC_KEY = "source path"
DST_KEY = "destination path"
DEFAULT_PATH = str(Path.home() / 'Desktop')
CONFIG_FILE = 'config.json'

def paths():
    try:
        with open(CONFIG_FILE) as f:
            pathings = json.load(f)
            source_path = no_path_file(pathings[SRC_KEY])
            destination_path = no_path_file(pathings[DST_KEY])
            return source_path, destination_path
    except (json.decoder.JSONDecodeError, FileNotFoundError):
        source_path = save_new_empty_json(SRC_KEY, DEFAULT_PATH)
        destination_path = save_json(DST_KEY, DEFAULT_PATH)
        return source_path, destination_path

def save_new_empty_json (key,value):
    data = {}
    data[key] = value
    with open (CONFIG_FILE, 'w') as file:
        json.dump(data, file, indent = 4)  

def save_json(key,value):
    with open(CONFIG_FILE) as f:
        data = json.load(f)
        data[key] = value
    with open (CONFIG_FILE, 'w') as file:
        json.dump(data, file, indent = 4)  
def no_path_file(path):
    if path == '':
        return DEFAULT_PATH
    return path
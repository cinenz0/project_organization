
import argparse
import json
from pathlib import Path
from default_paths import paths

source, destination = paths()

CONFIG_FILE = 'config.json'
SRC_KEY = "source path"
DST_KEY = "destination path"

def prompt(default, key):
    result = prompting(key, default)
    return (Path(result))

def prompting(key,default):
    user_path = input(f'{key} path (blank to use default): ')
    if user_path == '':
        return default
    elif not Path(user_path).exists():
        raise FileNotFoundError
    
    while True:
        defaulting = input('Would you like to meke this your default path? ').lower()
        if defaulting in ['y','yes']:
            save_path(key,user_path)
            break
        elif defaulting in ['n','no']:
            break
        else:
            print('Invalid answer, [Y]es or [N]o, please')
            continue
        
    return user_path

def save_path(key, value):
    with open(CONFIG_FILE) as f:
        data = json.load(f)
        data[key] = value
    with open (CONFIG_FILE, 'w') as file:
        json.dump(data, file, indent = 4)
            

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-sd', '--set-default', action='store_true', help='Sets the chosen path to be the default path of file sorting')
    parser.add_argument('-s', '--source', help='The source directory to organize')
    parser.add_argument('-d', '--destination', help='The destination directory')
    args = parser.parse_args()
    source_path = None
    destination_path = None

    # Check for source path independently
    if args.source:
        path = Path(args.source)
        if path.exists():
            source_path = path
        else:
            print(f"Error: Provided source path does not exist: {path}")

    # Check for destination path independently
    if args.destination:
        path = Path(args.destination)
        if path.exists():
            destination_path = path
        else:
            print(f"Error: Provided destination path does not exist: {path}")

    # Handle the -sd flag
    if args.set_default:
        # You could add logic here to only save paths that were successfully found
        print("Saving new default paths...")
        if source_path:
            save_path(SRC_KEY, args.source)
        if destination_path:
            save_path(DST_KEY, args.destination)
    
    # Return what was found, which might be one, both, or neither.
    return source_path, destination_path

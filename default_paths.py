import sys
import re
import argparse
from pathlib import Path
from data_dict import data_dict


def get_default_path():
    try:
        with open(CONFIG_FILE) as f:
            default_path = f.readline().strip()
            return Path(default_path)
    except FileNotFoundError:
        return Path.home() / 'Desktop'



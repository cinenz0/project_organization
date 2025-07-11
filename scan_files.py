
import re

from pathlib import Path


def scan_files(directory):
    files =  [f for f in directory.iterdir() if f.is_file()]
    pattern = (r'[^\\]+$')
    files_list = []
    for file in files:
        files_list +=  re.findall(pattern, str(file)) 
    return files_list
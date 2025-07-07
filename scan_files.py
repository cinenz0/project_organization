import sys
import re
import argparse
from pathlib import Path
from data_dict import data_dict

def scan_files(directory):
    files =  [f for f in directory.iterdir() if f.is_file()]
    pattern = (r'[^\\]+$')
    files_list = []
    for file in files:
        files_list +=  re.findall(pattern, str(file)) 
    return files_list
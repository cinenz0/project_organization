
'''    
Asks the user for the directory to be organized
    If given a -d or --defaut flag, saves the path in a separate file 
        If user doesnt provide any directory does it on desktop by defaut or on the defaut directory previously set✅

Scans the directory  for files ending in a pattern like .pdf or .docx or .csv based on a dictornary which associetes 
file types and file extenssions ✅
    If there isn't a folder called "Documents" or smthing like that the program creates one and inside this folder it creates a new folder for
    each of the file types found on the chosen directory ✅
'''

import sys
import re
import argparse
from pathlib import Path
from data_dict import data_dict
from organize_by_suffix import organize_by_sufix
from paths import get_default_path, parse_args, prompt_for_path
from scan_files import scan_files



def main():
    try:
        default = get_default_path()
        if len(sys.argv)> 1:
            directory = parse_args()
        else:
            directory = prompt_for_path(default)
        list_of_files = scan_files(directory)
        organize_by_sufix(list_of_files, directory)
    except FileNotFoundError:
        sys.exit('Invalid file path')
       
if __name__ == '__main__':
    main()
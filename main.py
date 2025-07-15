import sys
from pathlib import Path
from data_dict import data_dict
from organize_by_suffix import organize_by_sufix
from paths import parse_args, prompt
from default_paths import paths


SRC_KEY = "source path"
DST_KEY = "destination path"

def main():
    try:
        src, dst = paths()
        if len(sys.argv)> 1:
            directory, dst_directory = parse_args()
        else:
            directory = prompt(src, SRC_KEY)
            dst_directory  = prompt(dst, DST_KEY)
        #print(f'default {default}, dst {dst}, directory {directory}, dst_directory {dst_directory}')
        organize_by_sufix(original_directory = directory, dst_directory = dst_directory)
    except FileNotFoundError:
        sys.exit('Invalid file path')
       
if __name__ == '__main__':
    main()
import sys
from pathlib import Path
from data_dict import data_dict
from organize_by_suffix import organize_by_sufix
from paths import parse_args, prompt_for_path, prompt_for_dst_path
from default_paths import get_default_path,get_default_path_dst
from scan_files import scan_files



def main():
    try:
        default, dst = get_default_path(), get_default_path_dst()
        if len(sys.argv)> 1:
            directory = parse_args()
        else:
            directory, dst_directory  = prompt_for_path(default), prompt_for_dst_path(dst)
        #print(f'default {default}, dst {dst}, directory {directory}, dst_directory {dst_directory}')
        list_of_files = scan_files(directory)
        organize_by_sufix(list_of_files,original_directory = directory, dst_directory = dst_directory)
    except FileNotFoundError:
        sys.exit('Invalid file path')
       
if __name__ == '__main__':
    main()
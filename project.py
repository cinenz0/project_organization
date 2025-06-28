
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

CONFIG_FILE = 'path.txt'

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

def get_default_path():
    try:
        with open(CONFIG_FILE) as f:
            default_path = f.readline().strip()
            return Path(default_path)
    except FileNotFoundError:
        return Path.home() / 'Desktop'

def prompt_for_path(default_path):

    user_path = input('Path to orginize (blank to use default): ')
    if user_path == '':
        return Path(default_path)
    elif not Path(user_path).exists():
        raise FileNotFoundError

    while True:
        defaulting = input('Would you like to meke this your default path? ').lower()
        if defaulting in ['y','yes']:
            with open (CONFIG_FILE, 'w') as new_file:
                 new_file.write(user_path)
            break
        elif defaulting in ['n','no']:
            break
        else:
            print('Invalid answer, [Y]es or [N]o, please')
            continue
    
    return Path(user_path)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-sd', '--set-default', action='store_true', help='Sets the chosen path to be the default path of file sorting')
    parser.add_argument('path', nargs = '?', help = 'Type the path to the directory you want to organize' )
    args = parser.parse_args()

    if args.set_default and args.path:
        with open(CONFIG_FILE, 'w') as f:
            f.write(args.path)    
        print(f'The default path to organize has been changed to: {args.path}')       
        return Path(args.path)

    elif args.path:
        return Path(args.path)
    
    stored_path = get_default_path()
    if stored_path:
        print(f'Using default path:{stored_path}')
        return Path(stored_path)


def scan_files(directory):
    
    files =  [f for f in directory.iterdir() if f.is_file()]
    pattern = (r'[^\\]+$')
    files_list = []
    for file in files:
        files_list +=  re.findall(pattern, str(file)) 
    return files_list

def organize_by_sufix(list_of_files, directory):
    
    documents_folder = directory / 'Documents'
    documents_folder.mkdir(exist_ok = True)
    for file in list_of_files:
        path_file = Path(file)
        for unique_type in data_dict:
            if path_file.suffix in unique_type['Suffixes']:
                folder = unique_type['Folder']
                folder_path = directory / 'Documents' / folder
                folder_path.mkdir(exist_ok =True)
                src_file = Path(directory/ file)
                dst_file = Path(directory / 'Documents' / folder / file )
                src_file.rename(dst_file)

       
if __name__ == '__main__':
    main()
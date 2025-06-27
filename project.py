
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
from pathlib import Path
from data_dict import data_dict

def main():
    p = path_selection()
    files_list = scan_files(p)
    organize_by_sufix(files_list,p)


def path_selection():
    default_path = (Path.home() / 'Desktop' / 'testando')
    return default_path




def scan_files(directory):
    
    files =  [f for f in directory.iterdir() if f.is_file()]
    pattern = (r'[^\\]+$')
    files_list = []
    for file in files:
        files_list +=  re.findall(pattern, str(file)) 
    return files_list



def organize_by_sufix(list_of_files, default_path):
    
    documents_folder = default_path / 'Documents'
    documents_folder.mkdir(exist_ok = True)
    for file in list_of_files:
        path_file = Path(file)
        for unique_type in data_dict:
            if path_file.suffix in unique_type['Suffixes']:
                folder = unique_type['Folder']
                folder_path = default_path / 'Documents' / folder
                folder_path.mkdir(exist_ok =True)
                src_file = Path(default_path / file)
                dst_file = Path(default_path / 'Documents' / folder / file )
                src_file.rename(dst_file)















       
if __name__ == '__main__':
    main()
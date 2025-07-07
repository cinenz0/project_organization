import sys
import re
import argparse
from pathlib import Path
from data_dict import data_dict



def organize_by_sufix(list_of_files, directory):
    documents_folder = directory / 'Documents'
    documents_folder.mkdir(exist_ok = True)
    
    for file in list_of_files:
        file_index = 1
        path_file = Path(file)
        for unique_type in data_dict:
            if path_file.suffix in unique_type['Suffixes']:
                folder = unique_type['Folder']
                folder_path = directory / 'Documents' / folder
                folder_path.mkdir(exist_ok =True)
                src_file = Path(directory/ file)
                while True:
                    try:
                        dst_file = Path(directory / 'Documents' / folder / file )
                        src_file.rename(dst_file)
                        break
                    except FileExistsError:
                        try:
                            new_name = f'{str(file_index)}_' + file
                            file_index += 1
                            dst_file = Path(directory / 'Documents' / folder / new_name )
                            src_file.rename(dst_file)
                            print(f"The file: '{file}' already exists. Renaming it to {new_name}")
                            break
                        except:
                            continue
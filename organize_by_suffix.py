from pathlib import Path
from data_dict import data_dict
import shutil

def organize_by_sufix(original_directory, dst_directory):
    #Scan the original direcotory for the files
    list_of_files =  [f for f in original_directory.iterdir() if f.is_file()]
    documents_folder = dst_directory / 'Documents'
    documents_folder.mkdir(exist_ok = True)
    print(original_directory, dst_directory)
    for file in list_of_files:
        file_index = 1
        for unique_type in data_dict:
            if file.suffix in unique_type['Suffixes']:
                folder = unique_type['Folder']
                folder_path = dst_directory / 'Documents' / folder
                folder_path.mkdir(exist_ok =True)
                src_file = Path(original_directory/ file)
                while True:
                    try:
                        dst_file = Path(dst_directory / 'Documents' / folder / file.name )
                        
                        shutil.move(file,dst_file)
                        break
                    except FileExistsError:
                        try:
                            new_name = f'{str(file_index)}_' + file.name
                            file_index += 1
                            dst_file = Path(dst_directory / 'Documents' / folder / new_name )
                            shutil.move(file,dst_file)
                            print(f"The file: '{file}' already exists. Renaming it to {new_name}")
                            break
                        except:
                            continue
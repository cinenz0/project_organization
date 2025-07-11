import sys
import argparse
from pathlib import Path



CONFIG_FILE = 'path.txt'


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


def prompt_for_path(default_path):
    user_path = input('Path to orginize (blank to use default): ')
    if user_path == '':
        return default_path
    elif not Path(user_path).exists():
        raise FileNotFoundError

    while True:
        defaulting = input('Would you like to meke this your default path? ').lower()
        if defaulting in ['y','yes']:
            with open(CONFIG_FILE) as file:
                first_line = file.readline()
                second_line = file.readline()
                first_line = user_path
            with open (CONFIG_FILE, 'w') as new_file:
                 new_file.write(first_line + '\n'+ second_line)
            break
        elif defaulting in ['n','no']:
            break
        else:
            print('Invalid answer, [Y]es or [N]o, please')
            continue
    
    return Path(user_path)

def prompt_for_dst_path(default_dst_path):
    user_path = input('Destination path (blank to use default): ')
    if user_path == '':
        return default_dst_path
    elif not Path(user_path).exists():
        raise FileNotFoundError

    while True:
        defaulting = input('Would you like to meke this your default destination path? ').lower()
        if defaulting in ['y','yes']:
            with open(CONFIG_FILE) as file:
                first_line = file.readline()
            with open (CONFIG_FILE, 'w') as new_file:
                 new_file.write(first_line + '\n'+ user_path)
            break
        elif defaulting in ['n','no']:
            break
        else:
            print('Invalid answer, [Y]es or [N]o, please')
            continue
    return Path(user_path)
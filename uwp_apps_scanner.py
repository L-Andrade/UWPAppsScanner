import argparse
import platform
import os
import firebase_admin
import filetype
import time

from firebase_admin import credentials, db
from pathlib import Path

def get_list_of_files(base_path):
    # create a list of file and sub directories 
    # names in the given directory 
    list_files = os.listdir(base_path)
    all_files = list()
    # Iterate over all the entries
    for entry in list_files:
        # Create full path
        full_path = os.path.join(base_path, entry)
        # If entry is a directory then get the list of files in this directory 
        if os.path.isdir(full_path):
            all_files = all_files + get_list_of_files(full_path)
        else:
            all_files.append(full_path)
                
    return all_files

def get_info():
    print('Print existing info on Firebase...')

def main(args):
    # toaster = ToastNotifier()
    # toaster.show_toast("UWP", path, duration=10)
    # Args
    if args.path:
        path = args.path
    else:
        path = str(Path.home()) + '\\AppData\\Local\\Packages'
    
    # Firebase setup
    cred = credentials.Certificate("config.json")

    firebase_admin.initialize_app(cred, {'databaseURL': 'https://uwp-apps-scanner.firebaseio.com/'})

    # Will be used later to identify version/user who updated the DB
    reported_by = os.getlogin()
    windows_ver = platform.platform()
    start_time = time.time()

    root = db.reference('/')
    apps_ref = root.child('apps')
    apps_snapshot = apps_ref.get()

    for app_name in apps_snapshot:
        app = apps_ref.child(app_name).get()
        full_path = os.path.join(path, app["path"])
        db_count = 0
        for file in get_list_of_files(full_path):
            try:
                kind = filetype.guess(file)
            except:
                continue
            if kind is not None:
                print(f'File with extension {kind.extension} is {kind.mime}')
                if kind.mime == 'application/x-sqlite3':
                    db_count = db_count + 1
            
        print(f'Found {str(db_count)} dbs for {full_path}')
    
    print(f'Elapsed time: {round(time.time() - start_time, 2)}s')

# Args boilerplat and main call
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', type=str, help='Path to AppData\\Local\\Packages')
    parser.add_argument('-n', '--notification', action='store_true', help='Receive notification if there are updates')
    parser.add_argument('-i', '--info', action='store_true', help='Print existing information on apps')
    args = parser.parse_args()
    if args.notification:
        from win10toast import ToastNotifier
    if args.info:
        get_info()
    else:
        main(args)
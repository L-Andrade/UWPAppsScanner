import argparse
import platform
import os
import firebase_admin

from firebase_admin import credentials, db
from win10toast import ToastNotifier
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

def main():
    # toaster = ToastNotifier()
    # toaster.show_toast("UWP", path, duration=10)
    # Args
    args = parser.parse_args()
    if args.path:
        path = args.path
    else:
        path = str(Path.home()) + '\\AppData\\Local\\Packages'
    
    # Firebase setup
    cred = credentials.Certificate("config.json")
    try:
        firebase_admin.initialize_app(cred, {'databaseURL': 'https://uwp-apps-scanner.firebaseio.com/'})
    except expression as identifier:
        print('Are you connected to the internet?')
        return

    # Will be used later to identify version/user who updated the DB
    reported_by = os.getlogin()
    windows_ver = platform.platform()

    root = db.reference('/')
    apps_ref = root.child('apps')
    apps_snapshot = apps_ref.get()

    for app_name in apps_snapshot:
        app = apps_ref.child(app_name).get()
        full_path = os.path.join(path, app["path"])
        db_count = 0
        for file in get_list_of_files(full_path):
            if file.endswith('.db'):
                # print(str(file))
                db_count = db_count + 1
            
        print(f'Found {str(db_count)} dbs for {full_path}')

# Args boilerplat and main call
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', type=str, help='Path to AppData\\Local\\Packages')
    parser.add_argument('-n', '--notification', action='store_true', help='Receive notification if there are updates')
    main()
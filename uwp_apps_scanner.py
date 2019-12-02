import argparse
import platform
import os
import firebase_admin
import filetype
import time
import json

from datetime import datetime
from firebase_admin import credentials, db
from pathlib import Path

DB_COUNT = 'db_count'
FILE_COUNT = 'file_count'
HISTORY = 'history'
CONFIG_FILE = 'config.json'
DATABASE_URL = 'https://uwp-apps-scanner.firebaseio.com/'

def get_list_of_files(base_path):
    # create a list of file and sub directories 
    # names in the given directory 
    all_files = list()
    # Iterate over all the entries
    try:
        list_files = os.listdir(base_path)
        for entry in list_files:
        # Create full path
            full_path = os.path.join(base_path, entry)
            # If entry is a directory then get the list of files in this directory 
            if os.path.isdir(full_path):
                all_files = all_files + get_list_of_files(full_path)
            else:
                all_files.append(full_path)
    except:
        pass
    
                
    return all_files

def get_info(with_history):
    print('Getting existing info from Firebase...')
    
    root = db.reference('/')
    apps_ref = root.child('apps')
    apps_snapshot = apps_ref.get()
    
    for app_name in apps_snapshot:
        app_ref = apps_ref.child(app_name)
        app = app_ref.get()
        
        print('\n-------------------------------------------------------------')
        print(f'App name: {app_name}')
        print('-------------------------------------------------------------')
        for key, val in app.items():
            if key == "history" and not with_history:
                continue
            if isinstance(val, dict):
                print(key)
                for key, val in val.items():
                    print(f'\t{key}: {val}')
            else:
                print(f'{key}: {val}')

def is_new(app, app_info):
    if not DB_COUNT in app or not FILE_COUNT in app:
        return True
    return app[DB_COUNT] != app_info[DB_COUNT] or app[FILE_COUNT] != app_info[FILE_COUNT]

def notify_user(toaster, app_name):
    # Library does not support notifications without duration...
    # It will throw an exception but still show message with the desired behavior.
    try:
        toaster.show_toast('UWP Scanner', f'{app_name} has updates.', duration=None)
    except:
        pass

def main(args):
    # Args
    if args.path:
        path = args.path
    else:
        path = str(Path.home()) + '\\AppData\\Local\\Packages'
    if args.notification:
        notify = True
        toaster = ToastNotifier()
    else:
        notify = False
    
    # Will be used later to identify version/user who updated the DB
    reported_by = os.getlogin()
    windows_ver = platform.platform()
    start_time = time.time()

    root = db.reference('/')
    apps_ref = root.child('apps')
    apps_snapshot = apps_ref.get()

    # For all apps in Firebase config
    for app_name in apps_snapshot:
        app_ref = apps_ref.child(app_name)
        app = app_ref.get()
        
        # Get path to app's folder
        full_path = os.path.join(path, app['path'])

        # Init app_info that will be sent to server
        app_info = {}
        db_count = 0
        file_count = 0

        # For all files in the app's folder
        for file in get_list_of_files(full_path):
            # Try to get file type
            # If it got an exception or could not guess type, skip it
            try:
                kind = filetype.guess(file)
            except:
                continue
            if kind is None:
                continue
            print(f'File with extension {kind.extension} is {kind.mime}')
            if kind.mime == 'application/x-sqlite3':
                db_count += 1
            else:
                file_count += 1
        
        app_info[DB_COUNT] = db_count
        app_info[FILE_COUNT] = file_count

        user_info = {'user': reported_by, 'windows_ver': windows_ver, 'updated_at': str(datetime.now())}
        if is_new(app, app_info):
            app_info['updated_by'] = user_info
            if notify:
                notify_user(toaster, app_name)
        app_ref.child(HISTORY).push(user_info)
        app_ref.update(app_info)
        
        print(f'Found {str(db_count)} dbs for {full_path}')
    
    print(f'Elapsed time: {round(time.time() - start_time, 2)}s')

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', type=str, help='Path to AppData\\Local\\Packages')
    parser.add_argument('-n', '--notification', action='store_true', help='Receive notification if there are updates')
    parser.add_argument('-i', '--info', action='store_true', help='Print existing information on apps')
    parser.add_argument('-ih', '--infohistory', action='store_true', help='Print existing information on apps with history')
    return parser.parse_args()

def setup_firebase():
    cred = credentials.Certificate(CONFIG_FILE)
    firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})

if __name__ == "__main__":
    args = setup_args()
    setup_firebase()
    if args.notification:
        from win10toast import ToastNotifier
    if args.info or args.infohistory:
        get_info(args.infohistory)
    else:
        main(args)
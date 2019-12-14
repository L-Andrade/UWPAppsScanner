import argparse
import platform
import os
import firebase_admin
import filetype
import time

from datetime import datetime
from firebase_admin import credentials, db
from pathlib import Path
from win32api import GetFileVersionInfo, LOWORD, HIWORD

PATH = 'path'
EXE = 'exe'
DBS = 'dbs'
FILE_COUNT = 'file_count'
HISTORY = 'history'
CONFIG_FILE = 'config.json'
DATABASE_URL = 'https://uwp-apps-scanner.firebaseio.com/'
VERSION = 'version'
SQLITE_MIME = 'application/x-sqlite3'
CONFIRMING_CHAR = 'y'

def print_if_verbose(msg):
    if verbose:
        print(msg)

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

def get_version_number(filename):
    try:
        print(str(filename))
        info = GetFileVersionInfo (filename, "\\")
        ms = info['FileVersionMS']
        ls = info['FileVersionLS']
        return [HIWORD(ms), LOWORD(ms), HIWORD(ls), LOWORD(ls)]
    except:
        return [0, 0, 0, 0]

def is_new_version(current, server):
    if len(current) > len(server):
        return True
    for i in range(0, len(server)):
        if current[i] > server[i]:
            return True
    return False

def is_new(app, app_info):
    if not VERSION in app:
        return True
    is_new_ver = is_new_version(app_info[VERSION], app[VERSION])
    if app_info[VERSION] != app[VERSION] and not is_new_ver:
        print(f'You are running an older version of {app[PATH]}')
    if app_info[VERSION] == app[VERSION] and app_info[DBS] != app[DBS]:
        print(f'App {app[EXE]} is in the same version in the server, but DBs are different.')
        print('Local DBs are: ')
        for db in app_info[DBS]:
            print(f'\t{db}')
        print('\nServer DBs are: ')
        for db in app[DBS]:
            print(f'\t{db}')
        option = input('\nType y if you would like to update server with local info: ')
        return option.lower() == CONFIRMING_CHAR
    return is_new_ver

def notify_user(toaster, app_name):
    # Library does not support notifications without duration...
    # It will throw an exception but still show message with the desired behavior.
    try:
        toaster.show_toast('UWP Scanner', f'{app_name} has updates.', duration = None)
    except:
        pass

def get_app_version(app):
    windows_apps_path = os.environ['ProgramW6432'] + '\\WindowsApps'
    app_start_path = app[PATH].split('_')[0]
    try:
        apps_dirs = [dI for dI in os.listdir(windows_apps_path) if os.path.isdir(os.path.join(windows_apps_path, dI))]
        for app_dir in apps_dirs:
            if app_start_path in app_dir and 'x64' in app_dir:
                full_path = windows_apps_path + '\\' + app_dir + '\\' + app[EXE]
                return get_version_number(full_path)
    except PermissionError:
        print(f'You do not have permissions to open {windows_apps_path}.')
    return None

def main(args):
    # Args
    if args.path:
        path = args.path
    else:
        path = str(Path.home()) + '\\AppData\\Local\\Packages'
    if notify:
        toaster = ToastNotifier()

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
        full_path = os.path.join(path, app[PATH])

        # Init app_info that will be sent to server
        app_info = {}
        dbs = []
        file_count = 0

        version = get_app_version(app)
        if version is None:
            continue
        app_info[VERSION] = version

        # For all files in the app's folder
        for file in get_list_of_files(full_path):
            # Try to get file type
            # If it got an exception or could not guess type, skip it
            try:
                kind = filetype.guess(file)
                filename = file.split('\\')[-1]
                print_if_verbose(f'File {filename} is {kind.mime}')
                if kind.mime == SQLITE_MIME:
                    dbs.append(filename)
                else:
                    file_count += 1
            except:
                print_if_verbose(f'Failed to guess type for {file}.')
        
        app_info[DBS] = dbs
        app_info[FILE_COUNT] = file_count

        user_info = {'user': reported_by, 'windows_ver': windows_ver, 'updated_at': str(datetime.now())}
        if is_new(app, app_info):
            print_if_verbose(f'There are updates for {app_name}')
            if notify:
                notify_user(toaster, app_name)
            app_info['updated_by'] = user_info
            app_ref.child(HISTORY).push(user_info)
            app_ref.update(app_info)
        else:
            print_if_verbose('No changes detected.')
        
        print(f'Found {str(len(dbs))} DBs for {app_name}, with version {app_info[VERSION]}')
    
    print(f'Elapsed time: {round(time.time() - start_time, 2)}s')

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', type=str, help='Path to AppData\\Local\\Packages')
    parser.add_argument('-n', '--notification', action='store_true', help='Receive notification if there are updates')
    parser.add_argument('-i', '--info', action='store_true', help='Print existing information on apps')
    parser.add_argument('-ih', '--infohistory', action='store_true', help='Print existing information on apps with history')
    parser.add_argument('-v', '--verbose', action='store_true', help='Shows all logging')
    return parser.parse_args()

def setup_firebase():
    cred = credentials.Certificate(CONFIG_FILE)
    firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})

if __name__ == "__main__":
    args = setup_args()
    setup_firebase()
    verbose = args.verbose
    notify = args.notification
    if notify:
        from win10toast import ToastNotifier
    if args.info or args.infohistory:
        get_info(args.infohistory)
    else:
        main(args)
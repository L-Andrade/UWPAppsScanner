import argparse
import platform
import os
import pyrebase
import filetype
import time
import sqlite3
import json

from dictdiffer import diff
from datetime import datetime
from pathlib import Path
from win32api import GetFileVersionInfo, LOWORD, HIWORD

# Constants
APPS = 'apps'
PATH = 'path'
EXE = 'exe'
DBS = 'dbs'
FILE_COUNT = 'file_count'
HISTORY = 'history'
DATABASE_URL = 'https://uwp-apps-scanner.firebaseio.com/'
VERSION = 'version'
SQLITE_MIME = 'application/x-sqlite3'
CONFIRMING_CHAR = 'y'
PRAGMA_USER_VERSION = 'PRAGMA user_version'
SELECT_SQLITE_TABLES = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
USER_VERSION = 'user_version'
CONFIG = {
        "apiKey": "AIzaSyDAkHPrbJa3IFyitFWBK_vXh5brDiJqf5E",
        "authDomain": "uwp-apps-scanner.firebaseapp.com",
        "databaseURL": "https://uwp-apps-scanner.firebaseio.com",
        "projectId": "uwp-apps-scanner",
        "storageBucket": "uwp-apps-scanner.appspot.com",
        "messagingSenderId": "507102484200",
        "appId": "1:507102484200:web:1050cceded4e0ef99e5b5d"
    }
SCHEMA_VERSION = 5

def print_if_verbose(msg):
    if verbose:
        print(msg)

def print_item_or_dict(item_key, item_value):
    if isinstance(item_value, dict):
        print(item_key)
        for key, val in item_value.items():
            if isinstance(val, dict):
                print('------------------------------------------------')
                print_item_or_dict(key, val)
            else:
                print(f'\t{key}: {val}')
    else:
        print(f'{item_key}: {item_value}')

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

def is_local_updated():
    root = firebase.database()
    schema_version = root.child('schema_version').get().val()

    if SCHEMA_VERSION != schema_version:
        print('Your script is outdated.')
        print(f'\tLocal is at version {SCHEMA_VERSION}.')
        print(f'\tServer is at version {schema_version}.')
        return False
    print(f'Your script is up-to-date, with version {schema_version}.')
    return True


def get_info(with_history):
    print('Getting existing info from Firebase...')
    
    root = firebase.database()
    
    # Get DB apps
    apps_ref = root.child(APPS).get()

    # For all apps in Firebase config
    for _app_name in apps_ref.each():
        app_name = _app_name.key()
        app = root.child(APPS).child(app_name).get().val()

        print('\n-------------------------------------------------------------')
        print(f'App name: {app_name}')
        print('-------------------------------------------------------------')
        for key, val in app.items():
            if key == "history" and not with_history:
                continue
            print_item_or_dict(key, val)

def export_as_json():
    root = firebase.database().child(APPS).get().val()
    date = datetime.now().strftime("%d%m%Y_%H%M%S")
    file_path = f'server{date}.json'

    print(f'Output file will be {file_path}')
    try:
        with open(file_path, 'w') as file:
            json.dump(root, file, indent = 4)
        print('Exported successfully')
    except Exception as e:
        print('Error exporting')
        print_if_verbose(str(e))


def get_version_number(filename):
    try:
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
        print(f'You are running an older version of {app[EXE]}')
    if not DBS in app and DBS in app_info:
        print_if_verbose(f'There are no DBs in server for {app[EXE]}. Updating with local info.')
        return True
    if app_info[VERSION] == app[VERSION] and app_info[DBS] != app[DBS]:
        print(f'App {app[EXE]} is in the same version in the server, but DBs are different.')
        print('Difference between LOCAL and SERVER is:')
        for difference in list(diff(app_info[DBS], app[DBS])):
            print(f'\t{difference}')
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
            if app_start_path in app_dir and ('x64' in app_dir or 'x86' in app_dir):
                full_path = windows_apps_path + '\\' + app_dir + '\\' + app[EXE]
                # EXE not found in dir. Keep looking.
                if not os.path.exists(full_path):
                    continue
                return get_version_number(full_path)
    except PermissionError:
        print(f'You do not have permissions to open {windows_apps_path}.')
    return None

def process_db(file):
    db_info = {}
    try:
        db_conn = sqlite3.connect(file)
        c = db_conn.cursor()
        c.execute(PRAGMA_USER_VERSION)
        db_info[USER_VERSION] = c.fetchone()[0]
        c.execute(SELECT_SQLITE_TABLES)
        db_info['tables'] = [item[0] for item in c.fetchall()]
    except Exception as e:
        db_info = None
        print_if_verbose(str(e))
    finally:
        c.close()
        db_conn.close()
    return db_info

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

    root = firebase.database()

    if not is_local_updated():
        return

    # Get DB apps
    apps_ref = root.child(APPS).get()

    # For all apps in Firebase config
    for _app_name in apps_ref.each():
        app_name = _app_name.key()
        app = root.child(APPS).child(app_name).get().val()
        
        # Get path to app's folder
        full_path = os.path.join(path, app[PATH])

        # Init app_info that will be sent to server
        app_info = {}
        dbs = {}
        file_count = 0

        version = get_app_version(app)
        if version is None:
            print(f'Did not find version for {app_name}. Skipping.')
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
                    sanitized_filename = filename.split('.')[0]
                    db_info = process_db(file)
                    if db_info is None:
                        print(f'Failed to get DB info for {file}')
                        continue
                    if dbs.get(sanitized_filename):
                        # Already exists in dict. Check if we need to update info
                        print_if_verbose(f'Two DBs with the same name found for {app_name}.')
                        if db_info[USER_VERSION] > dbs.get(sanitized_filename)[USER_VERSION]:
                            print_if_verbose('User version is greater than the last. Updating.')
                            dbs[sanitized_filename] = db_info
                    else:
                        dbs[sanitized_filename] = db_info
                else:
                    file_count += 1
            except:
                print_if_verbose(f'Failed to guess type for {file}.')
        
        # app_info[DBS] = list(dict.fromkeys(dbs))
        app_info[DBS] = dbs
        app_info[FILE_COUNT] = file_count

        user_info = {
                        'user': reported_by, \
                        'windows_ver': windows_ver, \
                        'updated_at': str(datetime.now()), \
                        'app_version': app_info[VERSION], \
                        'dbs': app_info[DBS]
                    }
        if is_new(app, app_info):
            print_if_verbose(f'There are updates for {app_name}')
            if notify:
                notify_user(toaster, app_name)
            app_info['updated_by'] = user_info
            root.child(APPS).child(app_name).child(HISTORY).push(user_info)
            root.child(APPS).child(app_name).update(app_info)
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
    parser.add_argument('-e', '--export', action='store_true', help='Export server data as JSON')
    parser.add_argument('--version', action='store_true', help='Checks if local is up-to-date')
    return parser.parse_args()

def setup_firebase():
    return pyrebase.initialize_app(CONFIG)

if __name__ == "__main__":
    args = setup_args()
    firebase = setup_firebase()
    verbose = args.verbose
    notify = args.notification
    if notify:
        from win10toast import ToastNotifier
    if args.info or args.infohistory:
        get_info(args.infohistory)
        exit()
    if args.version:
        is_local_updated()
        exit()
    if args.export:
        export_as_json()
        exit()
    main(args)
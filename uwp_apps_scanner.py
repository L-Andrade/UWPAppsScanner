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
SCHEMA_VERSION = 6

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

def get_evolution(queried_app):
    print('Getting existing info from Firebase...')
    
    root = firebase.database()
    
    # Get DB apps
    apps_ref = root.child(APPS).get()

    # For all apps in Firebase config
    if queried_app:
        app = get_app_or_none(root, queried_app)
        if app:
            print_app_evolution(root, queried_app, app)
        return

    for _app_name in apps_ref.each():
        app_name = _app_name.key()
        app = root.child(APPS).child(app_name).get().val()
        print_app_evolution(root, app_name, app)

def list_of_dict_keys(any_dict):
    return list(any_dict.keys())

def print_app_evolution(root, app_name, app):
    print('\n-------------------------------------------------------------')
    print(f'App name: {app_name}')
    print('-------------------------------------------------------------')
    history = list(app[HISTORY].values())
    previous_printed = None
    for i in range(len(history)):
        is_last = (i == len(history) - 1)
        record = history[i]
        previous_printed = print_evolution(record, previous_printed)

def print_evolution(new, previous_printed):
    if DBS not in new:
        return previous_printed
    new_keys = list_of_dict_keys(new[DBS])
    if previous_printed is None:
        print(f'\n{new_keys}')
        return new
    if previous_printed is None or DBS not in previous_printed:
        return new
    old_keys = list_of_dict_keys(previous_printed[DBS])
    if new_keys == old_keys:
        diff_result = list(diff(previous_printed[DBS], new[DBS]))
        if len(diff_result) == 0:
            return new
        print(f'\n{new_keys}')
        print('\tDiffers inside the databases: ')
        for each_diff in diff_result:
            print(f'\t\t{each_diff}')
    else:
        print(f'\n{new_keys}')
    return new

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
    root = firebase.database().get().val()
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
    root = firebase.database()

    if not is_local_updated():
        return

    # Get DB apps
    apps_ref = root.child(APPS).get()

    if args.app is None:
        for _app_name in apps_ref.each():
            app_name = _app_name.key()
            app = root.child(APPS).child(app_name).get().val()
            
            analyze_app(root, app_name, app)
    else:
        app = get_app_or_none(root, args.app)
        if app:
            analyze_app(root, args.app, app)
    
    print(f'Elapsed time: {round(time.time() - start_time, 2)}s')

def get_app_or_none(root, app_name):
    app = root.child(APPS).child(app_name).get().val()
    if app is None:
        print(f'\nThere is no app with the name "{args.app}" in the server.\nDid you mean any of these apps:')
        get_apps(False)
    return app


def analyze_app(root, app_name, app):
    # Get path to app's folder
    full_path = os.path.join(path, app[PATH])

    # Init app_info that will be sent to server
    app_info = {}
    dbs = {}
    file_count = 0

    version = get_app_version(app)
    if version is None:
        print(f'Did not find version for {app_name}. Skipping.')
        return
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
    if not dbs:
        print(f'Your database list is empty for {app_name}')
        return
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
        print(f'No changes detected for {app_name}.')
    
    print(f'Found {str(len(dbs))} DBs for {app_name}, with version {app_info[VERSION]}')

def print_table (tbl, border_horizontal = '-', border_vertical = '|', border_cross = '+'):
    cols = [list(x) for x in zip(*tbl)]
    lengths = [max(map(len, map(str, col))) for col in cols]
    f = border_vertical + border_vertical.join(' {:>%d} ' % l for l in lengths) + border_vertical
    s = border_cross + border_cross.join(border_horizontal * (l+2) for l in lengths) + border_cross

    print(s)
    for row in tbl:
        print(f.format(*row))
        print(s)

def get_apps(with_more_info):
    root = firebase.database()
    apps_ref = root.child(APPS).get()
    
    headers = ['App', 'Version']
    if with_more_info:
        headers.append('Last updated')
        headers.append('Databases')
    table_rows = [headers]
    for _app_name in apps_ref.each():
        app_name = _app_name.key()
        app = root.child(APPS).child(app_name).get().val()
        app_info = [app_name, str(app[VERSION])]
        if with_more_info:
            app_info.append(app['updated_by']['updated_at'])
            if DBS in app:
                app_info.append(str(list(app[DBS].keys())))
            else:
                app_info.append("No databases found yet.")
        table_rows.append(app_info)

    print_table(table_rows)

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', type=str, help='Path to AppData\\Local\\Packages')
    parser.add_argument('-n', '--notification', action='store_true', help='Receive notification if there are updates')
    parser.add_argument('-i', '--info', action='store_true', help='Print existing information on apps')
    parser.add_argument('-ih', '--infohistory', action='store_true', help='Print existing information on apps with history')
    parser.add_argument('-evo', '--evolution', action='store_true', help='Print evolution of the apps databases')
    parser.add_argument('-v', '--verbose', action='store_true', help='Shows all logging')
    parser.add_argument('-e', '--export', action='store_true', help='Export server data as JSON')
    parser.add_argument('--version', action='store_true', help='Checks if local is up-to-date')
    parser.add_argument('--apps', action='store_true', help='Lists all monitored apps in the server')
    parser.add_argument('--appsdetail', action='store_true', help='Lists all monitored apps in the server with additional details')
    parser.add_argument('--appevo', type=str, help='Print evolution of a certain app')
    parser.add_argument('--app', type=str, help='Update only a certain app')
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
    if args.apps or args.appsdetail:
        get_apps(args.appsdetail)
        exit()
    if args.info or args.infohistory:
        get_info(args.infohistory)
        exit()
    if args.version:
        is_local_updated()
        exit()
    if args.export:
        export_as_json()
        exit()
    if args.evolution or args.appevo:
        get_evolution(args.appevo)
        exit()
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
    main(args)
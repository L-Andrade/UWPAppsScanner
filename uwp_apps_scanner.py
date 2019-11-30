import argparse
import platform
import os
import firebase_admin

from firebase_admin import credentials, db
from win10toast import ToastNotifier
from pathlib import Path

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
    firebase_admin.initialize_app(cred, {'databaseURL': 'https://uwp-apps-scanner.firebaseio.com/'})

    root = db.reference('/')
    apps_ref = root.child('apps')
    apps_snapshot = apps_ref.get()

    for app_name in apps_snapshot:
        app = apps_ref.child(app_name).get()
        full_path = os.path.join(path, app["path"])
        print(full_path)

# Args boilerplat and main call
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--path', type=str, help='Path to AppData\\Local\\Packages')
    parser.add_argument('-n', '--notification', action='store_true', help='Receive notification if there are updates')
    main()
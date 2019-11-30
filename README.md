# UWPAppsScanner
A Python script with a Firebase Realtime Database to check for updates on certain Windows apps. Needs a config.json to connect to Firebase.

# Requirements
* Python 3.7
* pip install firebase-admin
* pip install tika
* pip install win10toast
  * for Windows notifications - might become optional in the future.

# Usage
`python uwp_apps_scanner.py`
* Possible arguments:
  * -h, --help: Help message and arguments.
  * -n, --notification: Pushes a notification if there are changes to an app's files.
  * -i, --info: Shows information available in Firebase.
  * -p, --path: Overrides the base path to AppData\Local\Packages to the specified one (useful if you have multiple users/disks or using a folder for tests)
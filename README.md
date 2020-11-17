# UWPAppsScanner
A Python script with a Firebase Realtime Database to check for updates on certain Windows apps.

# Disclaimer
The scanner does not export any personal data that might be in the SQLite databases found. This can be seen from the queries at the top of the Python script. The scanner does use the Windows 10 username and Windows version.

# Requirements
* Python 3.7
* `pip install pyrebase4`
* `pip install filetype`
* `pip install dictdiffer`
* `pip install pywin32`
  * And for the post-install: `python Scripts/pywin32_postinstall.py -install`
* `pip install win10toast`
  * Optional, for Windows notifications. Use the `-n` argument.

# Usage
`python uwp_apps_scanner.py`

Possible arguments:
* -h, --help: Help message and arguments.
* -n, --notification: Pushes a notification if there are changes to an app's files.
* -i, --info: Shows information available in Firebase.
* -ih, --infohistory: Shows information available in Firebase with update history.
* -v, --verbose: Shows all logging.
* --version: Checks if local is up-to-date with the server schema.
* -p, --path: Overrides the base path to AppData\Local\Packages to the specified one (useful if you have multiple users/disks or using a folder for tests).
* -e, --export: Exports server data to a JSON file in the script directory

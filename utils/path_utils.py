# ---------------------------------------------------------
# utils/path_utils.py
# ---------------------------------------------------------
"""
Helper to safely locate resource files and determine where to store
settings/logs in both development and PyInstaller‐bundled modes.
"""

import os
import sys

def resource_path(relative_path):
    """
    Get absolute path to resource (e.g. an icon), works for dev and for PyInstaller.
    Usage:
        resource_path('resources/icon.ico')
    When frozen, sys._MEIPASS is the temporary folder holding bundled data.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Not frozen: use the folder where this .py lives
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


# utils/path_utils.py

import os
import sys
import ctypes

def app_data_path(file_name=None):
    """
    Return a folder named "ROP_data" next to the .exe (if frozen) or next to the script (if dev).
    Mark it as hidden on Windows so it doesn't clutter Explorer.
    """
    # 1) Determine where to place the folder
    if getattr(sys, "frozen", False):
        exe_folder = os.path.dirname(os.path.abspath(sys.executable))
        base_dir = os.path.join(exe_folder, "ROP_data")
    else:
        script_folder = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.join(script_folder, "ROP_data")

    # 2) Create it (if missing)
    try:
        os.makedirs(base_dir, exist_ok=True)
    except OSError as e:
        print(f"Warning: could not create ROP_data at {base_dir}: {e}")
        base_dir = os.getcwd()

    # 3) On Windows, set the HIDDEN attribute
    if os.name == "nt":
        FILE_ATTRIBUTE_HIDDEN = 0x02
        try:
            # Use the wide‐char version (SetFileAttributesW) for correct Unicode support
            ctypes.windll.kernel32.SetFileAttributesW(base_dir, FILE_ATTRIBUTE_HIDDEN)
        except Exception as ex:
            # If it fails (e.g. lack of permission), just continue without error
            print(f"Warning: could not hide folder {base_dir}: {ex}")

    # 4) Return either the folder or the specific file inside it
    if file_name:
        return os.path.join(base_dir, file_name)
    return base_dir

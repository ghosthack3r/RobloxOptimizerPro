# ---------------------------------------------------------
# utils/path_utils.py
# ---------------------------------------------------------
"""Helper to safely locate resource files in dev & PyInstaller builds."""
import os
import sys # Ensure sys is imported if you use it directly later, though os.path usually suffices

print("EXECUTING utils/path_utils.py SOURCE") # For debugging

def resource_path(relative_path): # Changed 'relative' to 'relative_path' for clarity
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        # When bundled, _MEIPASS is the root. We want resources relative to that.
    except AttributeError:
        # Not bundled, running in normal Python environment.
        # __file__ is utils/path_utils.py
        # os.path.dirname(__file__) is utils/
        # os.path.join(..., "..") goes up to the project root
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    final_path = os.path.join(base_path, relative_path)
    # print(f"DEBUG resource_path: relative='{relative_path}', base='{base_path}', final='{final_path}'") # Optional debug
    return final_path

def app_data_path(file_name=""):
    """Get path to a file in a dedicated application data directory or next to exe."""
    if getattr(sys, "frozen", False): # Bundled app
        # For bundled app, place data next to the executable
        app_dir = os.path.dirname(sys.executable)
    else: # Development
        # Place data in the project root
        # __file__ is utils/path_utils.py
        # os.path.dirname(__file__) is utils/
        # os.path.join(..., "..") goes up to the project root
        app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Optional: Create a subdirectory for app data if you prefer, e.g., "AppData"
    # app_data_specific_dir = os.path.join(app_dir, "AppData")
    # if not os.path.exists(app_data_specific_dir):
    #     try:
    #         os.makedirs(app_data_specific_dir, exist_ok=True)
    #     except OSError as e:
    #         print(f"Error creating app data specific directory {app_data_specific_dir}: {e}")
    #         # Fallback if subdirectory creation fails
    #         return os.path.join(app_dir, file_name) if file_name else app_dir
    # final_base_dir = app_data_specific_dir

    # For now, using app_dir directly (next to exe or project root)
    final_base_dir = app_dir

    if not os.path.exists(final_base_dir): # Should not happen if app_dir is derived from sys.executable or project root
        try:
            os.makedirs(final_base_dir, exist_ok=True)
        except OSError as e:
            print(f"Critical Error creating base app data directory {final_base_dir}: {e}")
            # Fallback to current working directory if creation fails catastrophically
            final_base_dir = os.getcwd()
            
    final_path = os.path.join(final_base_dir, file_name) if file_name else final_base_dir
    # print(f"DEBUG app_data_path: file_name='{file_name}', base_dir='{final_base_dir}', final='{final_path}'") # Optional debug
    return final_path

print("app_data_path FUNCTION DEFINED in utils.path_utils.py") # For debugging
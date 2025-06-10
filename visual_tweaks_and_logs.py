# visual_tweaks_and_logs.py

import ctypes
import subprocess
import os
import sys # Added sys for platform check
import platform # Added platform for platform check
from datetime import datetime # For timestamping logs
import winreg

# --- Helper for resource paths (ensure this is correctly defined if not using a separate utils.py) ---
# If utils.path_utils is a separate file, this import is fine.
# If not, resource_path needs to be defined here or imported from elsewhere.
# Assuming it's available from a utils module as per other files.
try:
    from utils.path_utils import resource_path
except ImportError:
    # Fallback definition if utils.path_utils is not found (e.g. running this file standalone for testing)
    # This basic version works if resources are relative to this script's dir, or for _MEIPASS.
    def resource_path(relative_path):
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(os.path.dirname(__file__))
        return os.path.join(base_path, relative_path)
    print("Warning: 'utils.path_utils.resource_path' not found, using fallback resource_path in visual_tweaks_and_logs.py.")


class VisualTweaks:
    @staticmethod
    def disable_wallpaper():
        """
        Uses the Windows API to set the desktop wallpaper to a blank string,
        effectively disabling it. (Windows-specific)
        """
        if platform.system().lower() != "windows":
            return "[-] Wallpaper modification is Windows-specific."
        try:
            # SPI_SETDESKWALLPAPER = 20
            # SPIF_UPDATEINIFILE = 0x01, SPIF_SENDCHANGE = 0x02
            # The last parameter '3' is SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            ctypes.windll.user32.SystemParametersInfoW(20, 0, "", 3)
            return "[*] Wallpaper temporarily disabled (set to blank)."
        except Exception as e:
            return f"[-] Failed to disable wallpaper: {e}"

    @staticmethod
    def enable_wallpaper(wallpaper_path): # Renamed from 'path' for clarity
        """
        Restores the desktop wallpaper from the given file path. (Windows-specific)
        If the path is invalid or empty, returns an error message.
        """
        if platform.system().lower() != "windows":
            return "[-] Wallpaper modification is Windows-specific."
        try:
            if not wallpaper_path or not os.path.isfile(wallpaper_path): # Check if file exists
                return f"[-] Invalid wallpaper path or file does not exist: {wallpaper_path}. Cannot restore."
            ctypes.windll.user32.SystemParametersInfoW(20, 0, str(wallpaper_path), 3)
            return f"[*] Wallpaper restored to: {wallpaper_path}"
        except Exception as e:
            return f"[-] Failed to restore wallpaper: {e}"

    @staticmethod
    def disable_visual_effects():
        """
        Disables common Windows visual effects (e.g., animations, shadows)
        by updating the UserPreferencesMask registry value. (Windows-specific)
        The mask 0x90,0x12,0x03,0x80,0x10,0x00,0x00,0x00 corresponds to "Adjust for best performance".
        """
        if platform.system().lower() != "windows":
            return "[-] Visual effects modification is Windows-specific."
        
        # UserPreferencesMask for "Adjust for best performance"
        # This value might vary slightly between Windows versions but generally aims to turn off visuals.
        # Little-endian representation of a 64-bit integer.
        # Original value (example, 'Best appearance'): 0x9E, 0x3E, 0x07, 0x80, 0x12, 0x00, 0x00, 0x00
        # 'Best performance' value (example):       0x90, 0x12, 0x03, 0x80, 0x10, 0x00, 0x00, 0x00
        best_performance_mask_hex = "9012038010000000" # As a flat hex string
        
        # This can also be set directly via winreg for HKEY_CURRENT_USER\Control Panel\Desktop\UserPreferencesMask REG_BINARY
        # However, SystemParametersInfo with SPI_SETUSERPREFERENCESMASK (value 4119 or 0x1017) is another way,
        # but it requires constructing the correct pvParam.
        # For direct registry modification:
        try:
            reg_path = r"Control Panel\Desktop"
            value_name = "UserPreferencesMask"
            # Convert hex string to bytes
            mask_bytes = bytes.fromhex(best_performance_mask_hex)
            
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, value_name, 0, winreg.REG_BINARY, mask_bytes)
            winreg.CloseKey(key)
            
            # Changes to UserPreferencesMask often require a logoff/logon or a broadcast of WM_SETTINGCHANGE.
            # Forcing a refresh of settings (might not be fully effective for all visuals without logoff):
            ctypes.windll.user32.SystemParametersInfoW(0x0011, 0, None, 0x0002 | 0x0001) # SPI_SETDESKWALLPAPER with null path, SPIF_SENDCHANGE | SPIF_UPDATEINIFILE
            # A more targeted way for UserPreferencesMask might be needed if above doesn't refresh all.
            # SendMessageTimeout might be better:
            # HWND_BROADCAST = 0xFFFF
            # WM_SETTINGCHANGE = 0x001A
            # SendMessageTimeout(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Policy", SMTO_ABORTIFHUNG, 5000, NULL)

            return "[*] Visual effects set to 'Best Performance' (registry updated)."
        except Exception as e:
            return f"[-] Exception disabling visual effects via registry: {e}"


    @staticmethod
    def enable_visual_effects(): # Renamed for clarity
        """
        Re-enables common Windows visual effects by restoring UserPreferencesMask
        to a typical "Let Windows choose" or "Best appearance" value. (Windows-specific)
        """
        if platform.system().lower() != "windows":
            return "[-] Visual effects modification is Windows-specific."

        # 'Let Windows choose' or 'Best appearance' (example, can vary)
        best_appearance_mask_hex = "9E3E078012000000" # Common default for "Best Appearance"
        
        try:
            reg_path = r"Control Panel\Desktop"
            value_name = "UserPreferencesMask"
            mask_bytes = bytes.fromhex(best_appearance_mask_hex)
            
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, value_name, 0, winreg.REG_BINARY, mask_bytes)
            winreg.CloseKey(key)

            # Force refresh
            ctypes.windll.user32.SystemParametersInfoW(0x0011, 0, None, 0x0002 | 0x0001)

            return "[*] Visual effects restored towards 'Best Appearance' (registry updated)."
        except Exception as e:
            return f"[-] Exception restoring visual effects via registry: {e}"


class GlobalLogger:
    """
    Provides simple, timestamped, file-based logging to 'app.log'.
    The log file is located using resource_path, making it work in dev and bundled modes.
    Logs include timestamps and markers for errors or internal messages.
    """
    log_file = resource_path("app.log") # Determine log file path once using resource_path

    # Ensure log directory exists at class initialization (or first log attempt)
    try:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir): # Check if log_dir is not empty string
            os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        # Print to stderr if directory creation fails, as logging itself might not work yet
        print(f"CRITICAL: Failed to create log directory '{os.path.dirname(log_file)}'. Error: {e}", file=sys.stderr)


    @staticmethod
    def append(message, is_error=False, is_internal=False):
        """
        Appends a timestamped message to the log file.
        - message: The string message to log.
        - is_error: If True, prepends "[ERROR]" to the message.
        - is_internal: If True, prepends "[DEBUG]" (for internal/verbose logs).
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] # Timestamp with milliseconds
            prefix = ""
            if is_error:
                prefix = "[ERROR] "
            elif is_internal: # For verbose/debug type messages from within components
                prefix = "[DEBUG] "
            
            # Ensure message is a string
            if not isinstance(message, str):
                try:
                    message = str(message)
                except:
                    message = "Undescribable log message object"

            log_entry = f"{timestamp} - {prefix}{message}\n"
            
            with open(GlobalLogger.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e_log:
            # Fallback if logging fails: print to stderr
            # Avoid recursion if print itself causes issues with GlobalLogger.append
            try:
                print(f"LOGGER_FAILURE: Failed to write to log file '{GlobalLogger.log_file}'. Error: {e_log}. Original message: {message}", file=sys.stderr)
            except:
                pass # Absolute fallback

    @staticmethod
    def get_log():
        """
        Returns the full contents of the log file.
        Returns a placeholder string if the log file doesn't exist or is unreadable.
        """
        try:
            if os.path.exists(GlobalLogger.log_file):
                with open(GlobalLogger.log_file, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                return "[*] Log file does not exist yet."
        except Exception as e:
            GlobalLogger.append(f"Failed to read log file for display: {e}", is_error=True)
            return f"[-] Error reading log file: {e}"

    @staticmethod
    def clear_log():
        """
        Deletes (empties) the log file if it exists.
        Returns a status message.
        """
        try:
            if os.path.exists(GlobalLogger.log_file):
                # Open in 'w' mode to truncate, then close. This is safer than os.remove sometimes.
                with open(GlobalLogger.log_file, "w", encoding="utf-8") as f:
                    f.write("") # Truncate the file
                GlobalLogger.append("Log file cleared by user.", is_internal=True) # Log the clear action itself
                return "[*] Log file has been cleared."
            else:
                return "[*] No log file found to clear."
        except Exception as e:
            # Try to log the error of clearing the log, then return error message
            GlobalLogger.append(f"Failed to clear log file: {e}", is_error=True)
            return f"[-] Error clearing log file: {e}"

    # Optional: Method to explicitly set log file path if needed during runtime,
    # though current design uses a class-level fixed path.
    # @staticmethod
    # def set_log_file_path(new_path):
    #     GlobalLogger.log_file = new_path
    #     # Re-ensure directory exists for new path
    #     try:
    #         log_dir = os.path.dirname(GlobalLogger.log_file)
    #         if log_dir and not os.path.exists(log_dir):
    #             os.makedirs(log_dir, exist_ok=True)
    #         GlobalLogger.append(f"Log file path explicitly set to: {new_path}", is_internal=True)
    #     except Exception as e:
    #         print(f"CRITICAL: Failed to create directory for new log path '{new_path}'. Error: {e}", file=sys.stderr)
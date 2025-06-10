# tcp_optimizer_ui.py

import subprocess
import winreg  # For Windows registry access
import json
import os
import sys
import re  # For parsing netsh output
import platform  # To check OS

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton,
    QTextEdit, QMessageBox, QHBoxLayout, QGridLayout, QFrame, QApplication,
    QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase

from visual_tweaks_and_logs import GlobalLogger
from utils.path_utils import app_data_path  # For consistent backup file location

# Registry path for global TCP/IP parameters
REG_PATH_GLOBAL_TCP = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"

# Backup file location using centralized app_data_path
BACKUP_FILE = app_data_path("tcp_optimizer_backup.json")

# Load and register the Audiowide font
def load_custom_font():
    font_path = os.path.join("resources", "fonts", "Audiowide", "Audiowide-Regular.ttf")
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            return QFontDatabase.applicationFontFamilies(font_id)[0]
    return "Segoe UI"  # Fallback to Segoe UI if font loading fails

# Get the custom font family name
CUSTOM_FONT = load_custom_font()

# --- Helper Functions for Registry and Commands ---

def run_shell_command(command_list, check_return_code=True):
    """
    Executes a shell command (Windows-only for TCP tuning).
    Returns a string with stdout or error details.
    """
    if platform.system().lower() != "windows":
        return "Error: Shell commands for TCP tuning are Windows-specific in this module."
    try:
        creationflags = 0x08000000  # CREATE_NO_WINDOW
        process = subprocess.run(
            command_list,
            shell=False,
            capture_output=True,
            text=True,
            check=False,
            creationflags=creationflags,
            encoding='utf-8',
            errors='ignore'
        )
        output = process.stdout.strip() if process.stdout else ""
        error_output = process.stderr.strip() if process.stderr else ""

        log_msg = (
            f"Cmd: {' '.join(command_list)}, RC: {process.returncode}, "
            f"StdOut: '{output[:100]}...', StdErr: '{error_output[:100]}...'"
        )
        GlobalLogger.append(f"[TCPOptimizer] {log_msg}", is_internal=True)

        if check_return_code and process.returncode != 0:
            combined_error = (
                error_output if error_output
                else output if "error" in output.lower() or "invalid" in output.lower()
                else f"Command failed with code {process.returncode}"
            )
            return f"Error: {combined_error}"

        # Prioritize meaningful stdout
        if output and "Ok." not in output and "error" not in output.lower() and "invalid" not in output.lower():
            return output
        elif error_output:
            return f"Info/Error: {error_output}"
        elif output:
            return output
        else:
            return f"Command executed with return code {process.returncode}."
    except FileNotFoundError:
        msg = f"Command '{command_list[0]}' not found."
        GlobalLogger.append(f"[TCPOptimizer] {msg}", is_error=True)
        return f"Error: {msg}"
    except Exception as e:
        msg = f"Exception running command '{' '.join(command_list)}': {e}"
        GlobalLogger.append(f"[TCPOptimizer] {msg}", is_error=True)
        return f"Error: {msg}"


def set_registry_dword(reg_path, value_name, value_data):
    """
    Sets a DWORD registry value under HKLM for the given path.
    Returns a message string indicating success or failure.
    """
    if platform.system().lower() != "windows":
        return "Error: Windows-only."
    try:
        key = winreg.CreateKeyEx(
            winreg.HKEY_LOCAL_MACHINE,
            reg_path,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
        )
        winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, int(value_data))
        winreg.CloseKey(key)
        msg = f"[+] Registry Set: HKLM\\{reg_path}\\{value_name} = {value_data} (DWORD)"
        GlobalLogger.append(msg, is_internal=True)
        return msg
    except ValueError:
        msg = f"[-] Registry Error: Value for '{value_name}' must be an integer (got '{value_data}')."
        GlobalLogger.append(msg, is_error=True)
        return msg
    except Exception as e:
        msg = f"[-] Registry Error: Failed to set '{value_name}' in HKLM\\{reg_path}: {e}"
        GlobalLogger.append(msg, is_error=True)
        return msg


def get_registry_dword(reg_path, value_name, default_value="N/A"):
    """
    Reads a DWORD registry value under HKLM for the given path.
    Returns the integer value or default_value if not found or on error.
    """
    if platform.system().lower() != "windows":
        return default_value
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            reg_path,
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        )
        value, reg_type = winreg.QueryValueEx(key, value_name)
        winreg.CloseKey(key)
        if reg_type == winreg.REG_DWORD:
            return value
        else:
            GlobalLogger.append(
                f"[TCPOptimizer] Registry value HKLM\\{reg_path}\\{value_name} is not DWORD (Type: {reg_type}).",
                is_error=True
            )
            return f"WrongType({reg_type})"
    except FileNotFoundError:
        return default_value
    except Exception as e:
        GlobalLogger.append(
            f"[TCPOptimizer] Error getting registry value HKLM\\{reg_path}\\{value_name}: {e}",
            is_error=True
        )
        return "Error"


# --- TCP Parameter Definitions and Profiles ---

TCP_REG_PARAMS_INFO = {
    # Display Name: (Registry Value Name, Typical Default, Description for UI Tooltip)
    "TCP/IP Stack TTL": ("DefaultTTL", 128, "Default Time To Live for IP packets. Standard is 64 or 128."),
    "TCP Window Scaling & Timestamps (RFC1323)": ("Tcp1323Opts", 3, "Enables RFC 1323 options (0=None, 1=WinScale, 2=Timestamps, 3=Both)."),
    "Selective ACK (SACK)": ("SackOpts", 1, "Enables Selective Acknowledgement (1=Enabled, 0=Disabled)."),
    "Max Duplicate ACKs for Fast Retransmit": ("MaxDupAcks", 2, "Number of duplicate ACKs before triggering fast retransmit (e.g., 2 or 3)."),
    # Netsh controlled parameters - will be queried and displayed separately
    "TCP Window Auto-Tuning Level": (None, "normal", "Controls TCP receive window auto-tuning level (e.g., normal, restricted, disabled)."),
    "Add-On Congestion Control Provider": (None, "ctcp", "TCP congestion control algorithm (e.g., ctcp, cubic, default)."),
    "Receive Side Scaling (RSS) State": (None, "enabled", "Distributes network processing across multiple CPUs."),
    "ECN Capability": (None, "disabled", "Explicit Congestion Notification (e.g., enabled, disabled, default)."),
    "RFC 1323 Timestamps (Netsh Global)": (None, "default", "Global setting for RFC 1323 timestamps via netsh (e.g., enabled, disabled, default)."),
}

TCP_PROFILES = {
    "Windows Default (Recommended Restore)": {
        "description": "Resets TCP settings towards typical Windows defaults (e.g., Normal auto-tuning, CTCP/Default congestion).",
        "registry": {"DefaultTTL": 128, "Tcp1323Opts": 3, "SackOpts": 1, "MaxDupAcks": 2},
        "netsh_global": {"autotuninglevel": "normal", "rss": "enabled", "ecncapability": "default", "timestamps": "default"},
        "netsh_supplemental": {"congestionprovider": "default"}
    },
    "Gaming (Low Latency Focus)": {
        "description": "Optimized for lower latency in games. May slightly reduce max throughput on some very high-speed connections.",
        "registry": {"DefaultTTL": 64, "Tcp1323Opts": 3, "SackOpts": 1, "MaxDupAcks": 2},
        "netsh_global": {"autotuninglevel": "restricted", "rss": "enabled", "ecncapability": "disabled", "timestamps": "disabled"},
        "netsh_supplemental": {"congestionprovider": "ctcp"}
    },
    "High-Speed Broadband (Max Throughput)": {
        "description": "For very fast internet connections (e.g., >500 Mbps) to maximize download/upload speeds. ECN enabled.",
        "registry": {"DefaultTTL": 128, "Tcp1323Opts": 3, "SackOpts": 1, "MaxDupAcks": 3},
        "netsh_global": {"autotuninglevel": "normal", "rss": "enabled", "ecncapability": "enabled", "timestamps": "allowed"},
        "netsh_supplemental": {"congestionprovider": "ctcp"}
    },
    "Custom Furia (Balanced Gaming)": {
        "description": "A balanced profile aiming for good gaming performance and general stability.",
        "registry": {"DefaultTTL": 128, "Tcp1323Opts": 3, "SackOpts": 1, "MaxDupAcks": 2},
        "netsh_global": {"autotuninglevel": "normal", "rss": "enabled", "ecncapability": "disabled", "timestamps": "allowed"},
        "netsh_supplemental": {"congestionprovider": "ctcp"}
    }
}


def _parse_netsh_show_output(output_str, key_name, default_val="N/A"):
    """
    Parses 'Key Name        : Value' lines from netsh output.
    Returns the captured value (lowercased), or default_val if not found.
    """
    try:
        pattern = rf"^\s*{re.escape(key_name)}\s*:\s*(\S+)"
        match = re.search(pattern, output_str, re.MULTILINE | re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    except Exception as e:
        GlobalLogger.append(
            f"[TCPOptimizer] Regex parse error for key '{key_name}': {e}",
            is_error=True
        )
    return default_val


def query_current_netsh_settings():
    """
    Queries 'netsh interface tcp show global' and 'netsh interface tcp show supplemental'
    Returns a dict with keys: autotuninglevel, rss, ecncapability, timestamps, congestionprovider.
    """
    if platform.system().lower() != "windows":
        return {}

    settings = {}

    # Query global TCP settings
    global_out = run_shell_command(
        ["netsh", "interface", "tcp", "show", "global"],
        check_return_code=False
    )
    if "Error" not in global_out and global_out:
        settings["autotuninglevel"] = _parse_netsh_show_output(global_out, "Receive Window Auto-Tuning Level")
        settings["rss"] = _parse_netsh_show_output(global_out, "Receive-Side Scaling State")
        settings["ecncapability"] = _parse_netsh_show_output(global_out, "ECN Capability")
        settings["timestamps"] = _parse_netsh_show_output(global_out, "RFC 1323 Timestamps")
    else:
        GlobalLogger.append(
            f"[TCPOptimizer] Error or no output querying netsh global settings: '{global_out}'",
            is_error=True
        )
        for key in ["autotuninglevel", "rss", "ecncapability", "timestamps"]:
            settings[key] = "Error Querying"

    # Query supplemental TCP settings
    supp_out = run_shell_command(
        ["netsh", "int", "tcp", "show", "supplemental"],
        check_return_code=False
    )
    if "Error" not in supp_out and supp_out:
        effective_settings_block = re.search(
            r"Effective settings\s*-+\s*(.*?)(?=\n\s*Template|\Z)",
            supp_out,
            re.DOTALL | re.IGNORECASE
        )
        search_block = effective_settings_block.group(1) if effective_settings_block else supp_out

        congestion_match = re.search(
            r"Congestion Control Provider\s+:\s+(\w+)",
            search_block,
            re.IGNORECASE
        )
        if congestion_match:
            settings["congestionprovider"] = congestion_match.group(1).lower()
        else:
            internet_template_block = re.search(
                r"Template\s*:\s*internet\s*-+\s*(.*?)(?=\n\s*Template|\Z)",
                supp_out,
                re.DOTALL | re.IGNORECASE
            )
            if internet_template_block:
                search_block_internet = internet_template_block.group(1)
                congestion_match_internet = re.search(
                    r"Congestion Control Provider\s+:\s+(\w+)",
                    search_block_internet,
                    re.IGNORECASE
                )
                if congestion_match_internet:
                    settings["congestionprovider"] = congestion_match_internet.group(1).lower()
                else:
                    settings["congestionprovider"] = "N/A (Parse)"
            else:
                settings["congestionprovider"] = "N/A (Parse)"
    else:
        GlobalLogger.append(
            f"[TCPOptimizer] Error or no output querying netsh supplemental settings: '{supp_out}'",
            is_error=True
        )
        settings["congestionprovider"] = "Error Querying"

    return settings


def backup_current_tcp_settings():
    """
    Backs up current registry and netsh TCP settings into BACKUP_FILE (JSON).
    Returns a status message string.
    """
    if platform.system().lower() != "windows":
        return "Backup skipped (Windows-only)."
    GlobalLogger.append("[TCPOptimizer] Backing up current TCP settings.", is_internal=True)

    backup_data = {"registry": {}, "netsh": {}}
    for _, (reg_name, _, _) in TCP_REG_PARAMS_INFO.items():
        if reg_name:
            backup_data["registry"][reg_name] = get_registry_dword(
                REG_PATH_GLOBAL_TCP,
                reg_name,
                "N/A_NotSet"
            )

    backup_data["netsh"] = query_current_netsh_settings()

    try:
        os.makedirs(os.path.dirname(BACKUP_FILE), exist_ok=True)
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=4)
        msg = f"[*] Current TCP settings backed up to {BACKUP_FILE}"
        GlobalLogger.append(msg, is_internal=True)
        return msg
    except Exception as e:
        msg = f"[-] Error backing up TCP settings to {BACKUP_FILE}: {e}"
        GlobalLogger.append(msg, is_error=True)
        return msg


def _apply_profile_logic(profile_name, logs_list_ref):
    """
    Applies the registry and netsh settings for the given profile_name,
    appending log messages to logs_list_ref.
    """
    if platform.system().lower() != "windows":
        return
    profile = TCP_PROFILES.get(profile_name)
    if not profile:
        logs_list_ref.append(f"[-] Profile '{profile_name}' not found.")
        return

    logs_list_ref.append(f"\n[*] Applying Registry settings for '{profile_name}':")
    for reg_name, value in profile.get("registry", {}).items():
        logs_list_ref.append(set_registry_dword(REG_PATH_GLOBAL_TCP, reg_name, value))

    logs_list_ref.append(f"\n[*] Applying Netsh Global settings for '{profile_name}':")
    for setting, value in profile.get("netsh_global", {}).items():
        cmd = ["netsh", "interface", "tcp", "set", "global", f"{setting}={value}"]
        logs_list_ref.append(f"  Executing: {' '.join(cmd)}")
        result = run_shell_command(cmd, check_return_code=False)
        logs_list_ref.append(f"  Result: {result}")
        if "error" in result.lower() or "invalid" in result.lower() or "incorrect" in result.lower():
            GlobalLogger.append(
                f"[TCPOptimizer] Possible error applying netsh global {setting}={value}: {result}",
                is_error=True
            )

    logs_list_ref.append(f"\n[*] Applying Netsh Supplemental settings for '{profile_name}':")
    for setting, value in profile.get("netsh_supplemental", {}).items():
        if setting == "congestionprovider":
            cmd = [
                "netsh", "int", "tcp", "set", "supplemental",
                "template=internet", f"congestionprovider={value}"
            ]
            logs_list_ref.append(f"  Executing: {' '.join(cmd)}")
            result = run_shell_command(cmd, check_return_code=False)
            logs_list_ref.append(f"  Result: {result}")
            if "error" in result.lower() or "invalid" in result.lower() or "incorrect" in result.lower():
                GlobalLogger.append(
                    f"[TCPOptimizer] Possible error applying netsh supplemental {setting}={value}: {result}",
                    is_error=True
                )


def apply_all(profile_name_to_apply):
    """
    Called by Dashboard. Backs up current settings, applies selected profile,
    and returns a concatenated log string.
    """
    if platform.system().lower() != "windows":
        return "TCP Optimization is Windows-only."
    GlobalLogger.append(f"[TCPOptimizer] apply_all called for profile: {profile_name_to_apply}", is_internal=True)

    backup_current_tcp_settings()
    logs = [f"[*] Applying TCP Profile: '{profile_name_to_apply}' (via apply_all)"]
    _apply_profile_logic(profile_name_to_apply, logs)
    logs.append("\n[*] TCP optimization process complete. A system REBOOT is highly recommended for changes to take full effect.")
    final_log_string = "\n".join(logs)
    GlobalLogger.append(
        f"[TCPOptimizer] Profile '{profile_name_to_apply}' application complete. Logs:\n{final_log_string}",
        is_internal=True
    )
    return final_log_string


def restore_settings():
    """
    Called by Restore Defaults and UI button.
    Restores TCP settings from BACKUP_FILE if it exists; otherwise applies Windows default profile.
    Returns a concatenated log string.
    """
    if platform.system().lower() != "windows":
        return "Restore skipped (Windows-only)."
    GlobalLogger.append("[TCPOptimizer] Attempting to restore TCP settings.", is_internal=True)

    logs = []
    profile_to_restore_to = "Windows Default (Recommended Restore)"

    if os.path.exists(BACKUP_FILE):
        try:
            with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            logs.append(f"[*] Restoring TCP settings using backup file: {BACKUP_FILE}")

            # Restore registry settings
            logs.append("\n  Restoring Registry settings from backup:")
            for reg_name, value in backup_data.get("registry", {}).items():
                if value not in ["N/A", "Error", "N/A_NotSet", None]:
                    logs.append(f"    {set_registry_dword(REG_PATH_GLOBAL_TCP, reg_name, value)}")
                elif value in ["N/A_NotSet", None]:
                    try:
                        key = winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE,
                            REG_PATH_GLOBAL_TCP,
                            0,
                            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
                        )
                        winreg.DeleteValue(key, reg_name)
                        winreg.CloseKey(key)
                        logs.append(f"    [*] Registry value {reg_name} deleted (restored to OS default/unset).")
                    except FileNotFoundError:
                        logs.append(
                            f"    [*] Registry value {reg_name} was not set in backup, "
                            "and not found to delete (already default/unset)."
                        )
                    except Exception as e_del:
                        logs.append(f"    [-] Error deleting backed-up registry value {reg_name}: {e_del}")
                else:
                    logs.append(
                        f"    [*] Skipped restoring registry value {reg_name} due to invalid backup value: {value}"
                    )

            # Restore netsh settings
            logs.append("\n  Restoring Netsh settings from backup:")
            backed_up_netsh = backup_data.get("netsh", {})
            applied_from_backup = set()

            for setting, value in backed_up_netsh.items():
                if value not in ["N/A", "Error", "Error Querying", "N/A (Parse)", None, ""]:
                    if setting in TCP_PROFILES[profile_to_restore_to]["netsh_global"]:
                        cmd = ["netsh", "interface", "tcp", "set", "global", f"{setting}={value}"]
                        logs.append(f"    Restoring global '{setting}' to '{value}': {run_shell_command(cmd, False)}")
                        applied_from_backup.add(setting)
                    elif setting in TCP_PROFILES[profile_to_restore_to]["netsh_supplemental"]:
                        cmd = [
                            "netsh", "int", "tcp", "set", "supplemental",
                            "template=internet", f"{setting}={value}"
                        ]
                        logs.append(
                            f"    Restoring supplemental '{setting}' to '{value}' for internet template: "
                            f"{run_shell_command(cmd, False)}"
                        )
                        applied_from_backup.add(setting)
                    else:
                        logs.append(
                            f"    [*] Unknown netsh setting '{setting}' in backup with value '{value}', skipping."
                        )
                else:
                    logs.append(
                        f"    [*] Invalid or missing backup value for netsh setting '{setting}', "
                        f"will apply from '{profile_to_restore_to}' profile if defined there."
                    )

            # Apply defaults for any netsh settings not restored from backup
            logs.append(f"\n  Applying '{profile_to_restore_to}' values for remaining netsh settings:")
            default_profile_netsh_global = TCP_PROFILES[profile_to_restore_to]["netsh_global"]
            for setting, value in default_profile_netsh_global.items():
                if setting not in applied_from_backup:
                    cmd = ["netsh", "interface", "tcp", "set", "global", f"{setting}={value}"]
                    logs.append(
                        f"    Applying default global '{setting}' to '{value}': {run_shell_command(cmd, False)}"
                    )

            default_profile_netsh_supp = TCP_PROFILES[profile_to_restore_to]["netsh_supplemental"]
            for setting, value in default_profile_netsh_supp.items():
                if setting not in applied_from_backup:
                    cmd = [
                        "netsh", "int", "tcp", "set", "supplemental",
                        "template=internet", f"{setting}={value}"
                    ]
                    logs.append(
                        f"    Applying default supplemental '{setting}' to '{value}' for internet template: "
                        f"{run_shell_command(cmd, False)}"
                    )

        except Exception as e_read_backup:
            logs.append(
                f"[-] Error reading or processing backup file '{BACKUP_FILE}': {e_read_backup}. "
                f"Applying full '{profile_to_restore_to}' profile instead."
            )
            GlobalLogger.append(
                f"[TCPOptimizer] Error processing backup: {e_read_backup}. Applying defaults.",
                is_error=True
            )
            _apply_profile_logic(profile_to_restore_to, logs)
    else:
        logs.append(
            f"[*] No backup file found at {BACKUP_FILE}. Applying '{profile_to_restore_to}' profile."
        )
        GlobalLogger.append("[TCPOptimizer] No backup file. Applying default profile.", is_internal=True)
        _apply_profile_logic(profile_to_restore_to, logs)

    logs.append("\n[*] TCP settings restoration process complete. A system REBOOT is highly recommended.")
    return "\n".join(logs)


def query_current_tcp_parameters_for_display():
    """
    Queries current registry and netsh TCP parameters for UI display.
    Returns a dict mapping display names to their current values (strings).
    """
    if platform.system().lower() != "windows":
        return {name: "N/A (Non-Windows)" for name in TCP_REG_PARAMS_INFO.keys()}

    params_display = {}
    for display_name, (reg_name, _, _) in TCP_REG_PARAMS_INFO.items():
        if reg_name:
            params_display[display_name] = str(get_registry_dword(REG_PATH_GLOBAL_TCP, reg_name))

    current_netsh = query_current_netsh_settings()
    params_display["TCP Window Auto-Tuning Level"] = current_netsh.get("autotuninglevel", "N/A")
    params_display["Add-On Congestion Control Provider"] = current_netsh.get("congestionprovider", "N/A")
    params_display["Receive Side Scaling (RSS) State"] = current_netsh.get("rss", "N/A")
    params_display["ECN Capability"] = current_netsh.get("ecncapability", "N/A")
    params_display["RFC 1323 Timestamps (Netsh Global)"] = current_netsh.get("timestamps", "N/A")

    GlobalLogger.append(
        f"[TCPOptimizer] Queried current TCP parameters for display: {params_display}",
        is_internal=True
    )
    return params_display


class TCPOptimizerPage(QWidget):
    """
    Dark-themed "TCP/IP Optimizer" page:
      • Displays current TCP parameters (registry + netsh) in a framed grid.
      • Dropdown to select an optimization profile.
      • Description label for the selected profile.
      • 'Apply Selected Profile' (green) and 'Restore TCP Settings' (red) buttons.
      • Read-only action log (dark background).
      • All existing functionality (backup, apply, restore) preserved exactly.
    """

    def __init__(self, main_window_instance=None):
        super().__init__()
        self.main_window = main_window_instance
        GlobalLogger.append("[TCPOptimizerPage] Initializing.", is_internal=True)

        # Overall dark page background
        self.setStyleSheet("""
            QWidget { background-color: #1E1E2F; font-family: "Segoe UI", sans-serif; }
            QLabel#pageTitle { font-size: 24px; font-weight: bold; color: #FFFFFF; margin-bottom: 15px; }
            QFrame#statsFrame { background-color: #2A2A3E; border: 1px solid #44444F; border-radius: 8px; padding: 15px; }
            QLabel.statHeader { font-size: 16px; font-weight: bold; color: #CFCFDF; margin-bottom: 10px; }
            QLabel.statLabel { font-size: 14px; color: #EEEEEE; font-weight: 500; padding-left: 10px; }
            QLabel.statValue { font-size: 14px; font-weight: bold; color: #5E5EFF; } /* Accent color for values */
            QPushButton#applyBtn {
                background-color: #28A745; border: 1px solid #1E7E34; color: #FFFFFF;
                min-height: 45px; font-size: 14px; border-radius: 5px;
            }
            QPushButton#applyBtn:hover { background-color: #218838; }
            QPushButton#restoreBtn {
                background-color: #FF5E5E; border: 1px solid #E04A4A; color: #FFFFFF;
                min-height: 45px; font-size: 14px; border-radius: 5px;
            }
            QPushButton#restoreBtn:hover { background-color: #E04A4A; }
            QTextEdit#logBox {
                background-color: #1A1A28; color: #EEEEEE; border: 1px solid #44444F;
                border-radius: 5px; font-family: Consolas, monospace; font-size: 12px;
            }
            QComboBox { 
                background-color: #2A2A3E; color: #EEEEEE; border: 1px solid #44444F;
                border-radius: 5px; padding: 5px 10px; font-size: 14px;
            }
            QComboBox:hover { border: 1px solid #5E5EFF; }
        """)

        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(20)
        self.setLayout(main_layout)

        # Page Title
        title = QLabel("TCP/IP Optimizer")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # ─── Stats Frame ───────────────────────────────────────────────────────────
        self.stats_frame = QFrame()
        self.stats_frame.setObjectName("statsFrame")
        self.stats_grid_layout = QGridLayout(self.stats_frame)
        self.stats_grid_layout.setSpacing(10)
        self.stats_grid_layout.setContentsMargins(15, 10, 15, 10)

        stats_header_label = QLabel("Current TCP/IP Parameters:")
        stats_header_label.setObjectName("statHeader")
        self.stats_grid_layout.addWidget(stats_header_label, 0, 0, 1, 4)

        self.displayed_stat_labels = {}
        self._populate_current_stats_display(self.stats_grid_layout, initial_load=True)
        main_layout.addWidget(self.stats_frame)

        # ─── Profile Selection ─────────────────────────────────────────────────────
        profile_hbox = QHBoxLayout()
        profile_hbox.setSpacing(10)
        profile_label = QLabel("Choose Optimization Profile:")
        profile_label.setStyleSheet("font-size: 14px; color: #FFFFFF;")
        profile_hbox.addWidget(profile_label)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(TCP_PROFILES.keys())
        self.profile_combo.setCurrentText("Windows Default (Recommended Restore)")
        self.profile_combo.currentTextChanged.connect(self.update_profile_description_display)
        profile_hbox.addWidget(self.profile_combo)
        profile_hbox.addStretch()
        main_layout.addLayout(profile_hbox)

        self.profile_description_label = QLabel("")
        self.profile_description_label.setWordWrap(True)
        self.profile_description_label.setStyleSheet(
            "font-size: 13px; font-style: italic; color: #CFCFDF; min-height: 40px; padding: 5px 0px;"
        )
        main_layout.addWidget(self.profile_description_label)
        self.update_profile_description_display(self.profile_combo.currentText())

        # ─── Buttons ────────────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.apply_btn = QPushButton("Apply Selected Profile")
        self.apply_btn.setObjectName("applyBtn")
        self.apply_btn.setToolTip("Applies the chosen TCP optimization profile. Admin rights required.")
        self.apply_btn.clicked.connect(self.on_apply_profile_button_click)
        btn_layout.addWidget(self.apply_btn)

        self.restore_btn = QPushButton("Restore TCP Settings")
        self.restore_btn.setObjectName("restoreBtn")
        self.restore_btn.setToolTip("Restores TCP settings from backup, or to Windows defaults if no backup exists.")
        self.restore_btn.clicked.connect(self.on_restore_settings_button_click)
        btn_layout.addWidget(self.restore_btn)

        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # ─── Action Log ──────────────────────────────────────────────────────────────
        log_area_label = QLabel("Action Log:")
        log_area_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF; margin-top: 15px;")
        main_layout.addWidget(log_area_label)

        self.log_text_edit = QTextEdit()
        self.log_text_edit.setObjectName("logBox")
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setMinimumHeight(180)
        main_layout.addWidget(self.log_text_edit)

        main_layout.addStretch(1)

        # On Windows, back up and refresh stats immediately
        if platform.system().lower() == "windows":
            backup_msg = backup_current_tcp_settings()
            self.log_text_edit.append(backup_msg)
            self._refresh_displayed_stats()
        else:
            self.log_text_edit.append("[-] TCP Optimization features are Windows-only.")
            self.apply_btn.setEnabled(False)
            self.restore_btn.setEnabled(False)
            self.profile_combo.setEnabled(False)
            self._populate_current_stats_display(self.stats_grid_layout, initial_load=True)

    def _populate_current_stats_display(self, grid_layout_ref, initial_load=False):
        """
        Populates or refreshes the grid of current TCP parameters.
        initial_load=True sets up QLabel widgets; else updates existing labels' text.
        """
        current_params = query_current_tcp_parameters_for_display()
        row = 1
        col_pair = 0

        display_order = list(TCP_REG_PARAMS_INFO.keys())

        for param_display_name in display_order:
            value_str = str(current_params.get(param_display_name, "N/A"))

            if initial_load:
                name_label = QLabel(f"{param_display_name}:")
                name_label.setObjectName("statLabel")
                name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                value_widget = QLabel(value_str)
                value_widget.setObjectName("statValue")
                value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

                grid_layout_ref.addWidget(name_label, row, col_pair * 2)
                grid_layout_ref.addWidget(value_widget, row, col_pair * 2 + 1)
                self.displayed_stat_labels[param_display_name] = value_widget
            else:
                if param_display_name in self.displayed_stat_labels:
                    self.displayed_stat_labels[param_display_name].setText(value_str)

            col_pair += 1
            if col_pair >= 2:
                col_pair = 0
                row += 1

        if initial_load:
            if col_pair != 0:
                grid_layout_ref.addItem(
                    QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum),
                    row, col_pair * 2 + 2, 1, -1
                )
            grid_layout_ref.setRowStretch(row + 1, 1)
            grid_layout_ref.setColumnStretch(4, 1)

            if not self.displayed_stat_labels and platform.system().lower() == "windows":
                grid_layout_ref.addWidget(
                    QLabel("Could not load current TCP/IP parameters."),
                    1, 0, 1, 4
                )

    def _refresh_displayed_stats(self):
        """
        Refreshes the displayed TCP/IP stats by re-querying and updating labels.
        """
        if platform.system().lower() != "windows":
            return
        GlobalLogger.append("[TCPOptimizerPage] Refreshing displayed TCP/IP statistics.", is_internal=True)
        self._populate_current_stats_display(self.stats_grid_layout, initial_load=False)

    def update_profile_description_display(self, profile_name):
        """
        Updates the profile description label when the combo box changes.
        """
        description = TCP_PROFILES.get(profile_name, {}).get("description", "No description available.")
        self.profile_description_label.setText(f"Info: {description}")

    def on_apply_profile_button_click(self):
        """
        Handles the 'Apply Selected Profile' button click.
        Backs up, applies profile, refreshes stats, and logs.
        """
        selected_profile = self.profile_combo.currentText()
        GlobalLogger.append(
            f"[TCPOptimizerPage] 'Apply Profile' button clicked for: {selected_profile}"
        )

        if platform.system().lower() != "windows":
            return

        confirm_msg = (
            f"You are about to apply the TCP/IP optimization profile: '{selected_profile}'.\n"
            "This will modify system registry and network settings.\n\n"
            "A system REBOOT is highly recommended after applying for changes to take full effect.\n\n"
            "Do you want to proceed?"
        )
        reply = QMessageBox.question(
            self,
            "Confirm TCP Optimization",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            self.log_text_edit.append(f"[*] Application of '{selected_profile}' profile cancelled by user.")
            return

        self.log_text_edit.append(f"[*] Backing up current settings before applying '{selected_profile}'...")
        backup_msg = backup_current_tcp_settings()
        self.log_text_edit.append(backup_msg)

        self.log_text_edit.append(f"\n[*] Applying '{selected_profile}' profile settings...")
        apply_logs = []
        _apply_profile_logic(selected_profile, apply_logs)
        self.log_text_edit.append("\n".join(apply_logs))

        self._refresh_displayed_stats()

        QMessageBox.information(
            self,
            "TCP Optimization Applied",
            f"The '{selected_profile}' profile has been applied.\n"
            "Please review the action log for details.\n\n"
            "A system REBOOT is strongly recommended."
        )
        GlobalLogger.append(f"[TCPOptimizerPage] Profile '{selected_profile}' application process complete.")

    def on_restore_settings_button_click(self):
        """
        Handles the 'Restore TCP Settings' button click.
        Restores from backup if available, else applies Windows default.
        """
        GlobalLogger.append("[TCPOptimizerPage] 'Restore TCP Settings' button clicked.")
        if platform.system().lower() != "windows":
            return

        restore_msg_detail = "from the last backup if available, otherwise to Windows default settings."
        if not os.path.exists(BACKUP_FILE):
            restore_msg_detail = "to Windows default settings (no backup file was found)."

        reply = QMessageBox.question(
            self,
            "Confirm Restore TCP Settings",
            f"This will attempt to restore TCP/IP settings {restore_msg_detail}\n"
            "A system REBOOT is highly recommended after restoring.\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.log_text_edit.append("\n[*] Initiating TCP settings restoration...")
            restore_logs_str = restore_settings()
            self.log_text_edit.append(restore_logs_str)
            self._refresh_displayed_stats()
            QMessageBox.information(
                self,
                "TCP Settings Restored",
                "TCP/IP settings restoration process has finished.\n"
                "Review the log. A REBOOT is highly recommended."
            )
        else:
            self.log_text_edit.append("[*] TCP settings restoration cancelled by user.")

    def shutdown(self):
        """
        Called when the application is closing.
        Logs shutdown; no additional cleanup needed here.
        """
        GlobalLogger.append("[TCPOptimizerPage] Shutdown.", is_internal=True)

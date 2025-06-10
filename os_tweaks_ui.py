# os_tweaks_ui.py

import subprocess
import platform
import re
import winreg
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QMessageBox,
    QSpacerItem,
    QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from visual_tweaks_and_logs import GlobalLogger


class OSTweaksPage(QWidget):
    """
    “OS Tweaks” page:
      - Title: “Operating System Tweaks”
      - Buttons:
          • Activate Windows Game Mode
          • Deactivate Windows Game Mode
          • Apply All Recommended OS Tweaks
          • Restore Original OS Settings
      - Dark theme: dark backgrounds (#1E1E2F), light text (#FFFFFF).
      - Blue buttons (#5E5EFF) and red buttons (#FF5E5E) to match the app’s accent colors.
      - Preserves all original functionality, including registry and subprocess logic.
      - Logs every action to GlobalLogger.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        GlobalLogger.append("[OSTweaksPage] Initializing.", is_internal=True)

        # Set dark background color for this page
        self.setStyleSheet("background-color: #1E1E2F;")

        # Main vertical layout with padding and spacing
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        self.setLayout(main_layout)

        # Page Title
        title_label = QLabel("Operating System Tweaks")
        title_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #FFFFFF;")
        main_layout.addWidget(title_label)

        # Common button style definitions
        button_base_style = """
            font-size: 16px;
            border-radius: 6px;
            padding: 10px 20px;
            min-height: 50px;
            font-weight: 500;
            color: #FFFFFF;
        """
        button_style_blue = f"""
            QPushButton {{
                {button_base_style}
                background-color: #5E5EFF;
                border: 1px solid #4A4AFF;
            }}
            QPushButton:hover {{ background-color: #4A4AFF; }}
            QPushButton:pressed {{ background-color: #3A3AE6; }}
            QPushButton:disabled {{ background-color: #3e3e5e; color: #AAAAAA; border-color: #3e3e5e; }}
        """
        button_style_red = f"""
            QPushButton {{
                {button_base_style}
                background-color: #FF5E5E;
                border: 1px solid #E04A4A;
            }}
            QPushButton:hover {{ background-color: #E04A4A; }}
            QPushButton:pressed {{ background-color: #C43939; }}
            QPushButton:disabled {{ background-color: #652e2e; color: #AAAAAA; border-color: #652e2e; }}
        """

        # Button: Activate Windows Game Mode
        self.activate_gm_btn = QPushButton("Activate Windows Game Mode")
        self.activate_gm_btn.setStyleSheet(button_style_blue)
        self.activate_gm_btn.setToolTip("Enables settings to optimize your PC for gaming.")
        self.activate_gm_btn.clicked.connect(self.activate_game_mode_action)
        main_layout.addWidget(self.activate_gm_btn)

        # Button: Deactivate Windows Game Mode
        self.deactivate_gm_btn = QPushButton("Deactivate Windows Game Mode")
        self.deactivate_gm_btn.setStyleSheet(button_style_red)
        self.deactivate_gm_btn.setToolTip("Reverts Game Mode optimizations.")
        self.deactivate_gm_btn.clicked.connect(self.deactivate_game_mode_action)
        main_layout.addWidget(self.deactivate_gm_btn)

        # Spacer between Game Mode buttons and All Tweaks buttons
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Button: Apply All Recommended OS Tweaks
        self.apply_tweaks_btn = QPushButton("Apply All Recommended OS Tweaks")
        self.apply_tweaks_btn.setStyleSheet(button_style_blue)
        self.apply_tweaks_btn.setToolTip("Applies a set of general OS optimizations for performance.")
        self.apply_tweaks_btn.clicked.connect(self.apply_all_tweaks_action)
        main_layout.addWidget(self.apply_tweaks_btn)

        # Button: Restore Original OS Settings
        self.restore_settings_btn = QPushButton("Restore Original OS Settings")
        self.restore_settings_btn.setStyleSheet(button_style_red)
        self.restore_settings_btn.setToolTip("Attempts to revert changes made by 'Apply All OS Tweaks'.")
        self.restore_settings_btn.clicked.connect(self.restore_os_settings_action)
        main_layout.addWidget(self.restore_settings_btn)

        main_layout.addStretch(1)

        # Store original power plan GUID at initialization
        self._original_power_plan_guid = self._get_current_power_plan_guid()

    def _get_current_power_plan_guid(self):
        """
        Retrieves the GUID of the current active power plan (Windows only).
        """
        if platform.system().lower() != "windows":
            return None
        try:
            result = subprocess.run(
                ["powercfg", "/getactivescheme"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                creationflags=0x08000000
            )
            output = result.stdout.strip()
            guid_match = re.search(r"GUID: ([A-Fa-f0-9-]+)", output)
            if guid_match:
                guid = guid_match.group(1)
                GlobalLogger.append(f"[OSTweaksPage] Current active power plan GUID: {guid}", is_internal=True)
                return guid
        except Exception as e:
            GlobalLogger.append(f"[OSTweaksPage] Failed to get current power plan GUID: {e}", is_error=True)
        return None

    def _set_game_mode_registry(self, enable: bool):
        """
        Enables or disables Windows Game Mode via registry.
        Returns True on success, False on failure.
        """
        if platform.system().lower() != "windows":
            QMessageBox.information(self, "OS Tweaks", "Game Mode tweaks are available on Windows only.")
            GlobalLogger.append("[OSTweaksPage] Attempted Game Mode on non-Windows.", is_internal=True)
            return False
        try:
            # HKEY_CURRENT_USER\Software\Microsoft\GameBar -> AllowAutoGameMode
            reg_path_gamebar = r"Software\Microsoft\GameBar"
            key_gamebar = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path_gamebar)
            winreg.SetValueEx(key_gamebar, "AllowAutoGameMode", 0, winreg.REG_DWORD, 1 if enable else 0)
            winreg.CloseKey(key_gamebar)

            # HKEY_CURRENT_USER\System\GameConfigStore -> GameDVR_Enabled
            reg_path_gamedvr = r"System\GameConfigStore"
            key_dvr = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path_gamedvr)
            winreg.SetValueEx(key_dvr, "GameDVR_Enabled", 0, winreg.REG_DWORD, 1 if enable else 0)
            winreg.CloseKey(key_dvr)

            GlobalLogger.append(f"[OSTweaksPage] Game Mode {'enabled' if enable else 'disabled'} in registry.", is_internal=True)
            return True
        except Exception as ex:
            GlobalLogger.append(f"[OSTweaksPage] Failed to set Game Mode registry: {ex}", is_error=True)
            QMessageBox.critical(self, "Registry Error", f"Failed to modify Game Mode registry:\n{ex}")
            return False

    def activate_game_mode_action(self):
        GlobalLogger.append("[OSTweaksPage] Activate Game Mode clicked.")
        if self._set_game_mode_registry(enable=True):
            QMessageBox.information(
                self,
                "Game Mode Activated",
                "Windows Game Mode has been ACTIVATED.\nA system restart might be required for full effect."
            )

    def deactivate_game_mode_action(self):
        GlobalLogger.append("[OSTweaksPage] Deactivate Game Mode clicked.")
        if self._set_game_mode_registry(enable=False):
            QMessageBox.information(
                self,
                "Game Mode Deactivated",
                "Windows Game Mode has been DEACTIVATED.\nA system restart might be required for full effect."
            )

    def _run_shell_command_silent(self, command_parts, log_message_base=""):
        """
        Runs a shell command silently (Windows only). Returns (success: bool, message: str).
        """
        if platform.system().lower() != "windows":
            GlobalLogger.append(f"[OSTweaksPage] Skipping command on non-Windows: {' '.join(command_parts)}", is_internal=True)
            return False, "Unsupported OS"
        try:
            process = subprocess.run(
                command_parts,
                shell=False,
                capture_output=True,
                text=True,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            if process.returncode == 0:
                GlobalLogger.append(f"[OSTweaksPage] {log_message_base}: succeeded.", is_internal=True)
                return True, "Success"
            else:
                error_details = process.stderr.strip() or process.stdout.strip() or f"Return code {process.returncode}"
                GlobalLogger.append(f"[OSTweaksPage] {log_message_base}: failed: {error_details}", is_error=True)
                return False, error_details
        except FileNotFoundError:
            msg = f"Command not found: {command_parts[0]}"
            GlobalLogger.append(f"[OSTweaksPage] {log_message_base}: {msg}", is_error=True)
            return False, msg
        except Exception as ex:
            msg = f"Error executing {command_parts}: {ex}"
            GlobalLogger.append(f"[OSTweaksPage] {log_message_base}: {msg}", is_error=True)
            return False, msg

    def apply_all_tweaks_action(self):
        GlobalLogger.append("[OSTweaksPage] Apply All OS Tweaks clicked.")
        reply = QMessageBox.question(
            self,
            "Confirm OS Tweaks",
            ("This will activate Game Mode, set a high-performance power plan, "
             "disable Superfetch (SysMain), and disable Xbox Game Bar. Proceed?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            GlobalLogger.append("[OSTweaksPage] OS Tweaks canceled by user.", is_internal=True)
            return

        results_summary = []

        # 1. Enable Game Mode
        if self._set_game_mode_registry(enable=True):
            results_summary.append("Game Mode: Activated")
        else:
            results_summary.append("Game Mode: Activation failed")

        # 2. Power Plan (Ultimate if available, else High Performance)
        ultimate_guid = "e9a42b02-d5df-448d-aa00-03f14749eb61"
        high_perf_guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
        chosen_guid = high_perf_guid
        plan_name = "High Performance"
        if platform.system().lower() == "windows":
            try:
                output = subprocess.check_output(
                    ["powercfg", "/list"],
                    universal_newlines=True,
                    creationflags=0x08000000
                )
                if ultimate_guid in output:
                    chosen_guid = ultimate_guid
                    plan_name = "Ultimate Performance"
            except Exception as e:
                GlobalLogger.append(f"[OSTweaksPage] Error listing power plans: {e}", is_error=True)
        success_power, msg_power = self._run_shell_command_silent(
            ["powercfg", "/setactive", chosen_guid],
            f"Set Power Plan to {plan_name}"
        )
        results_summary.append(f"Power Plan ({plan_name}): {'Applied' if success_power else f'Failed: {msg_power}'}")

        # 3. Disable Superfetch (SysMain)
        success_stop, _ = self._run_shell_command_silent(
            ["sc", "stop", "SysMain"], "Stop SysMain"
        )
        success_config, msg_config = self._run_shell_command_silent(
            ["sc", "config", "SysMain", "start=", "disabled"], "Disable SysMain"
        )
        results_summary.append(f"SysMain Service: {'Disabled' if success_config else f'Failed: {msg_config}'}")

        # 4. Disable Xbox Game Bar (AppCaptureEnabled) via registry
        try:
            if platform.system().lower() == "windows":
                reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR"
                key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path)
                winreg.SetValueEx(key, "AppCaptureEnabled", 0, winreg.REG_DWORD, 0)
                winreg.CloseKey(key)
                results_summary.append("Xbox Game Bar: Disabled")
                GlobalLogger.append("[OSTweaksPage] AppCaptureEnabled set to 0", is_internal=True)
        except Exception as ex_gamedvr:
            results_summary.append(f"Xbox Game Bar: Disable failed ({ex_gamedvr})")
            GlobalLogger.append(f"[OSTweaksPage] Failed disabling Game DVR: {ex_gamedvr}", is_error=True)

        GlobalLogger.append("[OSTweaksPage] Completed applying all OS tweaks.")
        QMessageBox.information(
            self,
            "OS Tweaks Applied",
            "Tweaks applied. Summary:\n- " + "\n- ".join(results_summary) +
            "\n\nA restart is recommended for full effect."
        )

    def restore_os_settings_action(self):
        GlobalLogger.append("[OSTweaksPage] Restore OS Settings clicked.")
        reply = QMessageBox.question(
            self,
            "Confirm Restore OS Settings",
            ("This will deactivate Game Mode, restore the original power plan, "
             "re-enable SysMain, and re-enable Xbox Game Bar. Proceed?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            GlobalLogger.append("[OSTweaksPage] Restore OS canceled by user.", is_internal=True)
            return

        results_summary = []

        # 1. Deactivate Game Mode
        if self._set_game_mode_registry(enable=False):
            results_summary.append("Game Mode: Deactivated")
        else:
            results_summary.append("Game Mode: Deactivation failed")

        # 2. Restore original or Balanced power plan
        balanced_guid = "381b4222-f694-41f0-9685-ff5bb260df2e"
        guid_to_restore = self._original_power_plan_guid or balanced_guid
        plan_name = "Original" if self._original_power_plan_guid else "Balanced"
        success_restore, msg_restore = self._run_shell_command_silent(
            ["powercfg", "/setactive", guid_to_restore],
            f"Restore Power Plan to {plan_name}"
        )
        results_summary.append(f"Power Plan ({plan_name}): {'Restored' if success_restore else f'Failed: {msg_restore}'}")

        # 3. Re-enable SysMain service
        success_reconfig, msg_reconfig = self._run_shell_command_silent(
            ["sc", "config", "SysMain", "start=", "auto"], "Re-enable SysMain"
        )
        if success_reconfig:
            results_summary.append("SysMain Service: Set to Automatic")
            self._run_shell_command_silent(["sc", "start", "SysMain"], "Start SysMain")
        else:
            results_summary.append(f"SysMain Service: Re-enable failed ({msg_reconfig})")

        # 4. Re-enable Xbox Game Bar (AppCaptureEnabled) in registry
        try:
            if platform.system().lower() == "windows":
                reg_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR"
                key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path)
                winreg.SetValueEx(key, "AppCaptureEnabled", 0, winreg.REG_DWORD, 1)
                winreg.CloseKey(key)
                results_summary.append("Xbox Game Bar: Re-enabled")
                GlobalLogger.append("[OSTweaksPage] AppCaptureEnabled set to 1", is_internal=True)
        except Exception as ex_gamedvr_restore:
            results_summary.append(f"Xbox Game Bar: Re-enable failed ({ex_gamedvr_restore})")
            GlobalLogger.append(f"[OSTweaksPage] Failed re-enabling Game DVR: {ex_gamedvr_restore}", is_error=True)

        GlobalLogger.append("[OSTweaksPage] Completed restoring OS settings.")
        QMessageBox.information(
            self,
            "OS Settings Restored",
            "Original settings restored. Summary:\n- " + "\n- ".join(results_summary) +
            "\n\nA restart is recommended for full effect."
        )

    def shutdown(self):
        """Called when the application is closing."""
        GlobalLogger.append("[OSTweaksPage] Shutdown.", is_internal=True)
        # No additional cleanup needed here compared to original file


# If run standalone for testing:
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = OSTweaksPage()
    window.show()
    sys.exit(app.exec())

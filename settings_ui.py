# settings_ui.py

import os
import sys
import json
import subprocess  # For DNS restore
import platform
import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QCheckBox, QComboBox,
    QPushButton, QHBoxLayout, QListWidget, QLineEdit,
    QMessageBox, QTextEdit, QApplication, QSpacerItem, QSizePolicy,
    QFrame, QScrollArea
)
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QFont, QFontDatabase

from visual_tweaks_and_logs import GlobalLogger
from utils.path_utils import app_data_path

from roblox_tweaks_ui import RobloxTweaksPage as RTPageForRestore
from os_tweaks_ui import OSTweaksPage as OSTweaksPageForRestore
from tcp_optimizer_ui import restore_settings as restore_tcp_settings_backup
from tcp_optimizer_ui import BACKUP_FILE as TCP_BACKUP_FILE

SETTINGS_FILE = app_data_path('settings.ini')
PROFILES_DIR = app_data_path('profiles')

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

class SettingsPage(QWidget):
    """
    "Settings & Logs" page, modern dark-themed.

    Features:
    - General Configuration: run_on_startup, run_as_admin, auto_optimize_on_launch
    - (Removed Theme selection since app is permanently dark-themed)
    - Profiles: save, load, delete JSON profiles of these settings
    - Application Log Viewer: view, refresh, clear logs
    - Full Restore to Defaults: reverts all app + system tweaks
    """

    def __init__(self, main_window_instance=None):
        super().__init__()
        self.main_window = main_window_instance
        GlobalLogger.append("[SettingsPage] Initializing.", is_internal=True)

        # QSettings for persistent settings
        self.settings_handler = QSettings(SETTINGS_FILE, QSettings.Format.IniFormat)

        # ---------- Overall Page Style ----------
        # Dark background and light text, consistent with modern UI
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #1E1E2F;
                color: #E0E0E0;
                font-family: "{CUSTOM_FONT}", sans-serif;
            }}
            QLabel#pageTitle {{
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 15px;
                color: #FFFFFF;
            }}
            QLabel.sectionTitle {{
                font-size: 18px;
                font-weight: bold;
                margin-top: 20px;
                margin-bottom: 8px;
                color: #CFCFDF;
            }}
            QCheckBox {{
                font-size: 14px;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 1px solid #666;
                background: #2A2A3E;
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background: #5E5EFF;
                border: 1px solid #5E5EFF;
                border-radius: 3px;
            }}
            QComboBox, QLineEdit, QListWidget {{
                background-color: #2A2A3E;
                color: #E0E0E0;
                border: 1px solid #44444F;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14px;
            }}
            QComboBox:hover, QLineEdit:hover, QListWidget:hover {{
                border: 1px solid #5E5EFF;
            }}
            QPushButton {{
                font-size: 14px;
                color: #FFFFFF;
                padding: 10px 18px;
                border-radius: 6px;
                font-weight: 500;
                min-height: 40px;
                background-color: #5E5EFF;
                border: 1px solid #4A4AFF;
            }}
            QPushButton:hover {{
                background-color: #4A4AFF;
            }}
            QPushButton:pressed {{
                background-color: #3A3AE6;
            }}
            QPushButton:disabled {{
                background-color: #3e3e5e;
                color: #AAAAAA;
                border-color: #3e3e5e;
            }}
            QPushButton#restoreAllBtn {{
                background-color: #FF5E5E;
                border: 1px solid #E04A4A;
                font-weight: bold;
            }}
            QPushButton#restoreAllBtn:hover {{
                background-color: #E04A4A;
            }}
            QTextEdit#logViewer {{
                background-color: #2A2A3E;
                color: #E0E0E0;
                border: 1px solid #44444F;
                border-radius: 5px;
                font-family: Consolas, monospace;
                font-size: 12px;
                padding: 8px;
            }}
            QFrame#restoreFrame {{
                background-color: #2A2A3E;
                border: 2px solid #FF5E5E;
                border-radius: 8px;
                margin-top: 25px;
                padding: 18px;
            }}
            QLabel#restoreTitle {{
                font-size: 20px;
                font-weight: bold;
                color: #FF5E5E;
                margin-bottom: 12px;
                qproperty-alignment: AlignCenter;
            }}
            QLabel#restoreInfoLabel {{
                font-size: 13px;
                color: #E0E0E0;
                line-height: 1.4;
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)

        # ---------- Main Scroll Area & Content ----------
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(35, 30, 35, 30)
        content_layout.setSpacing(20)

        # Page Title
        title = QLabel("Application Settings & Logs")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(title)

        # --- General Configuration Section ---
        general_settings_label = QLabel("General Configuration")
        general_settings_label.setObjectName("sectionTitle")
        content_layout.addWidget(general_settings_label)

        # Run on Startup
        self.startup_chk = QCheckBox("Run Roblox Optimizer Pro on System Startup")
        self.startup_chk.setChecked(self.settings_handler.value("run_on_startup", False, type=bool))
        self.startup_chk.setToolTip("If checked, the application will attempt to start when Windows boots.")
        content_layout.addWidget(self.startup_chk)

        # Always run as Admin
        self.admin_chk = QCheckBox("Always Attempt to Run as Administrator (Recommended)")
        self.admin_chk.setChecked(self.settings_handler.value("run_as_admin", True, type=bool))
        self.admin_chk.setToolTip("Ensures features requiring elevation work correctly. Restart app after changing.")
        content_layout.addWidget(self.admin_chk)

        # Auto-Optimize on Launch
        self.autoopt_chk = QCheckBox("Enable Auto-Optimize on Roblox Launch")
        self.autoopt_chk.setChecked(self.settings_handler.value("auto_optimize_on_launch", False, type=bool))
        self.autoopt_chk.setToolTip("If checked, Auto-Optimize runs before Roblox starts via the Dashboard.")
        content_layout.addWidget(self.autoopt_chk)

        # (Theme selection removed—app is permanently dark)

        # --- Profile Management Section ---
        prof_label = QLabel("Settings Profiles")
        prof_label.setObjectName("sectionTitle")
        content_layout.addWidget(prof_label)

        # Ensure profiles directory exists
        if not os.path.exists(PROFILES_DIR):
            try:
                os.makedirs(PROFILES_DIR, exist_ok=True)
                GlobalLogger.append(f"[SettingsPage] Created profiles directory: {PROFILES_DIR}", is_internal=True)
            except OSError as e:
                GlobalLogger.append(f"[SettingsPage] Error creating profiles directory {PROFILES_DIR}: {e}", is_error=True)

        self.profile_list = QListWidget()
        self.profile_list.setFixedHeight(120)
        self.refresh_profile_list_display()
        content_layout.addWidget(self.profile_list)

        self.profile_input = QLineEdit()
        self.profile_input.setPlaceholderText("Enter new profile name here to save current settings")
        content_layout.addWidget(self.profile_input)

        prof_btn_layout = QHBoxLayout()
        self.save_profile_btn = QPushButton("Save Current as Profile")
        self.load_profile_btn = QPushButton("Load Selected Profile")
        self.delete_profile_btn = QPushButton("Delete Selected Profile")
        prof_btn_layout.addWidget(self.save_profile_btn)
        prof_btn_layout.addWidget(self.load_profile_btn)
        prof_btn_layout.addWidget(self.delete_profile_btn)
        content_layout.addLayout(prof_btn_layout)

        # --- Application Log Viewer Section ---
        logs_label = QLabel("Application Log Viewer")
        logs_label.setObjectName("sectionTitle")
        content_layout.addWidget(logs_label)

        self.log_viewer = QTextEdit()
        self.log_viewer.setObjectName("logViewer")
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMinimumHeight(200)
        content_layout.addWidget(self.log_viewer)

        log_btn_layout = QHBoxLayout()
        self.refresh_log_button = QPushButton("Refresh Log View")
        self.clear_log_button = QPushButton("Clear Log File")
        log_btn_layout.addWidget(self.refresh_log_button)
        log_btn_layout.addWidget(self.clear_log_button)
        content_layout.addLayout(log_btn_layout)

        # --- Restore Defaults Section ---
        restore_frame = QFrame()
        restore_frame.setObjectName("restoreFrame")
        restore_layout_inner = QVBoxLayout(restore_frame)
        restore_layout_inner.setSpacing(12)

        restore_title_label = QLabel("Restore All Application & System Settings to Defaults")
        restore_title_label.setObjectName("restoreTitle")
        restore_layout_inner.addWidget(restore_title_label)

        restore_info_label = QLabel(
            "Warning: This action will attempt to revert settings modified by this application "
            "to their original or a safe default state. This includes OS tweaks (Game Mode, Power Plan, SysMain), "
            "network configurations (DNS to DHCP, TCP settings from any backup), and will stop related processes "
            "like the FPS unlocker. Application settings (startup, admin) will also be reset. The log file will be cleared. "
            "This process is largely irreversible. Proceed with caution."
        )
        restore_info_label.setObjectName("restoreInfoLabel")
        restore_info_label.setWordWrap(True)
        restore_layout_inner.addWidget(restore_info_label)

        self.restore_all_defaults_btn = QPushButton("Perform Full Restore")
        self.restore_all_defaults_btn.setObjectName("restoreAllBtn")
        self.restore_all_defaults_btn.setToolTip("Click to reset application-managed settings and system tweaks to defaults.")
        restore_layout_inner.addWidget(self.restore_all_defaults_btn, alignment=Qt.AlignCenter)

        content_layout.addWidget(restore_frame)

        self.content_widget.setLayout(content_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.content_widget)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        main_page_layout = QVBoxLayout(self)
        main_page_layout.setContentsMargins(0, 0, 0, 0)
        main_page_layout.addWidget(scroll_area)
        self.setLayout(main_page_layout)

        # -------- Connect Signals ----------
        self.save_profile_btn.clicked.connect(self.save_current_settings_as_profile)
        self.load_profile_btn.clicked.connect(self.load_selected_profile)
        self.delete_profile_btn.clicked.connect(self.delete_selected_profile)
        self.refresh_log_button.clicked.connect(self.refresh_log_display_action)
        self.clear_log_button.clicked.connect(self.clear_log_file_action)
        self.restore_all_defaults_btn.clicked.connect(self.execute_full_restore_to_defaults)

        # Load log on initialization
        self.refresh_log_display_action()
        GlobalLogger.append("[SettingsPage] Initialization complete with QScrollArea.", is_internal=True)

    def refresh_profile_list_display(self):
        """
        Refresh the QListWidget that shows saved profiles (JSON files in PROFILES_DIR).
        """
        self.profile_list.clear()
        if not os.path.exists(PROFILES_DIR):
            try:
                os.makedirs(PROFILES_DIR, exist_ok=True)
            except OSError:
                pass

        if os.path.exists(PROFILES_DIR):
            try:
                for file_name in os.listdir(PROFILES_DIR):
                    if file_name.endswith(".json"):
                        self.profile_list.addItem(file_name[:-5])
            except OSError as e:
                GlobalLogger.append(f"[SettingsPage] Error reading profiles directory {PROFILES_DIR}: {e}", is_error=True)
        GlobalLogger.append("[SettingsPage] Profile list refreshed.", is_internal=True)

    def save_current_settings_as_profile(self):
        """
        Save current general settings (startup/admin/autoopt) into a JSON profile.
        """
        profile_name = self.profile_input.text().strip()
        if not profile_name:
            QMessageBox.warning(self, "Save Profile Error", "Please enter a name for the settings profile.")
            return
        if any(c in profile_name for c in r'\/:*?"<>|'):
            QMessageBox.warning(self, "Save Profile Error", "Profile name contains invalid characters.")
            return

        profile_data = {
            "run_on_startup": self.startup_chk.isChecked(),
            "run_as_admin": self.admin_chk.isChecked(),
            "auto_optimize_on_launch": self.autoopt_chk.isChecked(),
        }
        file_path = os.path.join(PROFILES_DIR, profile_name + ".json")
        try:
            os.makedirs(PROFILES_DIR, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=4)
            self.refresh_profile_list_display()
            self.profile_input.clear()
            QMessageBox.information(self, "Profile Saved", f"Settings profile '{profile_name}' saved.")
            GlobalLogger.append(f"[SettingsPage] Profile '{profile_name}' saved.")
        except Exception as e:
            QMessageBox.critical(self, "Save Profile Error", f"Failed to save profile '{profile_name}':\n{e}")
            GlobalLogger.append(f"[SettingsPage] Error saving profile '{profile_name}': {e}", is_error=True)

    def load_selected_profile(self):
        """
        Load the JSON profile selected in the list, apply it to the UI and QSettings.
        """
        current_item = self.profile_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Load Profile Error", "Please select a profile to load.")
            return

        profile_name = current_item.text()
        file_path = os.path.join(PROFILES_DIR, profile_name + ".json")
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "Load Profile Error", f"Profile file not found: {file_path}")
            self.refresh_profile_list_display()
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                profile_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Load Profile Error", f"Failed to read profile '{profile_name}':\n{e}")
            return

        # Apply loaded values to checkboxes
        self.startup_chk.setChecked(profile_data.get("run_on_startup", False))
        self.admin_chk.setChecked(profile_data.get("run_as_admin", True))
        self.autoopt_chk.setChecked(profile_data.get("auto_optimize_on_launch", False))

        # Save loaded settings back to QSettings
        self.settings_handler.setValue("run_on_startup", self.startup_chk.isChecked())
        self.settings_handler.setValue("run_as_admin", self.admin_chk.isChecked())
        self.settings_handler.setValue("auto_optimize_on_launch", self.autoopt_chk.isChecked())
        self.settings_handler.sync()

        # No theme to apply anymore

        QMessageBox.information(self, "Profile Loaded", f"Settings profile '{profile_name}' loaded and applied.")
        GlobalLogger.append(f"[SettingsPage] Profile '{profile_name}' loaded.")

    def delete_selected_profile(self):
        """
        Delete the JSON profile selected in the list.
        """
        current_item = self.profile_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Delete Profile Error", "Please select a profile to delete.")
            return

        profile_name = current_item.text()
        reply = QMessageBox.question(
            self, "Confirm Delete Profile",
            f"Are you sure you want to permanently delete the settings profile '{profile_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            file_path = os.path.join(PROFILES_DIR, profile_name + ".json")
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    self.refresh_profile_list_display()
                    QMessageBox.information(self, "Profile Deleted", f"Profile '{profile_name}' deleted.")
                    GlobalLogger.append(f"[SettingsPage] Profile '{profile_name}' deleted.")
                else:
                    QMessageBox.warning(self, "Delete Profile Error", f"Profile file '{profile_name}' not found.")
                    self.refresh_profile_list_display()
            except Exception as e:
                QMessageBox.critical(self, "Delete Profile Error", f"Failed to delete profile '{profile_name}':\n{e}")
                GlobalLogger.append(f"[SettingsPage] Error deleting profile '{profile_name}': {e}", is_error=True)

    def refresh_log_display_action(self):
        """
        Load the latest log from GlobalLogger into the QTextEdit.
        """
        GlobalLogger.append("[SettingsPage] Refresh Log View clicked.", is_internal=True)
        self.log_viewer.setPlainText(GlobalLogger.get_log())
        scrollbar = self.log_viewer.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log_file_action(self):
        """
        Prompts user to confirm and then clears the log file.
        """
        GlobalLogger.append("[SettingsPage] Clear Log File clicked.", is_internal=True)
        reply = QMessageBox.question(
            self, "Confirm Clear Log File",
            "Are you sure you want to permanently clear the application's log file? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            status_msg = GlobalLogger.clear_log()
            self.log_viewer.setPlainText(status_msg + "\nLog is now empty.")
            GlobalLogger.append(f"[SettingsPage] Log file cleared by user. Status: {status_msg}", is_internal=True)
            QMessageBox.information(self, "Log File Cleared", status_msg)

    def execute_full_restore_to_defaults(self):
        """
        Restores all settings (app + system) to defaults. This is largely irreversible.
        """
        GlobalLogger.append("[SettingsPage] 'Perform Full Restore' button clicked.", is_internal=True)
        reply = QMessageBox.warning(
            self, "Confirm Full Restore",
            "This will reset application settings and attempt to revert system tweaks.\n"
            "ARE YOU ABSOLUTELY SURE YOU WANT TO PROCEED?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            GlobalLogger.append("[SettingsPage] Full restore cancelled by user.", is_internal=True)
            return

        # Prepare a small text area to log summary (appended to log_viewer)
        summary_log = ["[+] Full Restore to Defaults - Summary:"]

        # 1. Reset Application Settings to default
        GlobalLogger.append("[RestoreDefaults] Resetting application settings to defaults.", is_internal=True)
        self.startup_chk.setChecked(False)
        self.admin_chk.setChecked(True)
        self.autoopt_chk.setChecked(False)
        self.settings_handler.setValue("run_on_startup", False)
        self.settings_handler.setValue("run_as_admin", True)
        self.settings_handler.setValue("auto_optimize_on_launch", False)
        self.settings_handler.sync()
        summary_log.append("- Application Settings: Reset to defaults (run_on_startup=False, run_as_admin=True, autoopt=False).")

        # 2. Terminate FPS Unlocker
        try:
            rt_page_temp = RTPageForRestore()
            rt_page_temp.terminate_fps_unlocker_action()
            summary_log.append("- Roblox FPS Unlocker: Termination attempted.")
        except Exception as e_fps:
            summary_log.append(f"- Roblox FPS Unlocker: Error during termination ({e_fps}).")
            GlobalLogger.append(f"[RestoreDefaults] Error terminating FPS Unlocker: {e_fps}", is_error=True)

        # 3. Restore OS Tweaks
        try:
            os_tweaks_temp = OSTweaksPageForRestore()
            os_tweaks_temp.restore_os_settings_action()
            summary_log.append("- OS Tweaks: Restoration process initiated.")
        except Exception as e_os:
            summary_log.append(f"- OS Tweaks: Error initiating restoration ({e_os}).")
            GlobalLogger.append(f"[RestoreDefaults] Error initiating OS Tweaks restoration: {e_os}", is_error=True)

        # 4. Restore DNS to DHCP (Windows only)
        if platform.system().lower().startswith("win"):
            try:
                interfaces_output = subprocess.check_output(
                    ["netsh", "interface", "show", "interface"],
                    universal_newlines=True,
                    creationflags=0x08000000,
                    encoding='utf-8',
                    errors='ignore'
                )
                restored_dns_ifaces = []
                for line in interfaces_output.splitlines():
                    if re.match(r"^\s*Enabled\s+Connected", line, re.IGNORECASE):
                        parts = re.split(r"\s{2,}", line.strip())
                        if len(parts) >= 3:
                            iface_name = parts[-1]
                            if iface_name:
                                subprocess.run(
                                    ["netsh", "interface", "ipv4", "set", "dns", f"name=\"{iface_name}\"", "source=dhcp"],
                                    check=False,
                                    creationflags=0x08000000
                                )
                                subprocess.run(
                                    ["netsh", "interface", "ipv6", "set", "dns", f"name=\"{iface_name}\"", "source=dhcp"],
                                    check=False,
                                    creationflags=0x08000000
                                )
                                restored_dns_ifaces.append(iface_name)
                msg_dns = f"- DNS: Restored to DHCP for interfaces: {', '.join(restored_dns_ifaces) if restored_dns_ifaces else 'No active interfaces found'}."
                summary_log.append(msg_dns)
            except Exception as e_dns:
                summary_log.append(f"- DNS: Failed to restore to DHCP: {e_dns}")
                GlobalLogger.append(f"[RestoreDefaults] DNS restore error: {e_dns}", is_error=True)
        else:
            summary_log.append("- DNS: Restore to DHCP is Windows-specific, skipped.")

        # 5. Restore TCP Settings
        try:
            tcp_restore_logs = restore_tcp_settings_backup()
            summary_log.append("- TCP Settings: Restoration to backup/defaults attempted.")
            GlobalLogger.append(f"[RestoreDefaults] TCP settings restore attempt logs:\n{tcp_restore_logs}")
        except Exception as e_tcp:
            summary_log.append(f"- TCP Settings: Error during restore attempt ({e_tcp}).")
            GlobalLogger.append(f"[RestoreDefaults] Error restoring TCP settings: {e_tcp}", is_error=True)

        # 6. Clear application log file
        clear_log_status = GlobalLogger.clear_log()
        summary_log.append(f"- Application Log File: {clear_log_status}")
        self.refresh_log_display_action()

        # Show summary in log_viewer and info dialog
        final_summary_text = "\n".join(summary_log)
        self.log_viewer.append(f"\n{final_summary_text}")
        QMessageBox.information(
            self, "Full Restore Complete",
            "The full restore to defaults sequence has finished.\n"
            "Some changes may require a system restart.\n\n"
            "Summary of actions:\n" + final_summary_text
        )
        GlobalLogger.append("[RestoreDefaults] Full restore sequence completed.", is_internal=True)

    def shutdown(self):
        """
        Called when the application is closing.
        Saves any final UI state into QSettings.
        """
        GlobalLogger.append("[SettingsPage] Shutdown: saving current UI settings to INI.", is_internal=True)
        self.settings_handler.setValue("run_on_startup", self.startup_chk.isChecked())
        self.settings_handler.setValue("run_as_admin", self.admin_chk.isChecked())
        self.settings_handler.setValue("auto_optimize_on_launch", self.autoopt_chk.isChecked())
        self.settings_handler.sync()
        status = self.settings_handler.status()
        if status != QSettings.Status.NoError:
            GlobalLogger.append(f"ERROR: QSettings status on shutdown sync: {status}", is_error=True)
        else:
            GlobalLogger.append(f"[SettingsPage] Settings saved on shutdown. Path: {self.settings_handler.fileName()}", is_internal=True)
        GlobalLogger.append("[SettingsPage] Shutdown complete.", is_internal=True)


# For standalone testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SettingsPage()
    window.show()
    sys.exit(app.exec())

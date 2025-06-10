# roblox_tweaks_ui.py

import subprocess
import os
import sys

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QFrame,
    QSizePolicy,
    QHBoxLayout,
    QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from visual_tweaks_and_logs import GlobalLogger
from utils.path_utils import resource_path  # For bundling the FPS Unlocker executable

# On Windows, hide console windows when starting subprocesses
if sys.platform.startswith("win"):
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0


class RobloxTweaksPage(QWidget):
    """
    “Roblox Tweaks” page (dark theme):
      - Page title: “Roblox Tweaks”
      - FPS Unlocker card (white background frame on dark page)
      - Read-only log box (100px tall)
      - “Unlock Roblox FPS” (green) and “Stop FPS Unlocker” (red) buttons
      - “More tweaks coming soon!” label beneath (italic, gray)
      - All existing logic and logging preserved
    """

    def __init__(self, main_window_instance=None):
        super().__init__()
        self.main_window = main_window_instance
        GlobalLogger.append("[RobloxTweaksPage] Initializing.", is_internal=True)

        # ─── Overall Page Styling ─────────────────────────────────────────────────
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E2F;  /* Dark background */
                font-family: "Segoe UI", sans-serif;
            }
            QLabel#pageTitle {
                font-size: 24px;
                font-weight: bold;
                color: #FFFFFF;
                margin-bottom: 15px;
            }
            QLabel#sectionTitle {
                font-size: 18px;
                font-weight: 600;
                color: #CFCFDF;
                margin-bottom: 12px;
            }
            QLabel#comingSoonLabel {
                font-size: 16px;
                font-style: italic;
                color: #AAAAAA;
                margin-top: 20px;
            }
            QTextEdit#logBox {
                background-color: #2A2A3E;
                color: #EEEEEE;
                border: 1px solid #44444F;
                border-radius: 5px;
                font-family: Consolas, monospace;
                font-size: 13px;
            }
            QFrame#contentFrame {
                background-color: #2A2A3E;
                border: 1px solid #44444F;
                border-radius: 8px;
            }
            QPushButton {
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: 500;
                min-width: 180px;
                color: #FFFFFF;
            }
            QPushButton#unlockBtn {
                background-color: #28A745;
                border: 1px solid #1E7E34;
            }
            QPushButton#unlockBtn:hover {
                background-color: #218838;
            }
            QPushButton#unlockBtn:pressed {
                background-color: #1E7E34;
            }
            QPushButton#stopBtn {
                background-color: #DC3545;
                border: 1px solid #C82333;
            }
            QPushButton#stopBtn:hover {
                background-color: #C82333;
            }
            QPushButton#stopBtn:pressed {
                background-color: #A71D2A;
            }
        """)

        # ─── Main Layout ─────────────────────────────────────────────────────────────
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(20)

        # Page Title
        page_title = QLabel("Roblox Tweaks")
        page_title.setObjectName("pageTitle")
        main_layout.addWidget(page_title, alignment=Qt.AlignLeft)

        # ─── FPS Unlocker Card ───────────────────────────────────────────────────────
        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 15, 20, 20)
        content_layout.setSpacing(15)

        # Section Title
        section_title = QLabel("FPS Unlocker")
        section_title.setObjectName("sectionTitle")
        content_layout.addWidget(section_title, alignment=Qt.AlignLeft)

        # Log Box (read-only)
        self.log_box = QTextEdit()
        self.log_box.setObjectName("logBox")
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(100)
        content_layout.addWidget(self.log_box)

        # Buttons (side by side)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)

        self.unlock_btn = QPushButton("Unlock Roblox FPS")
        self.unlock_btn.setObjectName("unlockBtn")
        self.unlock_btn.setToolTip("Launches the Roblox FPS Unlocker utility.")
        self.unlock_btn.clicked.connect(self.launch_fps_unlocker_action)
        buttons_layout.addWidget(self.unlock_btn)

        self.stop_btn = QPushButton("Stop FPS Unlocker")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setToolTip("Terminates any running instances of the FPS Unlocker.")
        self.stop_btn.clicked.connect(self.terminate_fps_unlocker_action)
        buttons_layout.addWidget(self.stop_btn)

        buttons_layout.addStretch()
        content_layout.addLayout(buttons_layout)

        main_layout.addWidget(content_frame)

        # “More tweaks coming soon!” Label
        coming_soon_label = QLabel("More tweaks coming soon!")
        coming_soon_label.setObjectName("comingSoonLabel")
        coming_soon_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(coming_soon_label)

        main_layout.addStretch(1)
        self.setLayout(main_layout)
        GlobalLogger.append("[RobloxTweaksPage] Initialization complete.", is_internal=True)

    def launch_fps_unlocker_action(self):
        GlobalLogger.append("[RobloxTweaksPage] 'Unlock Roblox FPS' button clicked.")

        # Determine the bundled executable path via resource_path
        relative_exe_path = os.path.join("resources", "rbxfpsunlocker", "rbxfpsunlocker.exe")
        exe_abs_path = resource_path(relative_exe_path)
        GlobalLogger.append(f"[RobloxTweaksPage] Resolved FPS Unlocker path: {exe_abs_path}")

        if exe_abs_path and os.path.isfile(exe_abs_path):
            try:
                # Launch the FPS Unlocker silently (Windows only)
                subprocess.Popen(
                    [exe_abs_path],
                    creationflags=CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
                )
                success_msg = "[+] FPS Unlocker started successfully."
                GlobalLogger.append(f"[RobloxTweaksPage] {success_msg}")
                self.log_box.append(success_msg)
            except Exception as ex:
                err_msg = f"[-] Failed to launch FPS Unlocker: {ex}"
                GlobalLogger.append(f"[RobloxTweaksPage] {err_msg}", is_error=True)
                self.log_box.append(err_msg)
                QMessageBox.critical(
                    self,
                    "Launch Error",
                    f"Could not start FPS Unlocker.\nPath: {exe_abs_path}\nError: {ex}"
                )
        else:
            not_found_msg = (
                f"[-] FPS Unlocker executable NOT FOUND.\n"
                f"Expected at (resolved): {exe_abs_path}\n"
                f"Relative path: {relative_exe_path}\n"
                f"Ensure it's included in 'resources/rbxfpsunlocker/'."
            )
            GlobalLogger.append(f"[RobloxTweaksPage] {not_found_msg}", is_error=True)
            self.log_box.append(not_found_msg)
            QMessageBox.warning(
                self,
                "File Not Found",
                not_found_msg
            )

    def terminate_fps_unlocker_action(self):
        GlobalLogger.append("[RobloxTweaksPage] 'Stop FPS Unlocker' button clicked.")

        process_name = "rbxfpsunlocker.exe"
        if not sys.platform.startswith("win"):
            msg = "[-] Stopping FPS Unlocker by process name is supported only on Windows."
            GlobalLogger.append(f"[RobloxTweaksPage] {msg}", is_error=True)
            self.log_box.append(msg)
            QMessageBox.information(
                self,
                "Platform Support",
                "Terminating by process name is implemented on Windows only."
            )
            return

        try:
            # Use taskkill on Windows to stop the process
            result = subprocess.run(
                ["taskkill", "/F", "/IM", process_name],
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                check=False
            )

            if result.returncode == 0:
                success_msg = f"[+] FPS Unlocker ({process_name}) terminated successfully."
                GlobalLogger.append(f"[RobloxTweaksPage] {success_msg}")
                self.log_box.append(success_msg)
            elif result.returncode == 128 or "not found" in result.stdout.lower() or "not found" in result.stderr.lower():
                not_running_msg = f"[*] FPS Unlocker ({process_name}) was not found running."
                GlobalLogger.append(f"[RobloxTweaksPage] {not_running_msg}", is_internal=True)
                self.log_box.append(not_running_msg)
            else:
                err_details = result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
                err_msg = f"[-] Failed to stop FPS Unlocker. Details: {err_details}"
                GlobalLogger.append(f"[RobloxTweaksPage] {err_msg}", is_error=True)
                self.log_box.append(err_msg)
                QMessageBox.warning(
                    self,
                    "Termination Error",
                    f"Could not stop {process_name}.\nDetails: {err_details}"
                )
        except FileNotFoundError:
            critical_err_msg = "[-] 'taskkill' command not found on this system."
            GlobalLogger.append(f"[RobloxTweaksPage] {critical_err_msg}", is_error=True)
            self.log_box.append(critical_err_msg)
            QMessageBox.critical(
                self,
                "System Error",
                critical_err_msg
            )
        except Exception as ex:
            unexpected_err_msg = f"[-] Unexpected error while stopping FPS Unlocker: {ex}"
            GlobalLogger.append(f"[RobloxTweaksPage] {unexpected_err_msg}", is_error=True)
            self.log_box.append(unexpected_err_msg)
            QMessageBox.critical(
                self,
                "Unexpected Error",
                unexpected_err_msg
            )

    def shutdown(self):
        GlobalLogger.append("[RobloxTweaksPage] Shutdown.", is_internal=True)
        # No cleanup needed, since FPS Unlocker runs as a detached process

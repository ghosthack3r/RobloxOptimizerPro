# launcher_script.py

import os
import sys
import platform
import ctypes
import time

from PySide6.QtGui import QIcon, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QListWidget,
    QWidget, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt, QSettings

# If running as a bundled executable, ensure the "utils" folder is on sys.path
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    if current_script_dir not in sys.path:
        sys.path.insert(0, current_script_dir)

# Try importing resource_path and app_data_path (for locating settings/logs)
try:
    from utils.path_utils import resource_path, app_data_path
except ImportError as e:
    print(f"Failed to import path_utils: {e}")
    raise

# Import the updated DashboardUI instead of DashboardPage
from dashboard_ui import DashboardUI
from roblox_tweaks_ui import RobloxTweaksPage      # Renamed from FPSUnlockerPage if applicable
from process_manager_ui import ProcessManagerPage   # "Memory Cleaner" page
from os_tweaks_ui import OSTweaksPage
from tcp_optimizer_ui import TCPOptimizerPage       # "TCP Optimizer" (formerly NetworkOptimizerPage)
from network_tests_ui import NetworkTestsPage
from overlay_customizer_ui import OverlayCustomizerPage
from settings_ui import SettingsPage                # Settings & Logs

# Import your logger
from visual_tweaks_and_logs import GlobalLogger

# ────────────── Application Paths ──────────────
APPLICATION_ROOT_PATH = app_data_path()
SETTINGS_FILE = os.path.join(APPLICATION_ROOT_PATH, 'settings.ini')

# Path to your application icon
APP_ICON_PATH = resource_path(os.path.join('resources', 'icon.ico'))

# Initialize GlobalLogger (it should manage its own log file location via app_data_path internally)
GlobalLogger.append(f"Application Root Path: {APPLICATION_ROOT_PATH}", is_internal=True)
GlobalLogger.append(f"Settings File Path: {SETTINGS_FILE}", is_internal=True)
GlobalLogger.append(f"App Icon Path: {APP_ICON_PATH}", is_internal=True)
GlobalLogger.append(f"Logger using path: {GlobalLogger.log_file}", is_internal=True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        GlobalLogger.append("MainWindow initializing...", is_internal=True)

        self.setWindowTitle("Roblox Optimizer Pro")
        if APP_ICON_PATH and os.path.exists(APP_ICON_PATH):
            self.setWindowIcon(QIcon(APP_ICON_PATH))
        else:
            GlobalLogger.append(f"Application icon not found at {APP_ICON_PATH}", is_error=True, is_internal=True)

        # Resize main window
        self.resize(1000, 700)

        # Ensure the directory for settings exists
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)

        # Initialize QSettings
        self.app_settings = QSettings(SETTINGS_FILE, QSettings.Format.IniFormat)

        # Force creation of settings.ini if it does not exist
        if not os.path.exists(SETTINGS_FILE):
            self.app_settings.setValue("Initialization/Timestamp", time.time())
            self.app_settings.sync()

        # ─── Sidebar Configuration ────────────────────
        self.sidebar = QListWidget()
        # Each tuple: (DisplayName, IconEmoji, PageClass, needs_main_window_arg)
        self.sidebar_config = [
            ("Dashboard", "📊", DashboardUI, False),
            ("Roblox Tweaks", "🚀", RobloxTweaksPage, False),
            ("Memory Cleaner", "⚙️", ProcessManagerPage, False),
            ("OS Tweaks", "🔧", OSTweaksPage, False),
            ("TCP Optimizer", "🌐", TCPOptimizerPage, False),
            ("Network Tests", "📈", NetworkTestsPage, False),
            ("Overlay Customizer", "🎨", OverlayCustomizerPage, True),
            ("Settings & Logs", "🛠️", SettingsPage, True),
        ]
        self.page_instances = {}

        # Populate sidebar items
        for display_name, icon_emoji, _, _ in self.sidebar_config:
            self.sidebar.addItem(f"{icon_emoji}  {display_name}")

        # Sidebar styling (modern dark look)
        self.sidebar.setFixedWidth(230)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #1A1A28;
                color: #CFCFDF;
                font-size: 16px;
                border: none;
                padding-top: 10px;
                padding-bottom: 10px;
            }
            QListWidget::item {
                padding: 12px 20px;
                border-radius: 5px;
                margin: 3px 10px;
            }
            QListWidget::item:hover {
                background-color: #2A2A3E;
                color: #FFFFFF;
            }
            QListWidget::item:selected {
                background-color: #3C7AEB;
                color: #FFFFFF;
                font-weight: bold;
            }
        """)
        self.sidebar.currentRowChanged.connect(self.display_page_by_index)

        # ─── Create and Populate a QStackedWidget ─────────────────────────────
        self.pages_widget = QStackedWidget()
        for display_name, _, PageClass, needs_main in self.sidebar_config:
            try:
                page_args = (self,) if needs_main else ()
                page_instance = PageClass(*page_args)
            except TypeError as e_page:
                msg = (
                    f"Failed to instantiate page '{PageClass.__name__}' "
                    f"with args {('MainWindow',) if needs_main else '()'}: {e_page}"
                )
                GlobalLogger.append(msg, is_error=True, is_internal=True)
                QMessageBox.critical(None, "Startup Error", msg)
                sys.exit(1)

            self.pages_widget.addWidget(page_instance)
            self.page_instances[display_name] = page_instance

        # ─── Assemble the Main Layout ────────────────────
        central_container = QWidget()
        main_layout = QHBoxLayout(central_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.pages_widget)
        self.setCentralWidget(central_container)

        # Start on the "Dashboard" tab
        self.sidebar.setCurrentRow(0)

        GlobalLogger.append("MainWindow initialized successfully.", is_internal=True)

    def display_page_by_index(self, index: int):
        """
        Show the selected page in the QStackedWidget, update window title,
        and call page_activated/page_deactivated if available.
        """
        if 0 <= index < len(self.sidebar_config):
            display_name, _, _, _ = self.sidebar_config[index]
            page_widget = self.page_instances.get(display_name)
            if page_widget:
                self.pages_widget.setCurrentWidget(page_widget)
                self.setWindowTitle(f"{display_name}  -  Roblox Optimizer Pro")
                GlobalLogger.append(f"Switched to page: {display_name}", is_internal=True)

                # Call page_activated() if defined
                if hasattr(page_widget, "page_activated") and callable(page_widget.page_activated):
                    try:
                        page_widget.page_activated()
                    except Exception as e_act:
                        GlobalLogger.append(
                            f"Error in page_activated() for {display_name}: {e_act}",
                            is_error=True, is_internal=True
                        )

                # Call page_deactivated() on all other pages
                for other_name, other_widget in self.page_instances.items():
                    if other_name != display_name:
                        if hasattr(other_widget, "page_deactivated") and callable(other_widget.page_deactivated):
                            try:
                                other_widget.page_deactivated()
                            except Exception as e_deact:
                                GlobalLogger.append(
                                    f"Error in page_deactivated() for {other_name}: {e_deact}",
                                    is_error=True, is_internal=True
                                )
            else:
                GlobalLogger.append(f"Page instance for '{display_name}' not found.", is_error=True, is_internal=True)
        else:
            GlobalLogger.append(f"Invalid sidebar index {index} selected.", is_error=True, is_internal=True)

    def closeEvent(self, event):
        """
        On application close, call shutdown() on all pages that implement it,
        sync QSettings, and write final logs.
        """
        GlobalLogger.append("MainWindow received closeEvent, starting shutdown sequence...", is_internal=True)
        for name, page_widget in self.page_instances.items():
            if hasattr(page_widget, "shutdown") and callable(page_widget.shutdown):
                try:
                    GlobalLogger.append(f"Shutting down page: {name}", is_internal=True)
                    page_widget.shutdown()
                except Exception as e_page:
                    GlobalLogger.append(
                        f"Error shutting down page {name}: {e_page}",
                        is_error=True, is_internal=True
                    )

        # Sync settings
        self.app_settings.sync()
        status = self.app_settings.status()
        if status != QSettings.Status.NoError:
            GlobalLogger.append(f"QSettings sync error on close: {status}", is_error=True, is_internal=True)
        else:
            GlobalLogger.append("QSettings sync successful on close.", is_internal=True)

        GlobalLogger.append("MainWindow shutdown complete. Exiting application.\n\n", is_internal=True)
        event.accept()


def run_app():
    """
    Initialize QApplication and launch MainWindow.
    """
    from PySide6.QtGui import QFont, QFontDatabase
    app = QApplication(sys.argv)

    # Load and set Audiowide as the default font
    font_path = os.path.join("resources", "fonts", "Audiowide", "Audiowide-Regular.ttf")
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            app.setFont(QFont(font_family, 12))
        else:
            app.setFont(QFont("Segoe UI", 12))
    else:
        app.setFont(QFont("Segoe UI", 12))

    # High-DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Set application name/organization for QSettings
    QApplication.setOrganizationName("RobloxOptimizerProOrg")
    QApplication.setApplicationName("RobloxOptimizerPro")

    # Set global icon (in case any dialogs or messages appear before MainWindow)
    if APP_ICON_PATH and os.path.exists(APP_ICON_PATH):
        app.setWindowIcon(QIcon(APP_ICON_PATH))

    # Create and show the main window
    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    # Before constructing MainWindow, check if we need to auto-elevate to admin
    temp_settings = QSettings(SETTINGS_FILE, QSettings.Format.IniFormat)
    run_as_admin_val = temp_settings.value("run_as_admin")
    if run_as_admin_val is None:
        run_as_admin_val = temp_settings.value("general/run_as_admin", True)

    always_run_as_admin = str(run_as_admin_val).lower() == 'true'
    is_admin = False
    try:
        if platform.system() == "Windows":
            is_admin = (ctypes.windll.shell32.IsUserAnAdmin() != 0)
        else:
            is_admin = (os.getuid() == 0)
    except Exception as e_admin:
        GlobalLogger.append(f"Could not determine admin status: {e_admin}", is_error=True, is_internal=True)

    GlobalLogger.append(f"Admin status: {'Admin' if is_admin else 'User'}; run_as_admin={always_run_as_admin}", is_internal=True)

    # If on Windows and we need to be admin but aren't, re-launch as admin
    if platform.system() == "Windows" and always_run_as_admin and not is_admin:
        GlobalLogger.append("Attempting Windows elevation to admin...", is_internal=True)
        try:
            # If frozen, re-launch the .exe; otherwise, launch Python with this script
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                params = ' '.join(sys.argv[1:])
            else:
                exe_path = sys.executable
                params = f'"{os.path.abspath(__file__)}" {" ".join(sys.argv[1:])}'

            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, params, None, 1)
            if ret <= 32:
                errmsg = f"Elevation failed (Error code {ret}). Please run as Administrator."
                GlobalLogger.append(errmsg, is_error=True, is_internal=True)
                ctypes.windll.user32.MessageBoxW(None, errmsg.encode('utf-16-le'),
                                                 "Admin Elevation Error".encode('utf-16-le'), 0x10)
                sys.exit(1)
            sys.exit(0)
        except Exception as e_elev:
            errmsg = f"Error relaunching as admin: {e_elev}"
            GlobalLogger.append(errmsg, is_error=True, is_internal=True)
            ctypes.windll.user32.MessageBoxW(None, errmsg.encode('utf-16-le'),
                                             "Elevation Error".encode('utf-16-le'), 0x10)
            sys.exit(1)

    # If we reach here and Windows + run_as_admin is true but not admin, warn
    if platform.system() == "Windows" and always_run_as_admin and not is_admin:
        warning = ("Warning: Not running as Administrator; some features may not work.")
        GlobalLogger.append(warning, is_error=True, is_internal=True)
        ctypes.windll.user32.MessageBoxW(None, warning.encode('utf-16-le'),
                                         "Privilege Warning".encode('utf-16-le'), 0x30)

    run_app()

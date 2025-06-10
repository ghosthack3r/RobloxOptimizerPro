# process_manager_ui.py

import psutil
import time
import os
import sys
import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QCheckBox, QTextEdit, QHBoxLayout,
    QComboBox, QMessageBox, QApplication, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QAction, QFontDatabase

from visual_tweaks_and_logs import GlobalLogger

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

# NAME_DESC_MAP: ensure your full map from the original file is included here.
NAME_DESC_MAP = {
    "python.exe": "Python interpreter running a script or application.",
    "python3.11.exe": "Python 3.11 interpreter running a script or application.",
    "chrome.exe": "Google Chrome Browser",
    "systemsettings.exe": "Windows Settings app for configuring system preferences.",
    "srvirtualdisplay.exe": "ASUS utility for virtual display or screen-sharing functionality.",
    "conhost.exe": "Windows Console Host for command-line interface applications.",
    "cursor.exe": "Cursor AI code editor for coding and development tasks.",
    "helperservice.exe": "Background service for system utilities or software support.",
    "asuscertservice.exe": "ASUS service for handling system certifications or driver updates.",
    "asusoptimizationstartuptask.exe": "ASUS utility for optimizing system startup performance.",
    "adobeupdateservice.exe": "Adobe service for managing software updates.",
    "applemobiledeviceservice.exe": "Apple service for syncing mobile devices with iTunes.",
    "asusswitch.exe": "ASUS utility for switching system modes or configurations.",
    "asussoftwaremanager.exe": "ASUS tool for managing software updates and installations.",
    "asusdiagnosisservice.exe": "ASUS utility for system diagnostics and health monitoring.",
    "mdnsresponder.exe": "Bonjour service for network device discovery.",
    "asusanalysisservice.exe": "ASUS tool for analyzing system performance and resources.",
    "gamesdk.exe": "Gaming-related service for SDK functionality.",
    "httpd.exe": "Apache HTTP server for hosting web services.",
    "oneapp.igcc.winservice.exe": "Intel Graphics Command Center service for GPU management.",
    "glidexservice.exe": "ASUS GlideX service for screen mirroring and extension.",
    "glidexserviceext.exe": "Extended service for ASUS GlideX screen-sharing features.",
    "glidexremoteservice.exe": "ASUS GlideX service for remote screen-sharing functionality.",
    "glidexnearservice.exe": "ASUS GlideX service for local device screen sharing.",
    "officeclicktorun.exe": "Microsoft Office Click-to-Run service for streaming Office apps.",
    "licenseservice.exe": "Service for managing software licenses.",
    "mydock.exe": "ASUS MyDock utility for managing application shortcuts.",
    "rogliveservice.exe": "ASUS ROG Live service for gaming performance monitoring.",
    "restservice.exe": "Background service for REST API functionality.",
    "thunderboltservice.exe": "Intel Thunderbolt service for managing Thunderbolt devices.",
    "rtkauduservice64.exe": "Realtek Audio Universal Service for audio driver management.",
    "tbtp2pshortcutservice.exe": "Thunderbolt peer-to-peer shortcut service.",
    "schedulerservice.exe": "Service for scheduling tasks or updates.",
    "agentservice.exe": "Background agent for software or system management.",
    "lghub_updater.exe": "Logitech G HUB updater for peripheral software.",
    "lightingservice.exe": "ASUS Aura service for controlling RGB lighting.",
    "ipf_uf.exe": "Intel Processor Frequency utility for CPU management.",
    "acpowernotification.exe": "ASUS utility for power status notifications.",
    "gamingservices.exe": "Microsoft Gaming Services for Xbox app functionality.",
    "coordservice.exe": "Service for coordinating system or application tasks.",
    "buildservice.exe": "Service for managing software builds or updates.",
    "intel_pie_service.exe": "Intel service for performance or system management.",
    "dllhost.exe": "Windows process for hosting DLL-based applications.",
    "unsecapp.exe": "Windows WMI provider for application communication.",
    "aacambientkeyscanner.exe": "ASUS utility for ambient keyboard scanning.",
    "asus_wdl_helper.exe": "ASUS utility for supporting wireless display functionality.",
    "wmiregistrationservice.exe": "Windows WMI service for system management.",
    "cursor.exe": "Cursor AI code editor for coding and development tasks.",
    "asusservice.exe": "ASUS service process.",
    "epicgameslauncher.exe": "Epic Games Launcher for managing games.",
    "whatsapp.exe": "WhatsApp desktop application for messaging.",
    "signal.exe": "Signal desktop application for secure messaging.",
    "igcc.exe": "Intel Graphics Command Center for GPU settings.",
    "searchhost.exe": "Windows Search service for indexing and searching files.",
    "searchprotocolhost.exe": "Windows Search protocol host for indexing.",
    "widgets.exe": "Windows Widgets application for desktop widgets.",
    "useroobebroker.exe": "Windows Out-of-Box Experience broker for user setup.",
    "asusarmourycrate.exe": "ASUS Armoury Crate for managing gaming hardware.",
    "shellexperiencehost.exe": "Windows process for rendering the shell UI.",
    "acrobatnotificationclient.exe": "Adobe Acrobat notification service.",
    "xboxpcappft.exe": "Xbox PC app component for gaming features.",
    "notepad.exe": "Notepad text editor."
}

# SYSTEM CRITICAL PROCESSES (all lowercase names)
CRITICAL_PROCESSES = {
    "system idle process", "system", "smss.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "lsass.exe", "services.exe", "svchost.exe", "registry",
    "fontdrvhost.exe", "dwm.exe", "explorer.exe", "sihost.exe", "ctfmon.exe",
    "taskhostw.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe",
    "searchhost.exe", "runtimebroker.exe", "applicationframehost.exe",
    "wudfhost.exe", "dllhost.exe", "conhost.exe", "unsecapp.exe",
    "wmiprvse.exe", "spoolsv.exe", "audiodg.exe",
    # Security software
    "msmpeng.exe", "nissrv.exe", "securityhealthservice.exe",
    "securityhealthsystray.exe", "mpdefendercoreservice.exe", "mpcmdrun.exe",
    # Hardware drivers/services
    "rtkauduservice64.exe", "igfxcuiservice.exe", "igfxem.exe", "igcctray.exe",
    "nvcontainer.exe", "nvidia web helper.exe", "nvdisplay.container.exe",
    "oneapp.igcc.winservice.exe", "igcc.exe",
    "thunderboltservice.exe", "tbtp2pshortcutservice.exe",
    # Virtualization
    "vmms.exe", "vmmem", "vmmemws", "vmcompute.exe", "vmwp.exe", "wslservice.exe", "vmmemcmzygote",
    # Common utilities
    "powershell.exe", "cmd.exe", "windowsterminal.exe", "openconsole.exe",
    "textinputhost.exe", "lockapp.exe", "widgets.exe", "dashost.exe",
    # ASUS-specific
    "asusystemanalysis.exe", "asusdiagnosisservice.exe", "armourycrateservice.exe",
    # Additional
    "lsaiso.exe", "memcompression", "wlanext.exe",
    "searchindexer.exe", "aggregatorhost.exe", "ngciso.exe",
    "mousocoreworker.exe", "useroobebroker.exe",
    "systemsettings.exe", "wmiregistrationservice.exe", "backgroundtaskhost.exe",
    "crossdeviceresume.exe", "crossdeviceservice.exe", "rundll32.exe",
    "srvirtualdisplay.exe", "srserver.exe", "srapppb.exe", "dataexchangehost.exe",
    "secd.exe", "wmiapsrv.exe", "ipf_uf.exe", "temperature.exe",
    "RobloxStudio.exe", "RobloxStudioBeta.exe", "RobloxPlayer.exe", "RobloxPlayerBeta.exe",
    "rbxfpsunlocker.exe", "rbxfpsunlocker_x64.exe", "rbxfpsunlocker_x86.exe",
    "rbxfpsunlocker_x64_d3d11.exe", "rbxfpsunlocker_x64_d3d12.exe", "rbxfpsunlocker_x86_d3d11.exe",
    "rbxfpsunlocker_x86_d3d12.exe", "rbxfpsunlocker_dx11.exe", "rbxfpsunlocker_dx12.exe",
    "RobloxOptimizer.exe", "RobloxOptimizerPro.exe", "RobloxOptimizerPro_x64.exe",
    "RobloxOptimizerPro_x86.exe", "RobloxOptimizerPro_x64_d3d11.exe", "RobloxOptimizerPro_x64_d3d12.exe",
    "RobloxOptimizerPro_x86_d3d11.exe", "RobloxOptimizerPro_x86_d3d12.exe", "RobloxOptimizerPro_dx11.exe",
    "RobloxOptimizerPro_dx12.exe",
    # (Optionally include your app's executable name if critical)
}

class ProcWorker(QThread):
    update_signal = Signal(list)  # Emits list of process dicts

    def __init__(self, sort_mode="MEM", parent=None):
        super().__init__(parent)
        self.sort_mode = sort_mode
        self.running = True
        GlobalLogger.append(f"[MemoryCleanerWorker] Initialized with sort_mode={sort_mode}", is_internal=True)

    def run(self):
        GlobalLogger.append("[MemoryCleanerWorker] Thread started.", is_internal=True)
        while self.running:
            procs_list = []
            for p in psutil.process_iter(['pid', 'name', 'username', 'memory_info', 'cpu_percent', 'exe', 'status']):
                if not self.running:
                    break
                try:
                    info = p.info
                    pid = info['pid']
                    name = info['name'] or ""
                    exe_path = info['exe'] or ""
                    status = info['status'] or ""
                    user = info['username'] or "N/A"
                    mem_mb = info['memory_info'].rss / (1024 * 1024)

                    if not name or not exe_path or pid in (0, 4) or status == psutil.STATUS_ZOMBIE:
                        continue

                    name_lower = name.lower()
                    exe_lower = os.path.basename(exe_path).lower()

                    # Skip critical processes
                    if (
                        name_lower in CRITICAL_PROCESSES
                        or exe_lower in CRITICAL_PROCESSES
                        or (
                            info['username'] and "system" in info['username'].lower()
                            and info['memory_info'].rss < 5 * 1024 * 1024
                        )
                    ):
                        continue

                    # Use the CPU percent directly
                    cpu_percent = p.cpu_percent(interval=None)
                    if mem_mb < 0.5 and cpu_percent < 0.1:
                        continue

                    desc = NAME_DESC_MAP.get(name_lower, NAME_DESC_MAP.get(exe_lower, "No description available."))

                    procs_list.append({
                        'pid': pid,
                        'name': name,
                        'cpu': cpu_percent,
                        'mem': mem_mb,
                        'user': user,
                        'status': status,
                        'desc': desc
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                except Exception as e:
                    GlobalLogger.append(f"[MemoryCleanerWorker] Error iterating PID {getattr(p, 'pid', 'N/A')}: {e}", is_error=True)
                    continue

            if not self.running:
                break

            # Sort
            if self.sort_mode == "CPU":
                procs_list.sort(key=lambda x: x['cpu'], reverse=True)
            else:
                procs_list.sort(key=lambda x: x['mem'], reverse=True)

            if self.running:
                self.update_signal.emit(procs_list)

            time.sleep(2.0)

        GlobalLogger.append("[MemoryCleanerWorker] Thread stopped.", is_internal=True)

    def stop(self):
        self.running = False
        GlobalLogger.append("[MemoryCleanerWorker] Stop requested.", is_internal=True)


class ProcessManagerPage(QWidget):
    """
    Modern dark-themed "Memory Cleaner" page:
      - Lists processes (filtered out critical)
      - Sort by Memory or CPU
      - Select checkboxes to kill processes
      - Context menu to copy PID/Name or kill a single process
      - Save current list to JSON
      - Auto-terminate non-critical (disable_non_critical), used by Dashboard
      - Logs all actions to both on-page log and GlobalLogger
    """

    def __init__(self, main_window_instance=None):
        super().__init__()
        self.main_window = main_window_instance
        GlobalLogger.append("[MemoryCleanerPage] Initializing.", is_internal=True)

        # Will store latest processes data for saving
        self.last_processes_data = []

        # Dark theme for the page
        self.setStyleSheet("""
            QWidget { background-color: #1E1E2F; color: #E0E0E0; font-family: "Segoe UI", sans-serif; }
            QLabel { color: #E0E0E0; }
            QPushButton {
                font-size: 14px; color: #FFFFFF; border-radius: 5px; padding: 8px 12px; min-height: 36px; font-weight: 500;
            }
            QPushButton#selectAllBtn { background-color: #5E5EFF; }
            QPushButton#selectAllBtn:hover { background-color: #4A4AFF; }
            QPushButton#killBtn { background-color: #FF5E5E; }
            QPushButton#killBtn:hover { background-color: #E04A4A; }
            QPushButton#saveBtn { background-color: #17A2B8; }
            QPushButton#saveBtn:hover { background-color: #117A8B; }
            QComboBox {
                font-size: 14px; padding: 6px; border: 1px solid #44444F; border-radius: 4px;
                background-color: #2A2A3E; color: #E0E0E0;
            }
            QTableWidget {
                background-color: #2A2A3E; color: #E0E0E0; gridline-color: #44444F;
                font-size: 13px; border: none;
            }
            QHeaderView::section {
                background-color: #3A3A3A; color: #FFFFFF; padding: 4px; font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #4A4AFF; color: #FFFFFF;
            }
            QCheckBox { color: #E0E0E0; }
            QTextEdit#logArea {
                background-color: #2A2A3E; border: 1px solid #44444F; color: #E0E0E0;
                font-family: Consolas, monospace; font-size: 12px; padding: 6px;
            }
            QMenu { background-color: #2A2A3E; color: #E0E0E0; }
            QMenu::item:selected { background-color: #4A4AFF; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Memory Cleaner")
        title.setFont(QFont("Segoe UI", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Sort mode controls
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Sort By:")
        mode_label.setFont(QFont("Segoe UI", 12))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Memory Usage", "CPU Usage"])
        self.mode_combo.setCurrentText("Memory Usage")
        self.mode_combo.currentTextChanged.connect(self.change_sort_mode)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Table: Kill?, PID, Name, CPU, Memory, User, Status
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Kill?", "PID", "Name", "CPU (%)", "Memory (MB)", "User", "Status"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_table_context_menu)
        layout.addWidget(self.table)

        # Buttons: Select/Deselect All, Kill Selected, Save List
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.select_all_btn = QPushButton("Select/Deselect All")
        self.select_all_btn.setObjectName("selectAllBtn")
        self.select_all_btn.clicked.connect(self.toggle_select_all)
        btn_layout.addWidget(self.select_all_btn)

        self.kill_selected_btn = QPushButton("Kill Selected Processes")
        self.kill_selected_btn.setObjectName("killBtn")
        self.kill_selected_btn.clicked.connect(self.kill_selected_processes)
        btn_layout.addWidget(self.kill_selected_btn)

        self.save_file_btn = QPushButton("Save Process List")
        self.save_file_btn.setObjectName("saveBtn")
        self.save_file_btn.clicked.connect(self.save_process_list_to_file)
        btn_layout.addWidget(self.save_file_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Log area
        log_label = QLabel("Action Log:")
        log_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(log_label)
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setObjectName("logArea")
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setFixedHeight(120)
        layout.addWidget(self.log_text_edit)

        # Start worker thread
        self.worker_thread = ProcWorker(sort_mode="MEM", parent=self)
        self.worker_thread.update_signal.connect(self.populate_table_data)
        self.worker_thread.start()

    def open_table_context_menu(self, position):
        """
        Context menu: copy PID/Name or kill single process.
        """
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        pid_item = self.table.item(row, 1)
        name_item = self.table.item(row, 2)
        if not pid_item or not name_item:
            return

        pid_val = pid_item.text()
        name_val = name_item.text()

        menu = QMenu(self)
        copy_pid_action = QAction(f"Copy PID: {pid_val}", self)
        copy_pid_action.triggered.connect(lambda: self.copy_to_clipboard(pid_val, "PID"))
        menu.addAction(copy_pid_action)

        copy_name_action = QAction(f"Copy Name: {name_val}", self)
        copy_name_action.triggered.connect(lambda: self.copy_to_clipboard(name_val, "Name"))
        menu.addAction(copy_name_action)

        menu.addSeparator()

        kill_action = QAction(f"Kill Process: {name_val} (PID: {pid_val})", self)
        kill_action.triggered.connect(lambda: self.kill_single_process_from_menu(int(pid_val), name_val))
        menu.addAction(kill_action)

        menu.exec(self.table.viewport().mapToGlobal(position))

    def copy_to_clipboard(self, text, item_type):
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.log_text_edit.append(f"[*] {item_type} '{text}' copied to clipboard.")
            GlobalLogger.append(f"[MemoryCleanerPage] Copied {item_type} '{text}' to clipboard.")
        except Exception as e:
            self.log_text_edit.append(f"[-] Error copying {item_type} to clipboard: {e}")
            GlobalLogger.append(f"[MemoryCleanerPage] Error copying {item_type} to clipboard: {e}", is_error=True)

    def kill_single_process_from_menu(self, pid, name):
        GlobalLogger.append(f"[MemoryCleanerPage] Kill via menu: {name} (PID: {pid}).", is_internal=True)
        reply = QMessageBox.question(
            self, "Confirm Kill Process",
            f"Terminate process:\n{name} (PID: {pid})?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                p = psutil.Process(pid)
                p.terminate()
                self.log_text_edit.append(f"[*] Terminated PID {pid} ({name}).")
                GlobalLogger.append(f"[MemoryCleanerPage] Terminated PID {pid} ({name}).")
            except psutil.NoSuchProcess:
                self.log_text_edit.append(f"[*] PID {pid} ({name}) no longer exists.")
                GlobalLogger.append(f"[MemoryCleanerPage] PID {pid} ({name}) not found when killing.")
            except psutil.AccessDenied:
                self.log_text_edit.append(f"[-] Access denied for PID {pid} ({name}).")
                GlobalLogger.append(f"[MemoryCleanerPage] Access denied terminating PID {pid} ({name}).", is_error=True)
                QMessageBox.warning(self, "Access Denied", f"Could not terminate {name} (PID: {pid}). Run as admin?")
            except Exception as e:
                self.log_text_edit.append(f"[-] Error terminating PID {pid} ({name}): {e}")
                GlobalLogger.append(f"[MemoryCleanerPage] Error terminating PID {pid} ({name}): {e}", is_error=True)

    def change_sort_mode(self, text):
        mode = "CPU" if text == "CPU Usage" else "MEM"
        if self.worker_thread:
            self.worker_thread.sort_mode = mode
            GlobalLogger.append(f"[MemoryCleanerPage] Sort mode changed to {mode}.", is_internal=True)
            self.log_text_edit.append(f"[*] Sorting by {text}.")

    def populate_table_data(self, processes_data):
        """
        Update table rows with the latest process data and store it for saving.
        """
        # Store latest data
        self.last_processes_data = processes_data.copy()

        # Preserve checked PIDs and selected row indices
        checked_pids = set()
        selected_rows = {idx.row() for idx in self.table.selectedIndexes()}

        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            pid_item = self.table.item(row, 1)
            if widget and pid_item:
                chk = widget.findChild(QCheckBox)
                if chk and chk.isChecked():
                    try:
                        checked_pids.add(int(pid_item.text()))
                    except ValueError:
                        pass

        # Clear table
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        restored_rows = []

        for i, proc in enumerate(processes_data):
            self.table.insertRow(i)

            # Checkbox cell
            chk = QCheckBox()
            if proc['pid'] in checked_pids:
                chk.setChecked(True)
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.addWidget(chk)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(i, 0, container)

            # PID
            pid_item = QTableWidgetItem(str(proc['pid']))
            pid_item.setFlags(pid_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 1, pid_item)

            # Name (with tooltip = description)
            name_item = QTableWidgetItem(proc['name'])
            name_item.setToolTip(proc['desc'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 2, name_item)

            # CPU
            cpu_item = QTableWidgetItem(f"{proc['cpu']:.1f}")
            cpu_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cpu_item.setFlags(cpu_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 3, cpu_item)

            # Memory
            mem_item = QTableWidgetItem(f"{proc['mem']:.2f}")
            mem_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            mem_item.setFlags(mem_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 4, mem_item)

            # User
            user_item = QTableWidgetItem(proc['user'])
            user_item.setFlags(user_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 5, user_item)

            # Status
            status_item = QTableWidgetItem(proc['status'])
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(i, 6, status_item)

            if i in selected_rows:
                restored_rows.append(i)

        # Restore selection
        for row_idx in restored_rows:
            self.table.selectRow(row_idx)

        self.table.setSortingEnabled(True)

    def toggle_select_all(self):
        GlobalLogger.append("[MemoryCleanerPage] Select/Deselect All clicked.", is_internal=True)
        select_all = False
        for row in range(self.table.rowCount()):
            container = self.table.cellWidget(row, 0)
            if container:
                chk = container.findChild(QCheckBox)
                if chk and not chk.isChecked():
                    select_all = True
                    break

        for row in range(self.table.rowCount()):
            container = self.table.cellWidget(row, 0)
            if container:
                chk = container.findChild(QCheckBox)
                if chk:
                    chk.setChecked(select_all)

        self.log_text_edit.append(f"[*] {'Selected' if select_all else 'Deselected'} all processes.")

    def kill_selected_processes(self):
        GlobalLogger.append("[MemoryCleanerPage] Kill Selected Processes clicked.", is_internal=True)
        to_kill = []
        for row in range(self.table.rowCount()):
            container = self.table.cellWidget(row, 0)
            if container:
                chk = container.findChild(QCheckBox)
                if chk and chk.isChecked():
                    try:
                        pid = int(self.table.item(row, 1).text())
                        name = self.table.item(row, 2).text()
                        to_kill.append({'pid': pid, 'name': name})
                    except Exception as e:
                        GlobalLogger.append(f"[MemoryCleanerPage] Error reading row {row}: {e}", is_error=True)

        if not to_kill:
            QMessageBox.information(self, "Kill Processes", "No processes selected.")
            self.log_text_edit.append("[*] No processes selected to terminate.")
            GlobalLogger.append("[MemoryCleanerPage] No selected processes to kill.", is_internal=True)
            return

        sample = ", ".join([p['name'] for p in to_kill[:3]])
        if len(to_kill) > 3:
            sample += "..."

        confirm = QMessageBox.question(
            self, "Confirm Termination",
            f"Terminate {len(to_kill)} process(es)?\nIncluding: {sample}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            self.log_text_edit.append("[*] Termination cancelled by user.")
            GlobalLogger.append("[MemoryCleanerPage] Termination cancelled.", is_internal=True)
            return

        killed, failed, not_found = 0, 0, 0
        for proc in to_kill:
            pid, name = proc['pid'], proc['name']
            try:
                p = psutil.Process(pid)
                p.terminate()
                killed += 1
                self.log_text_edit.append(f"[*] Terminated PID {pid} ({name}).")
                GlobalLogger.append(f"[MemoryCleanerPage] Terminated PID {pid} ({name}).")
            except psutil.NoSuchProcess:
                not_found += 1
                self.log_text_edit.append(f"[*] PID {pid} ({name}) not found.")
                GlobalLogger.append(f"[MemoryCleanerPage] PID {pid} ({name}) not found.", is_internal=True)
            except psutil.AccessDenied:
                failed += 1
                self.log_text_edit.append(f"[-] Access denied for PID {pid} ({name}).")
                GlobalLogger.append(f"[MemoryCleanerPage] Access denied terminating PID {pid} ({name}).", is_error=True)
            except Exception as e:
                failed += 1
                self.log_text_edit.append(f"[-] Error terminating PID {pid} ({name}): {e}")
                GlobalLogger.append(f"[MemoryCleanerPage] Error terminating PID {pid} ({name}): {e}", is_error=True)

        summary = f"[*] Summary – Terminated: {killed}, Failed: {failed}, Not Found: {not_found}."
        self.log_text_edit.append(summary)
        GlobalLogger.append(f"[MemoryCleanerPage] {summary}", is_internal=True)

    def save_process_list_to_file(self):
        """
        Save last_processes_data (not the table) to JSON. Ensures non-blank output.
        """
        GlobalLogger.append("[MemoryCleanerPage] Save Process List clicked.", is_internal=True)
        if not self.last_processes_data:
            QMessageBox.information(self, "Save Process List", "No process data available to save.")
            self.log_text_edit.append("[*] No process data available to save.")
            GlobalLogger.append("[MemoryCleanerPage] Attempted to save with no data.", is_internal=True)
            return

        procs = []
        for proc in self.last_processes_data:
            procs.append({
                "pid": proc['pid'],
                "name": proc['name'],
                "cpu": f"{proc['cpu']:.1f}",
                "mem": f"{proc['mem']:.2f}",
                "user": proc['user'],
                "status": proc['status'],
                "desc": proc['desc']
            })

        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.getcwd()
        file_path = os.path.join(base_dir, "memory_cleaner_process_list.json")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(procs, f, indent=4)
            self.log_text_edit.append(f"[*] Process list saved to: {file_path}")
            GlobalLogger.append(f"[MemoryCleanerPage] Saved process list to {file_path}.")
            QMessageBox.information(self, "Save Successful", f"List saved to:\n{file_path}")
        except Exception as e:
            self.log_text_edit.append(f"[-] Error saving process list: {e}")
            GlobalLogger.append(f"[MemoryCleanerPage] Error saving process list: {e}", is_error=True)
            QMessageBox.critical(self, "Save Error", f"Could not save list:\n{e}")

    def disable_non_critical(self):
        """
        Auto-terminate non-critical processes (called by Dashboard).
        """
        GlobalLogger.append("[MemoryCleanerPage] Auto-terminate non-critical initiated.", is_internal=True)
        self.log_text_edit.append("[*] Auto-terminating non-critical processes...")

        term_count, fail_count = 0, 0
        for row in range(self.table.rowCount()):
            try:
                pid = int(self.table.item(row, 1).text())
                name = self.table.item(row, 2).text()
                p = psutil.Process(pid)
                p.terminate()
                term_count += 1
                self.log_text_edit.append(f"[*] Auto-terminated PID {pid} ({name}).")
                GlobalLogger.append(f"[MemoryCleanerPage] Auto-terminated PID {pid} ({name}).")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                fail_count += 1
            except Exception as e:
                fail_count += 1
                GlobalLogger.append(f"[MemoryCleanerPage] Error auto-terminating PID {pid}: {e}", is_error=True)

        msg = f"[*] Auto-terminate finished. Terminated: {term_count}, Failed/Skipped: {fail_count}."
        self.log_text_edit.append(msg)
        GlobalLogger.append(f"[MemoryCleanerPage] {msg}", is_internal=True)

    def shutdown(self):
        """
        Called on app exit: stop the worker thread cleanly.
        """
        GlobalLogger.append("[MemoryCleanerPage] Shutdown initiated.", is_internal=True)
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.worker_thread.stop()
            if not self.worker_thread.wait(3000):
                GlobalLogger.append("[MemoryCleanerPage] Worker did not stop; force terminating.", is_error=True)
                self.worker_thread.terminate()
                self.worker_thread.wait()
            else:
                GlobalLogger.append("[MemoryCleanerPage] Worker stopped gracefully.", is_internal=True)
        GlobalLogger.append("[MemoryCleanerPage] Shutdown complete.", is_internal=True)


# For standalone testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProcessManagerPage()
    window.show()
    sys.exit(app.exec())







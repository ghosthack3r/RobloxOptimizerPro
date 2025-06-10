# network_tests_ui.py

import subprocess
import json
import os
import platform
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem, QSpinBox,
    QHeaderView, QProgressDialog, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from utils.path_utils import resource_path
from visual_tweaks_and_logs import GlobalLogger

# Path to bundled speedtest.exe
SPEEDTEST_EXE = resource_path("resources/speedtest/speedtest.exe")

# DNS servers
DNS_SERVERS_BASE = {
    "Current DNS": None,
    "Google (8.8.8.8)": "8.8.8.8",
    "Cloudflare (1.1.1.1)": "1.1.1.1",
    "Quad9 (9.9.9.9)": "9.9.9.9",
    "OpenDNS (208.67.222.222)": "208.67.222.222",
}

# Roblox endpoints to ping
ROBLOX_SERVERS = {
    "www.roblox.com": "www.roblox.com",
    "gamejoin.roblox.com": "gamejoin.roblox.com"
}

# Hide console windows on Windows
if sys.platform.startswith("win"):
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0


class PingWorker(QThread):
    """
    Worker thread to do ping tests (for Roblox hosts or DNS servers).
    Emits a dict mapping label -> average-latency string (e.g., '32ms' or 'N/A').
    """
    result_signal = Signal(dict)

    def __init__(self, targets: dict, count: int = 3):
        super().__init__()
        self.targets = targets
        self.count = count

    def run(self):
        results = {}
        for name, addr in self.targets.items():
            current_addr = addr

            # Discover "Current DNS" via ipconfig /all on Windows
            if name == "Current DNS":
                if platform.system().lower().startswith("win"):
                    try:
                        proc = subprocess.Popen(
                            ["ipconfig", "/all"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL,
                            universal_newlines=True,
                            creationflags=CREATE_NO_WINDOW
                        )
                        output, _ = proc.communicate(timeout=10)
                        dns_ip = ""
                        for line in output.splitlines():
                            line = line.strip()
                            if line.lower().startswith("dns servers") and ":" in line:
                                parts = line.split(":", 1)
                                dns_ip = parts[1].strip()
                                break
                        current_addr = dns_ip or ""
                    except Exception:
                        current_addr = ""
                else:
                    current_addr = ""  # Non-Windows: no discovery

            if not current_addr:
                results[name] = "N/A"
                continue

            try:
                # Use '-n' on Windows, '-c' elsewhere
                count_flag = "-n" if platform.system().lower().startswith("win") else "-c"
                proc = subprocess.Popen(
                    ["ping", count_flag, str(self.count), current_addr],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    universal_newlines=True,
                    creationflags=CREATE_NO_WINDOW
                )
                stdout, _ = proc.communicate(timeout=10)
                avg = "N/A"
                for l in stdout.splitlines():
                    if "Average" in l or "avg" in l.lower():
                        # Windows: "Average = XXms"
                        if "Average =" in l:
                            avg = l.split("Average =")[-1].strip()
                        else:
                            # Unix: "rtt min/avg/max/mdev = X/X/X/X ms"
                            parts = l.split("=")[-1].split("/")
                            if len(parts) >= 2:
                                avg = parts[1].strip() + " ms"
                        break
                results[name] = avg
            except Exception:
                results[name] = "N/A"

        self.results = results
        self.result_signal.emit(results)


class SpeedTestWorker(QThread):
    """
    Worker thread to run an Internet speed test by calling bundled speedtest.exe.
    Emits a single string: the raw "--simple" output or error message.
    """
    result_signal = Signal(str)

    def run(self):
        if not SPEEDTEST_EXE or not os.path.exists(SPEEDTEST_EXE):
            msg = (
                "Error: speedtest.exe not found in resources.\n"
                "Copy speedtest.exe from .venv\\Scripts into resources/speedtest/ before building."
            )
            GlobalLogger.append(msg)
            self.result_signal.emit(msg)
            return

        try:
            proc = subprocess.Popen(
                [SPEEDTEST_EXE, "--simple"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=CREATE_NO_WINDOW
            )
            out, err = proc.communicate(timeout=60)
            if out.strip():
                self.result_signal.emit(out.strip())
                GlobalLogger.append(f"Speed Test Results:\n{out.strip()}")
            else:
                msg = err.strip() or "Speedtest returned no output."
                self.result_signal.emit(msg)
                GlobalLogger.append(f"Speed Test Error / no output:\n{msg}")
        except subprocess.TimeoutExpired:
            proc.kill()
            msg = "Error: speedtest.exe timed out."
            self.result_signal.emit(msg)
            GlobalLogger.append(msg)
        except Exception as e:
            msg = f"Error running speedtest.exe: {e}"
            self.result_signal.emit(msg)
            GlobalLogger.append(msg)


class NetworkTestsPage(QWidget):
    """
    “Network Tests” page containing:
      • Roblox Host Ping Test
      • DNS Benchmark
      • Custom Host Traceroute (placeholder)
      • Internet Speed Test (bundled speedtest.exe)
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        self.setLayout(layout)

        # Title
        title = QLabel("Network Tests")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(title)

        # ─── Roblox Host Ping Test ───────────────────────
        ping_section = QFrame()
        ping_layout = QVBoxLayout()
        ping_layout.setSpacing(10)
        ping_section.setLayout(ping_layout)

        ping_label = QLabel("Roblox Services Ping Test:")
        ping_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        ping_label.setStyleSheet("color: #CFCFDF;")
        ping_layout.addWidget(ping_label)

        self.ping_table = QTableWidget(0, 2)
        self.ping_table.setHorizontalHeaderLabels(["Host", "Avg Latency"])
        self.ping_table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A28;
                color: #EEEEEE;
                border: 1px solid #44444F;
                gridline-color: #44444F;
            }
            QHeaderView::section {
                background-color: #2A2A3E;
                color: #FFFFFF;
                padding: 4px;
                font-size: 14px;
            }
        """)
        header_ping = self.ping_table.horizontalHeader()
        header_ping.setSectionResizeMode(0, QHeaderView.Stretch)
        header_ping.setSectionResizeMode(1, QHeaderView.Stretch)
        ping_layout.addWidget(self.ping_table)

        self.run_ping_btn = QPushButton("Run Ping Test")
        self.run_ping_btn.setFixedHeight(35)
        self.run_ping_btn.setStyleSheet("""
            QPushButton {
                background-color: #5E5EFF;
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #4A4AFF;
            }
            QPushButton:pressed {
                background-color: #3A3AE6;
            }
        """)
        self.run_ping_btn.clicked.connect(self.run_ping_test)
        ping_layout.addWidget(self.run_ping_btn)

        layout.addWidget(ping_section)

        # ─── DNS Benchmark ───────────────────────────────
        dns_section = QFrame()
        dns_layout = QVBoxLayout()
        dns_layout.setSpacing(10)
        dns_section.setLayout(dns_layout)

        dns_label = QLabel("DNS Benchmark:")
        dns_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        dns_label.setStyleSheet("color: #CFCFDF;")
        dns_layout.addWidget(dns_label)

        dns_config_hbox = QHBoxLayout()
        dns_config_hbox.setSpacing(10)
        dns_config_hbox.addWidget(QLabel("Pings per DNS server:"))
        self.dns_ping_count_spinbox = QSpinBox()
        self.dns_ping_count_spinbox.setRange(5, 15)
        self.dns_ping_count_spinbox.setValue(8)
        self.dns_ping_count_spinbox.setSuffix(" pings")
        self.dns_ping_count_spinbox.setToolTip(
            "Number of pings to send to each DNS server for averaging."
        )
        dns_config_hbox.addWidget(self.dns_ping_count_spinbox)
        dns_config_hbox.addStretch()
        dns_layout.addLayout(dns_config_hbox)

        self.dns_table = QTableWidget(0, 2)
        self.dns_table.setHorizontalHeaderLabels(["DNS Provider", "Avg Latency"])
        self.dns_table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A28;
                color: #EEEEEE;
                border: 1px solid #44444F;
                gridline-color: #44444F;
            }
            QHeaderView::section {
                background-color: #2A2A3E;
                color: #FFFFFF;
                padding: 4px;
                font-size: 14px;
            }
        """)
        header_dns = self.dns_table.horizontalHeader()
        header_dns.setSectionResizeMode(0, QHeaderView.Stretch)
        header_dns.setSectionResizeMode(1, QHeaderView.Stretch)
        dns_layout.addWidget(self.dns_table)

        dns_btn_layout = QHBoxLayout()
        dns_btn_layout.setSpacing(10)
        self.run_dns_btn = QPushButton("Run DNS Benchmark")
        self.run_dns_btn.setFixedHeight(35)
        self.run_dns_btn.setStyleSheet("""
            QPushButton {
                background-color: #5E5EFF;
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #4A4AFF;
            }
            QPushButton:pressed {
                background-color: #3A3AE6;
            }
        """)
        self.run_dns_btn.clicked.connect(self.run_dns_test)
        dns_btn_layout.addWidget(self.run_dns_btn)

        self.apply_fastest_btn = QPushButton("Apply Fastest DNS")
        self.apply_fastest_btn.setFixedHeight(35)
        self.apply_fastest_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1E7E34;
            }
        """)
        self.apply_fastest_btn.setEnabled(False)
        self.apply_fastest_btn.setToolTip("Run DNS Benchmark to enable")
        self.apply_fastest_btn.clicked.connect(self.apply_fastest_dns)
        dns_btn_layout.addWidget(self.apply_fastest_btn)

        dns_layout.addLayout(dns_btn_layout)

        self.fastest_label = QLabel("Fastest DNS: N/A")
        self.fastest_label.setFont(QFont("Segoe UI", 14))
        self.fastest_label.setStyleSheet("color: #FFFFFF;")
        dns_layout.addWidget(self.fastest_label)

        layout.addWidget(dns_section)

        # ─── Custom Host Traceroute ──────────────────────
        trace_section = QFrame()
        trace_layout = QVBoxLayout()
        trace_layout.setSpacing(10)
        trace_section.setLayout(trace_layout)

        trace_label = QLabel("Custom Host Traceroute (IP or Hostname):")
        trace_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        trace_label.setStyleSheet("color: #CFCFDF;")
        trace_layout.addWidget(trace_label)

        host_layout = QHBoxLayout()
        self.custom_host_input = QLineEdit()
        self.custom_host_input.setPlaceholderText("e.g., www.example.com")
        self.custom_host_input.setFixedWidth(300)
        self.custom_host_input.setStyleSheet("""
            QLineEdit {
                background-color: #1A1A28;
                border: 1px solid #44444F;
                border-radius: 5px;
                padding: 5px 10px;
                color: #EEEEEE;
            }
            QLineEdit:focus {
                border: 1px solid #5E5EFF;
            }
        """)
        host_layout.addWidget(self.custom_host_input)

        self.run_trace_btn = QPushButton("Run Traceroute")
        self.run_trace_btn.setFixedHeight(35)
        self.run_trace_btn.setStyleSheet("""
            QPushButton {
                background-color: #17A2B8;
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:pressed {
                background-color: #117A8B;
            }
        """)
        self.run_trace_btn.clicked.connect(self.run_tracert)
        host_layout.addWidget(self.run_trace_btn)

        trace_layout.addLayout(host_layout)

        self.trace_results = QTableWidget(0, 2)
        self.trace_results.setHorizontalHeaderLabels(["Hop", "Address / Time"])
        self.trace_results.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A28;
                color: #EEEEEE;
                border: 1px solid #44444F;
                gridline-color: #44444F;
            }
            QHeaderView::section {
                background-color: #2A2A3E;
                color: #FFFFFF;
                padding: 4px;
                font-size: 14px;
            }
        """)
        header_trace = self.trace_results.horizontalHeader()
        header_trace.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_trace.setSectionResizeMode(1, QHeaderView.Stretch)
        trace_layout.addWidget(self.trace_results)

        layout.addWidget(trace_section)

        # ─── Internet Speed Test ─────────────────────────
        speed_section = QFrame()
        speed_layout = QVBoxLayout()
        speed_layout.setSpacing(10)
        speed_section.setLayout(speed_layout)

        speed_label = QLabel("Internet Speed Test:")
        speed_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        speed_label.setStyleSheet("color: #CFCFDF;")
        speed_layout.addWidget(speed_label)

        speed_inner_layout = QHBoxLayout()
        self.run_speed_btn = QPushButton("Run Internet Speed Test")
        self.run_speed_btn.setFixedHeight(35)
        self.run_speed_btn.setStyleSheet("""
            QPushButton {
                background-color: #6F42C1;
                color: #FFFFFF;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #59359C;
            }
            QPushButton:pressed {
                background-color: #4C2F80;
            }
        """)
        self.run_speed_btn.clicked.connect(self.run_speed_test)
        speed_inner_layout.addWidget(self.run_speed_btn)

        self.speed_result_box = QTextEdit()
        self.speed_result_box.setReadOnly(True)
        self.speed_result_box.setFixedHeight(100)
        self.speed_result_box.setStyleSheet("""
            QTextEdit {
                background-color: #1A1A28;
                border: 1px solid #44444F;
                border-radius: 5px;
                color: #EEEEEE;
                font-family: Consolas, monospace;
                font-size: 12px;
                padding: 10px;
            }
        """)
        speed_inner_layout.addWidget(self.speed_result_box)

        speed_layout.addLayout(speed_inner_layout)
        layout.addWidget(speed_section)

        layout.addStretch()

        # Thread & progress-dialog references
        self.ping_thread = None
        self.dns_thread = None
        self.trace_thread = None
        self.speed_thread = None
        self.ping_progress = None
        self.dns_progress = None
        self.trace_progress = None
        self.speed_progress = None

        # Store last DNS results
        self.last_dns_results = {}

    def center_progress(self, dialog: QProgressDialog):
        """
        Center a QProgressDialog on this widget.
        """
        parent_geo = self.frameGeometry()
        dlg_geo = dialog.frameGeometry()
        x = parent_geo.center().x() - (dlg_geo.width() // 2)
        y = parent_geo.center().y() - (dlg_geo.height() // 2)
        dialog.move(x, y)

    def run_ping_test(self):
        """
        Start PingWorker to ping each Roblox host.
        """
        self.ping_table.setRowCount(0)
        self.run_ping_btn.setEnabled(False)

        self.ping_progress = QProgressDialog("Pinging Roblox hosts...", None, 0, 0, self)
        self.ping_progress.setWindowModality(Qt.WindowModal)
        self.ping_progress.setMinimumSize(400, 120)
        self.ping_progress.show()
        self.center_progress(self.ping_progress)

        self.ping_thread = PingWorker(ROBLOX_SERVERS, count=3)
        self.ping_thread.result_signal.connect(self.display_ping_results)
        self.ping_thread.start()

    def display_ping_results(self, results: dict):
        """
        Populate the ping_table once PingWorker finishes.
        """
        if self.ping_progress:
            self.ping_progress.cancel()
        self.run_ping_btn.setEnabled(True)

        self.ping_table.setRowCount(0)
        for host, avg in results.items():
            row = self.ping_table.rowCount()
            self.ping_table.insertRow(row)
            self.ping_table.setItem(row, 0, QTableWidgetItem(host))
            self.ping_table.setItem(row, 1, QTableWidgetItem(avg))

        GlobalLogger.append(f"Ping Test Results: {json.dumps(results)}")

    def run_dns_test(self):
        """
        Start PingWorker to benchmark each DNS server.
        """
        self.dns_table.setRowCount(0)
        self.run_dns_btn.setEnabled(False)
        self.apply_fastest_btn.setEnabled(False)
        self.fastest_label.setText("Fastest DNS: N/A")

        servers = DNS_SERVERS_BASE.copy()
        servers["Current DNS"] = None  # Discover via PingWorker

        self.dns_progress = QProgressDialog("Benchmarking DNS servers...", None, 0, 0, self)
        self.dns_progress.setWindowModality(Qt.WindowModal)
        self.dns_progress.setMinimumSize(400, 120)
        self.dns_progress.show()
        self.center_progress(self.dns_progress)

        self.dns_thread = PingWorker(servers, count=self.dns_ping_count_spinbox.value())
        self.dns_thread.result_signal.connect(self.display_dns_results)
        self.dns_thread.start()

    def display_dns_results(self, results: dict):
        """
        Populate the dns_table and determine the fastest server.
        """
        if self.dns_progress:
            self.dns_progress.cancel()
        self.run_dns_btn.setEnabled(True)

        self.dns_table.setRowCount(0)
        ordered = ["Current DNS"] + [
            k for k in results.keys() if k != "Current DNS"
        ]
        for name in ordered:
            avg = results.get(name, "N/A")
            row = self.dns_table.rowCount()
            self.dns_table.insertRow(row)
            self.dns_table.setItem(row, 0, QTableWidgetItem(name))
            self.dns_table.setItem(row, 1, QTableWidgetItem(avg))

        fastest_name, fastest_val = self.get_fastest_dns(results)
        if fastest_name and fastest_val not in ("N/A", ""):
            self.fastest_label.setText(f"Fastest DNS: {fastest_name} ({fastest_val})")
            self.apply_fastest_btn.setEnabled(True)
        else:
            self.fastest_label.setText("Fastest DNS: N/A")
            self.apply_fastest_btn.setEnabled(False)

        self.last_dns_results = results
        GlobalLogger.append(f"DNS Benchmark Results: {json.dumps(results)}")

    def get_fastest_dns(self, results: dict):
        """
        Return (name, '<n> ms') of the fastest (lowest-latency) DNS server.
        """
        best, best_val = None, 999999
        for name, val in results.items():
            try:
                ms = int(val.replace("ms", "").strip())
                if ms < best_val:
                    best_val = ms
                    best = name
            except Exception:
                continue
        if best is not None:
            return best, f"{best_val} ms"
        return None, None

    def apply_fastest_dns(self):
        """
        Apply the fastest DNS IP to both Ethernet and Wi-Fi via netsh.
        """
        fastest_name, _ = self.get_fastest_dns(self.last_dns_results)
        fastest_ip = None
        if fastest_name and fastest_name != "Current DNS":
            fastest_ip = DNS_SERVERS_BASE.get(fastest_name)

        if not fastest_ip:
            QMessageBox.warning(self, "Apply DNS", "No valid fastest DNS found.")
            return

        logs = []
        for iface in ["Ethernet", "Wi-Fi"]:
            cmd = f'netsh interface ip set dns name="{iface}" static {fastest_ip}'
            logs.append(subprocess.getoutput(cmd))

        msg = "\n".join(logs)
        QMessageBox.information(self, "Applied DNS", f"Set DNS to {fastest_ip}:\n{msg}")
        GlobalLogger.append(f"Fastest DNS applied: {fastest_ip}")

    def run_tracert(self):
        """
        Placeholder traceroute using PingWorker. A real tracert would parse 'tracert' output.
        """
        target = self.custom_host_input.text().strip()
        if not target:
            QMessageBox.warning(self, "Traceroute", "Please enter a hostname or IP.")
            return

        self.trace_results.setRowCount(0)
        self.run_trace_btn.setEnabled(False)

        self.trace_progress = QProgressDialog(f"Running tracert to {target}...", None, 0, 0, self)
        self.trace_progress.setWindowModality(Qt.WindowModal)
        self.trace_progress.setMinimumSize(400, 120)
        self.trace_progress.show()
        self.center_progress(self.trace_progress)

        # Placeholder: Use PingWorker to get a single ping output as dummy traceroute
        self.trace_thread = PingWorker({target: target}, count=1)
        self.trace_thread.result_signal.connect(self.display_tracert_results)
        self.trace_thread.start()

    def display_tracert_results(self, results: dict):
        """
        Dump placeholder “tracert” lines into trace_results table.
        """
        if self.trace_progress:
            self.trace_progress.cancel()
        self.run_trace_btn.setEnabled(True)

        # The PingWorker emits a dict: {target: "<ping output>"}
        output = ""
        if results:
            output = list(results.values())[0]

        self.trace_results.setRowCount(0)
        for line in output.splitlines():
            row = self.trace_results.rowCount()
            self.trace_results.insertRow(row)
            parts = line.strip().split()
            if len(parts) >= 2 and parts[0].isdigit():
                hop = parts[0]
                rest = " ".join(parts[1:])
            else:
                hop = ""
                rest = line.strip()
            self.trace_results.setItem(row, 0, QTableWidgetItem(hop))
            self.trace_results.setItem(row, 1, QTableWidgetItem(rest))

        GlobalLogger.append(f"Traceroute to {self.custom_host_input.text()}: {output}")

    def run_speed_test(self):
        """
        Start SpeedTestWorker thread to run an Internet speed test.
        """
        self.speed_result_box.clear()
        self.run_speed_btn.setEnabled(False)

        self.speed_progress = QProgressDialog("Running Internet Speed Test...", None, 0, 0, self)
        self.speed_progress.setWindowModality(Qt.WindowModal)
        self.speed_progress.setMinimumSize(400, 120)
        self.speed_progress.show()
        self.center_progress(self.speed_progress)

        self.speed_thread = SpeedTestWorker()
        self.speed_thread.result_signal.connect(self.display_speed_results)
        self.speed_thread.start()

    def display_speed_results(self, output: str):
        """
        Once SpeedTestWorker finishes, display its output or error message.
        """
        if self.speed_progress:
            self.speed_progress.cancel()
        self.run_speed_btn.setEnabled(True)
        self.speed_result_box.setPlainText(output)
        GlobalLogger.append(f"Speed Test Results:\n{output}")

    def run_dns_test_sync(self):
        """
        Synchronous helper for Dashboard's Auto-Optimize:
        Blocks and returns last DNS results dict.
        """
        servers = DNS_SERVERS_BASE.copy()
        servers["Current DNS"] = None
        worker = PingWorker(servers, count=3)
        worker.run()  # Blocks
        return worker.results

    def apply_dns_server(self, dns_name: str):
        """
        Called from DashboardPage Auto-Optimize: set DNS for both Ethernet and Wi-Fi.
        """
        ip = DNS_SERVERS_BASE.get(dns_name)
        if not ip:
            return
        for iface in ["Ethernet", "Wi-Fi"]:
            subprocess.getoutput(f'netsh interface ip set dns name="{iface}" static {ip}')
        GlobalLogger.append(f"Auto-Optimize: DNS set to {ip}")

    def shutdown(self):
        """
        Called when app is closing—terminate any running threads cleanly.
        """
        try:
            if self.ping_thread and self.ping_thread.isRunning():
                self.ping_thread.terminate()
                self.ping_thread.wait()
        except Exception:
            pass
        try:
            if self.dns_thread and self.dns_thread.isRunning():
                self.dns_thread.terminate()
                self.dns_thread.wait()
        except Exception:
            pass
        try:
            if self.trace_thread and self.trace_thread.isRunning():
                self.trace_thread.terminate()
                self.trace_thread.wait()
        except Exception:
            pass
        try:
            if self.speed_thread and self.speed_thread.isRunning():
                self.speed_thread.terminate()
                self.speed_thread.wait()
        except Exception:
            pass


# For standalone testing
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = NetworkTestsPage()
    window.show()
    sys.exit(app.exec())

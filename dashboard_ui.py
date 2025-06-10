# dashboard_ui.py

from collections import deque
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QProgressBar,
    QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import psutil
import random
import os

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

class DashboardUI(QWidget):
    """
    Modernized DashboardUI with:
      - Big numeric labels (+ progress bars) for CPU & RAM
      - Combined Latency + FPS card
      - CPU & RAM history charts (slightly narrower)
      - Enlarged buttons
      - Larger labels & values
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main container layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        self.setLayout(main_layout)

        # ─── Top Metric Cards Row ──────────────────────────
        cards_frame = QFrame()
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        cards_frame.setLayout(cards_layout)

        # CPU Usage Card (224×140 px)
        self.cpu_card = self._make_metric_card_with_bar("CPU Usage", "0%")
        cards_layout.addWidget(self.cpu_card)

        # RAM Usage Card (224×140 px)
        self.ram_card = self._make_metric_card_with_bar("RAM Usage", "0%")
        cards_layout.addWidget(self.ram_card)

        # Latency Card (224×140 px)
        latency_card = QFrame()
        latency_card.setStyleSheet("""
            QFrame { background-color: #2A2A3E; border-radius: 10px; }
        """)
        latency_card.setFixedSize(224, 140)
        lat_layout = QVBoxLayout()
        lat_layout.setContentsMargins(15, 10, 15, 10)

        lat_label = QLabel("Latency")
        lat_label.setFont(QFont(CUSTOM_FONT, 12))
        lat_label.setStyleSheet("color: #CFCFDF;")
        lat_value = QLabel("0 ms")
        lat_value.setFont(QFont(CUSTOM_FONT, 28, QFont.Bold))
        lat_value.setStyleSheet("color: #FFFFFF;")
        
        lat_layout.addWidget(lat_label)
        lat_layout.addStretch()
        lat_layout.addWidget(lat_value)
        latency_card.setLayout(lat_layout)

        # FPS Card (224×140 px)
        fps_card = QFrame()
        fps_card.setStyleSheet("""
            QFrame { background-color: #2A2A3E; border-radius: 10px; }
        """)
        fps_card.setFixedSize(224, 140)
        fps_layout = QVBoxLayout()
        fps_layout.setContentsMargins(15, 10, 15, 10)

        fps_label = QLabel("FPS")
        fps_label.setFont(QFont(CUSTOM_FONT, 12))
        fps_label.setStyleSheet("color: #CFCFDF;")
        fps_value = QLabel("0")
        fps_value.setFont(QFont(CUSTOM_FONT, 28, QFont.Bold))
        fps_value.setStyleSheet("color: #FFFFFF;")
        
        fps_layout.addWidget(fps_label)
        fps_layout.addStretch()
        fps_layout.addWidget(fps_value)
        fps_card.setLayout(fps_layout)

        # Keep references so we can update them in update_metrics()
        self.latency_value_label = lat_value
        self.fps_value_label = fps_value

        cards_layout.addWidget(latency_card)
        cards_layout.addWidget(fps_card)
        cards_layout.addStretch()
        main_layout.addWidget(cards_frame)

        # ─── Chart Row (CPU & RAM History) ─────────────────
        charts_frame = QFrame()
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(20)
        charts_frame.setLayout(charts_layout)

        # Prepare history deques for visualization (length 30)
        self.history_length = 30
        self.cpu_history = deque([0]*self.history_length, maxlen=self.history_length)
        self.ram_history = deque([0]*self.history_length, maxlen=self.history_length)

        # CPU History Chart (464×300 px)
        self.cpu_chart_frame = self._make_chart_card("CPU History", self.cpu_history, "Usage (%)", "#5E5EFF")
        charts_layout.addWidget(self.cpu_chart_frame)

        # RAM History Chart (464×300 px)
        self.ram_chart_frame = self._make_chart_card("Memory History", self.ram_history, "Usage (%)", "#5E5EFF")
        charts_layout.addWidget(self.ram_chart_frame)

        main_layout.addWidget(charts_frame)

        # ─── Bottom Action Buttons Row ─────────────────────
        actions_frame = QFrame()
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(20)
        actions_frame.setLayout(actions_layout)

        actions_layout.addStretch()

        self.auto_opt_btn = QPushButton("Auto-Optimize")
        self.auto_opt_btn.setFixedHeight(70)   # Bigger height
        self.auto_opt_btn.setMinimumWidth(200) # Wider button
        self.auto_opt_btn.setStyleSheet("""
            QPushButton {
                background-color: #5E5EFF;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #4A4AFF;
            }
            QPushButton:pressed {
                background-color: #3A3AE6;
            }
        """)
        actions_layout.addWidget(self.auto_opt_btn)

        self.start_roblox_btn = QPushButton("Start Roblox")
        self.start_roblox_btn.setFixedHeight(70)
        self.start_roblox_btn.setMinimumWidth(200)
        self.start_roblox_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5E5E;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #E04A4A;
            }
            QPushButton:pressed {
                background-color: #C43939;
            }
        """)
        actions_layout.addWidget(self.start_roblox_btn)

        main_layout.addWidget(actions_frame)

        # ─── Timer to update metrics every second ──────────
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self.update_metrics)
        self.update_timer.start()

    def _make_metric_card_with_bar(self, title: str, initial_value: str):
        """
        Create a metric card (224×140 px) with:
          - Title label (12 pt)
          - Large numeric label (28 pt)
          - Thin horizontal QProgressBar beneath
        """
        card = QFrame()
        card.setStyleSheet("""
            QFrame { background-color: #2A2A3E; border-radius: 10px; }
        """)
        card.setFixedSize(224, 140)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)

        lbl = QLabel(title)
        lbl.setFont(QFont(CUSTOM_FONT, 12))
        lbl.setStyleSheet("color: #CFCFDF;")
        layout.addWidget(lbl)

        layout.addStretch()

        val_lbl = QLabel(initial_value)
        val_lbl.setFont(QFont(CUSTOM_FONT, 28, QFont.Bold))
        val_lbl.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(val_lbl)

        # Horizontal progress bar under the number
        bar = QProgressBar()
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(12)
        bar.setStyleSheet("""
            QProgressBar {
                background-color: #1A1A28;
                border: 1px solid #44444F;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #5E5EFF;
                border-radius: 5px;
            }
        """)
        layout.addWidget(bar)

        card.setLayout(layout)

        # Attach references for updating
        if title == "CPU Usage":
            self.cpu_value_label = val_lbl
            self.cpu_bar = bar
        elif title == "RAM Usage":
            self.ram_value_label = val_lbl
            self.ram_bar = bar

        return card

    def _make_chart_card(self, title: str, history_deque, ylabel: str, line_color: str):
        """
        Create a chart card (464×300 px) embedding a matplotlib FigureCanvas.
        history_deque: deque of numeric values to plot.
        line_color: hex color for the plot line.
        """
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame { background-color: #2A2A3E; border-radius: 10px; }
        """)
        frame.setFixedSize(464, 300)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        header_layout = QHBoxLayout()
        header_label = QLabel(title)
        header_label.setFont(QFont(CUSTOM_FONT, 12, QFont.Bold))
        header_label.setStyleSheet("color: #FFFFFF;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Create matplotlib canvas
        canvas = FigureCanvas(Figure(figsize=(4, 2.2)))
        ax = canvas.figure.subplots()
        ax.plot(list(range(len(history_deque))), list(history_deque),
                linewidth=2, color=line_color)
        ax.set_facecolor("#2A2A3E")
        ax.tick_params(colors="#CFCFDF")
        ax.spines["bottom"].set_color("#44444F")
        ax.spines["left"].set_color("#44444F")
        ax.spines["top"].set_color("#2A2A3E")
        ax.spines["right"].set_color("#2A2A3E")
        ax.set_ylabel(ylabel, color="#CFCFDF")
        canvas.figure.set_facecolor("#2A2A3E")

        # Store references to update later
        if title == "CPU History":
            self.cpu_chart_ax = ax
            self.cpu_chart_canvas = canvas
            self.cpu_history = history_deque
        elif title == "Memory History":
            self.ram_chart_ax = ax
            self.ram_chart_canvas = canvas
            self.ram_history = history_deque

        layout.addWidget(canvas)
        frame.setLayout(layout)
        return frame

    def update_metrics(self):
        """
        Called by QTimer every second. Updates:
          - CPU % text + CPU progress bar
          - RAM % text + RAM progress bar
          - Redraw CPU & RAM charts
          - (Placeholder) Update latency + FPS labels
        """
        # Update CPU
        cpu_pct = psutil.cpu_percent(interval=None)
        self.cpu_value_label.setText(f"{cpu_pct:.0f}%")
        self.cpu_bar.setValue(int(cpu_pct))
        self.cpu_history.append(cpu_pct)

        # Update RAM
        ram_pct = psutil.virtual_memory().percent
        self.ram_value_label.setText(f"{ram_pct:.0f}%")
        self.ram_bar.setValue(int(ram_pct))
        self.ram_history.append(ram_pct)

        # Redraw CPU chart
        self.cpu_chart_ax.clear()
        self.cpu_chart_ax.plot(
            list(range(len(self.cpu_history))),
            list(self.cpu_history),
            linewidth=2, color="#5E5EFF"
        )
        self.cpu_chart_ax.set_facecolor("#2A2A3E")
        self.cpu_chart_ax.tick_params(colors="#CFCFDF")
        self.cpu_chart_ax.spines["bottom"].set_color("#44444F")
        self.cpu_chart_ax.spines["left"].set_color("#44444F")
        self.cpu_chart_ax.spines["top"].set_color("#2A2A3E")
        self.cpu_chart_ax.spines["right"].set_color("#2A2A3E")
        self.cpu_chart_ax.set_ylabel("Usage (%)", color="#CFCFDF")
        self.cpu_chart_canvas.draw()

        # Redraw RAM chart
        self.ram_chart_ax.clear()
        self.ram_chart_ax.plot(
            list(range(len(self.ram_history))),
            list(self.ram_history),
            linewidth=2, color="#5E5EFF"
        )
        self.ram_chart_ax.set_facecolor("#2A2A3E")
        self.ram_chart_ax.tick_params(colors="#CFCFDF")
        self.ram_chart_ax.spines["bottom"].set_color("#44444F")
        self.ram_chart_ax.spines["left"].set_color("#44444F")
        self.ram_chart_ax.spines["top"].set_color("#2A2A3E")
        self.ram_chart_ax.spines["right"].set_color("#2A2A3E")
        self.ram_chart_ax.set_ylabel("Usage (%)", color="#CFCFDF")
        self.ram_chart_canvas.draw()

        # ── Placeholder for real latency/fps logic ──────
        # Replace with actual measurements; for now, leave at 0:
        # e.g.:
        # latency_ms = ping_some_server()
        # self.latency_value_label.setText(f"{latency_ms} ms")
        #
        # fps_count = measure_current_fps()
        # self.fps_value_label.setText(f"{fps_count}")

        # (Currently, remains "0 ms" and "0" for FPS.)
        pass


# If run standalone for testing:
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = DashboardUI()
    window.show()
    sys.exit(app.exec())

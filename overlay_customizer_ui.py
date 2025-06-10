# overlay_customizer_ui.py
try:
    from PySide6.QtWidgets import QShortcut
except ImportError:
    from PySide6.QtGui import QShortcut

try:
    from PySide6.QtWidgets import QKeySequence
except ImportError:
    from PySide6.QtGui import QKeySequence

import subprocess
import json
import os
import platform
import sys
import re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QPushButton,
    QColorDialog, QHBoxLayout, QLineEdit, QMessageBox, QFrame,
    QApplication, QSpacerItem, QSizePolicy, QProgressDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QPoint, QSettings
from PySide6.QtGui import QColor, QFont

import psutil
from visual_tweaks_and_logs import GlobalLogger

# Determine where to store/read settings.ini
if getattr(sys, 'frozen', False):
    BASE_DIR_FOR_OVERLAY_SETTINGS = os.path.dirname(sys.executable)
else:
    BASE_DIR_FOR_OVERLAY_SETTINGS = os.path.abspath(os.path.dirname(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR_FOR_OVERLAY_SETTINGS, 'settings.ini')

# Try to import the 'keyboard' library for true global hotkeys
GLOBAL_HOTKEY_LIB_AVAILABLE = False
try:
    import keyboard
    GLOBAL_HOTKEY_LIB_AVAILABLE = True
    GlobalLogger.append("[OverlayCustomizer] 'keyboard' library imported for global hotkeys.", is_internal=True)
except ImportError:
    GlobalLogger.append(
        "[OverlayCustomizer] 'keyboard' library NOT FOUND. "
        "Global hotkeys will not be available; fallback to QShortcut (app must be focused).",
        is_error=True, is_internal=True
    )

# Try to import Windows‐specific APIs for FPS detection
FPS_DETECTION_SUPPORTED = False
if platform.system().lower() == "windows":
    try:
        import win32gui
        import win32process
        FPS_DETECTION_SUPPORTED = True
        GlobalLogger.append("[OverlayCustomizer] Windows APIs for FPS detection imported.", is_internal=True)
    except ImportError:
        GlobalLogger.append(
            "[OverlayCustomizer] 'win32gui' or 'win32process' not found. "
            "FPS detection will be unavailable on Windows.", is_error=True, is_internal=True
        )

CREATE_NO_WINDOW = 0x08000000 if platform.system().lower().startswith("win") else 0


class OverlayWindow(QWidget):
    """
    This frameless, always‐on‐top, translucent window displays:
      • CPU% and RAM% (top line)
      • Ping to 8.8.8.8 + current FPS (bottom line)
    It refreshes once per second and emits fps_updated(str) whenever the FPS changes.
    """
    fps_updated = Signal(str)

    def __init__(self):
        super().__init__()
        GlobalLogger.append("[OverlayWindow] Initializing overlay window.", is_internal=True)

        # Make window always on top, frameless, transparent to mouse clicks
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # Info label with monospaced font, semi‐transparent background
        self.info_label = QLabel("Overlay Initializing...", self)
        self.info_label.setStyleSheet(
            """
            QLabel {
                color: #00FF00;
                font-size: 15px;
                font-family: "Consolas", "Lucida Console", Monaco, monospace;
                background-color: rgba(20, 20, 20, 190);
                padding: 7px 10px;
                border-radius: 6px;
                line-height: 1.3;
            }
            """
        )
        self.info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.info_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.info_label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.refresh_stats)

        self.current_fps_value = "N/A"
        self.target_roblox_pid = None

        # Position overlay at default coords (will be moved properly later)
        self.move(30, 30)
        self.setMinimumSize(200, 60)

        GlobalLogger.append("[OverlayWindow] OverlayWindow initialization complete.", is_internal=True)

    def start_overlay(self):
        """Show the overlay and start periodic refresh."""
        if not self.update_timer.isActive():
            self.update_timer.start(1000)
            GlobalLogger.append("[OverlayWindow] Update timer started.", is_internal=True)
        self.show()
        self.refresh_stats()
        GlobalLogger.append("[OverlayWindow] Overlay shown and active.", is_internal=True)

    def stop_overlay(self):
        """Stop the refresh timer and hide the overlay."""
        if self.update_timer.isActive():
            self.update_timer.stop()
            GlobalLogger.append("[OverlayWindow] Update timer stopped.", is_internal=True)
        self.hide()
        GlobalLogger.append("[OverlayWindow] Overlay hidden.", is_internal=True)

    def _try_find_roblox_pid(self):
        """Search for a running RobloxPlayerBeta.exe process; return its PID or None."""
        if not FPS_DETECTION_SUPPORTED:
            return None

        found_pid = None
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and "RobloxPlayerBeta.exe" in proc.info['name']:
                    found_pid = proc.info['pid']
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if found_pid != self.target_roblox_pid:
            if found_pid:
                GlobalLogger.append(f"[OverlayWindow] Detected Roblox PID: {found_pid}", is_internal=True)
            elif self.target_roblox_pid:
                GlobalLogger.append(f"[OverlayWindow] Roblox PID {self.target_roblox_pid} lost.", is_internal=True)
            self.target_roblox_pid = found_pid

        return self.target_roblox_pid

    def _fetch_fps_from_roblox_window_title(self):
        """
        On Windows, enumerate windows belonging to the Roblox process
        and parse “FPS: <number>” from its title bar. Returns FPS string or “N/A”.
        """
        if not FPS_DETECTION_SUPPORTED:
            return "N/A (OS)"

        if not self.target_roblox_pid or not psutil.pid_exists(self.target_roblox_pid):
            self._try_find_roblox_pid()

        if not self.target_roblox_pid:
            return "N/A (Game)"

        fps_value_container = ["N/A"]

        def enum_windows_callback(hwnd, param):
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == self.target_roblox_pid:
                    title = win32gui.GetWindowText(hwnd)
                    if "Roblox" in title:
                        match = re.search(r"FPS\s*:\s*(\d+)", title, re.IGNORECASE)
                        if match:
                            fps_value_container[0] = match.group(1)
                            return False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception:
            pass

        return fps_value_container[0]

    def refresh_stats(self):
        """Called once per second: updates CPU/RAM, ping, FPS, updates label text."""
        # CPU & RAM
        cpu_usage = psutil.cpu_percent(interval=None)
        ram_usage = psutil.virtual_memory().percent

        # Ping to 8.8.8.8 (single packet, 500ms timeout on Windows; 1s on Unix)
        ping_val = "N/A"
        try:
            sys_pl = platform.system().lower()
            if sys_pl.startswith("win"):
                cmd = ["ping", "-n", "1", "-w", "500", "8.8.8.8"]
            else:
                # Linux: -c 1 -W 1; macOS: -c 1 -t 1
                if sys_pl == "linux":
                    cmd = ["ping", "-c", "1", "-W", "1", "8.8.8.8"]
                else:
                    cmd = ["ping", "-c", "1", "-t", "1", "8.8.8.8"]

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
                creationflags=CREATE_NO_WINDOW,
                encoding='utf-8',
                errors='ignore'
            )
            out, _ = proc.communicate(timeout=1.5)
            if sys_pl.startswith("win"):
                m = re.search(r"Average = (\d+)ms", out, re.IGNORECASE)
                if m:
                    ping_val = f"{m.group(1)}ms"
            else:
                m = re.search(r"min\/avg\/max\/.*= [\d\.]+\/([\d\.]+)\/", out, re.IGNORECASE)
                if m:
                    ping_val = f"{float(m.group(1)):.0f}ms"
        except Exception:
            pass

        # FPS
        self.current_fps_value = self._fetch_fps_from_roblox_window_title()

        # Update label text
        self.info_label.setText(
            f"CPU : {cpu_usage:<3.0f}%   RAM : {ram_usage:<3.0f}%\n"
            f"Ping: {ping_val:<7s} FPS : {self.current_fps_value}"
        )
        self.adjustSize()
        self.fps_updated.emit(self.current_fps_value)

    def apply_style_and_position(self, text_color_hex, theme_name, position_str, screen_rect):
        """
        Rebuilds the label’s stylesheet based on chosen theme, text color, and repositions
        the overlay window in one of four corners. `screen_rect` is a QRect from primaryScreen.availableGeometry().
        """
        GlobalLogger.append(
            f"[OverlayWindow] Applying style: color={text_color_hex}, theme={theme_name}, pos={position_str}",
            is_internal=True
        )

        base_css = (
            f"color: {text_color_hex}; "
            "font-size: 15px; "
            "font-family: 'Consolas', 'Lucida Console', Monaco, monospace; "
            "padding: 7px 10px; "
            "border-radius: 6px; "
            "line-height: 1.3; "
        )
        if theme_name == "Minimal (transparent text)":
            final_css = base_css + "background-color: transparent;"
        elif theme_name == "Dark (semi-transparent)":
            final_css = base_css + "background-color: rgba(10, 10, 10, 210);"
        else:  # "HUD (black bg)"
            final_css = base_css + "background-color: rgba(20, 20, 20, 190);"

        self.info_label.setStyleSheet(final_css)
        self.refresh_stats()  # immediately refresh so color takes effect

        QApplication.processEvents()

        # Reposition according to position_str
        overlay_w, overlay_h = self.width(), self.height()
        margin = 25
        left = screen_rect.left()
        top = screen_rect.top()
        right = screen_rect.right()
        bottom = screen_rect.bottom()
        if position_str == "Top-Left":
            x, y = left + margin, top + margin
        elif position_str == "Top-Right":
            x, y = right - overlay_w - margin, top + margin
        elif position_str == "Bottom-Left":
            x, y = left + margin, bottom - overlay_h - margin
        else:  # Bottom-Right
            x, y = right - overlay_w - margin, bottom - overlay_h - margin

        self.move(QPoint(x, y))
        GlobalLogger.append(f"[OverlayWindow] Moved to x={x}, y={y}, size={overlay_w}×{overlay_h}", is_internal=True)


class OverlayCustomizerPage(QWidget):
    """
    The page where users select:
      • Overlay Theme (HUD / Minimal / Dark)
      • Overlay Position (TL, TR, BL, BR)
      • Overlay Text Color (QColorDialog)
      • Hotkey to toggle overlay (Global via 'keyboard' lib, or QShortcut fallback)
      • Buttons to Activate / Deactivate overlay
    Settings are persisted in settings.ini under [overlay].
    """
    def __init__(self, main_window_instance):
        super().__init__()
        GlobalLogger.append("[OverlayCustomizerPage] Initializing.", is_internal=True)
        self.main_window = main_window_instance
        self.overlay_instance = OverlayWindow()

        # Load persisted settings (or defaults)
        self.app_settings = QSettings(SETTINGS_FILE, QSettings.Format.IniFormat)
        self.current_text_color = self.app_settings.value("overlay/text_color", "#00FF00", type=str)
        self.current_theme = self.app_settings.value("overlay/theme", "HUD (black bg)", type=str)
        self.current_position = self.app_settings.value("overlay/position", "Top-Right", type=str)
        self.current_hotkey_str = self.app_settings.value("overlay/hotkey", "Ctrl+Shift+Alt+O", type=str)
        self._current_hotkey_obj = None

        # Page styling: dark background, light text
        self.setStyleSheet("""
            QWidget { background-color: #1E1E2F; font-family: "Segoe UI", sans-serif; }
            QLabel { color: #FFFFFF; font-size: 14px; }
            QLabel#pageTitle { color: #FFFFFF; font-size: 24px; font-weight: bold; margin-bottom: 15px; }
            QComboBox, QLineEdit {
                background-color: #2A2A3E;
                color: #EEEEEE;
                border: 1px solid #44444F;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14px;
            }
            QComboBox:hover, QLineEdit:hover {
                border: 1px solid #5E5EFF;
            }
            QPushButton {
                font-size: 14px;
                color: #FFFFFF;
                padding: 10px 15px;
                border-radius: 5px;
                min-height: 38px;
                font-weight: 500;
            }
            QPushButton#colorBtn { background-color: #5E5EFF; border: 1px solid #4A4AFF; }
            QPushButton#colorBtn:hover { background-color: #4A4AFF; }
            QPushButton#activateBtn { background-color: #28A745; border: 1px solid #1E7E34; }
            QPushButton#activateBtn:hover { background-color: #218838; }
            QPushButton#deactivateBtn { background-color: #FF5E5E; border: 1px solid #E04A4A; }
            QPushButton#deactivateBtn:hover { background-color: #E04A4A; }
            QPushButton#setHotkeyBtn { background-color: #ffc107; color: #000000; border: 1px solid #e0a800; }
            QPushButton#setHotkeyBtn:hover { background-color: #e0a800; }
            QLabel#colorPreviewLabel { border: 1px solid #888; padding: 2px 5px; color: #FFFFFF; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 25, 30, 25)
        main_layout.setSpacing(18)
        self.setLayout(main_layout)

        # Page title
        title = QLabel("Performance Overlay Customizer")
        title.setObjectName("pageTitle")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # ----- Settings Frame (deep background)
        settings_frame = QFrame()
        settings_frame.setStyleSheet("QFrame { background-color: #2A2A3E; border-radius: 8px; }")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        settings_layout.setSpacing(15)

        # Overlay Theme dropdown
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Overlay Theme:")
        theme_label.setStyleSheet("color: #CFCFDF;")
        theme_layout.addWidget(theme_label)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            "HUD (black bg)",
            "Minimal (transparent text)",
            "Dark (semi-transparent)"
        ])
        self.theme_combo.setCurrentText(self.current_theme)
        self.theme_combo.currentTextChanged.connect(self.update_overlay_settings)
        theme_layout.addWidget(self.theme_combo)
        settings_layout.addLayout(theme_layout)

        # Overlay Position dropdown
        pos_layout = QHBoxLayout()
        pos_label = QLabel("Overlay Position:")
        pos_label.setStyleSheet("color: #CFCFDF;")
        pos_layout.addWidget(pos_label)
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right"])
        self.pos_combo.setCurrentText(self.current_position)
        self.pos_combo.currentTextChanged.connect(self.update_overlay_settings)
        pos_layout.addWidget(self.pos_combo)
        settings_layout.addLayout(pos_layout)

        # Text Color selection
        color_layout = QHBoxLayout()
        self.color_btn = QPushButton("Choose Text Color")
        self.color_btn.setObjectName("colorBtn")
        self.color_btn.clicked.connect(self.select_overlay_text_color)
        color_layout.addWidget(self.color_btn)

        self.color_preview_label = QLabel(f"Current: {self.current_text_color}")
        self.color_preview_label.setObjectName("colorPreviewLabel")
        self.update_color_preview_label()
        color_layout.addWidget(self.color_preview_label)
        color_layout.addStretch()
        settings_layout.addLayout(color_layout)

        # Hotkey configuration
        hotkey_layout = QHBoxLayout()
        hotkey_label = QLabel("Toggle Overlay Hotkey:")
        hotkey_label.setStyleSheet("color: #CFCFDF;")
        hotkey_layout.addWidget(hotkey_label)

        self.hotkey_input_field = QLineEdit(self.current_hotkey_str)
        self.hotkey_input_field.setPlaceholderText("e.g., Ctrl+Shift+O")
        hotkey_layout.addWidget(self.hotkey_input_field)

        self.set_hotkey_button = QPushButton("Set/Update Hotkey")
        self.set_hotkey_button.setObjectName("setHotkeyBtn")
        self.set_hotkey_button.clicked.connect(self.configure_hotkey_action)
        hotkey_layout.addWidget(self.set_hotkey_button)

        if not GLOBAL_HOTKEY_LIB_AVAILABLE:
            self.hotkey_input_field.setToolTip(
                "‘keyboard’ library not available; hotkey will only work when app is focused."
            )
            self.set_hotkey_button.setToolTip(
                "‘keyboard’ library not available; hotkey will only work when app is focused."
            )

        settings_layout.addLayout(hotkey_layout)

        main_layout.addWidget(settings_frame)
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Activate / Deactivate buttons
        overlay_action_btn_layout = QHBoxLayout()
        self.activate_button = QPushButton("Activate Overlay")
        self.activate_button.setObjectName("activateBtn")
        self.activate_button.clicked.connect(self.activate_overlay_action)
        overlay_action_btn_layout.addWidget(self.activate_button)

        self.deactivate_button = QPushButton("Deactivate Overlay")
        self.deactivate_button.setObjectName("deactivateBtn")
        self.deactivate_button.clicked.connect(self.deactivate_overlay_action)
        overlay_action_btn_layout.addWidget(self.deactivate_button)

        main_layout.addLayout(overlay_action_btn_layout)
        main_layout.addStretch(1)

        # Register the hotkey immediately (so it toggles overlay)
        self._register_hotkey(self.current_hotkey_str)
        GlobalLogger.append("[OverlayCustomizerPage] Initialization complete.", is_internal=True)

    def update_color_preview_label(self):
        """
        Updates the small label that shows the current text color code,
        with a contrasting background (white if color is dark, black if color is light).
        """
        try:
            c = QColor(self.current_text_color)
            brightness = 0.299*c.redF() + 0.587*c.greenF() + 0.114*c.blueF()
            bg = "white" if brightness < 0.5 else "black"
        except:
            bg = "black"

        self.color_preview_label.setText(f"Current: {self.current_text_color.upper()}")
        self.color_preview_label.setStyleSheet(
            f"QLabel#colorPreviewLabel {{ color: {self.current_text_color}; "
            f"background-color: {bg}; border: 1px solid #888; padding: 2px 5px; }}"
        )

    def select_overlay_text_color(self):
        """Launches QColorDialog to pick a new overlay text color."""
        GlobalLogger.append("[OverlayCustomizerPage] 'Choose Text Color' clicked.", is_internal=True)
        init_color = QColor(self.current_text_color) if QColor.isValidColor(self.current_text_color) else QColor("#00FF00")
        new_color = QColorDialog.getColor(initial=init_color, parent=self, title="Select Overlay Text Color")
        if new_color.isValid():
            self.current_text_color = new_color.name().upper()
            self.update_color_preview_label()
            GlobalLogger.append(f"[OverlayCustomizerPage] Selected text color: {self.current_text_color}", is_internal=True)
            self.update_overlay_settings()

    def update_overlay_settings(self):
        """
        Called whenever theme, position, or color combos change.
        Persists settings and, if overlay is visible, re-applies style/position immediately.
        """
        self.current_theme = self.theme_combo.currentText()
        self.current_position = self.pos_combo.currentText()
        GlobalLogger.append(
            f"[OverlayCustomizerPage] Settings changed: theme={self.current_theme}, "
            f"position={self.current_position}, color={self.current_text_color}", is_internal=True
        )

        # Persist in QSettings
        self.app_settings.setValue("overlay/text_color", self.current_text_color)
        self.app_settings.setValue("overlay/theme", self.current_theme)
        self.app_settings.setValue("overlay/position", self.current_position)

        # If overlay is already showing, update on screen
        if self.overlay_instance.isVisible():
            self.apply_current_settings_to_overlay()

    def apply_current_settings_to_overlay(self):
        """
        Gets primary screen geometry, then calls overlay_instance.apply_style_and_position(...)
        to restyle and reposition.
        """
        screen = QApplication.primaryScreen()
        if not screen:
            GlobalLogger.append("[OverlayCustomizerPage] Error: primaryScreen() returned None", is_error=True)
            QMessageBox.warning(self, "Error", "Unable to detect screen geometry for overlay.")
            return

        screen_geom = screen.availableGeometry()
        self.overlay_instance.apply_style_and_position(
            self.current_text_color,
            self.current_theme,
            self.current_position,
            screen_geom
        )
        GlobalLogger.append("[OverlayCustomizerPage] Applied settings to active overlay.", is_internal=True)

    def activate_overlay_action(self):
        """
        Called when “Activate Overlay” is clicked:
          • Update overlay per current settings
          • Show overlay (start timer)
          • Change button text/tooltips to allow “Refresh/Apply Styles”
        """
        GlobalLogger.append("[OverlayCustomizerPage] 'Activate Overlay' clicked.", is_internal=True)
        self.apply_current_settings_to_overlay()
        self.overlay_instance.start_overlay()
        self.activate_button.setText("Refresh/Apply Styles")
        self.activate_button.setToolTip("Click to re-apply theme/position/color to the visible overlay.")

    def deactivate_overlay_action(self):
        """Called when “Deactivate Overlay” is clicked."""
        GlobalLogger.append("[OverlayCustomizerPage] 'Deactivate Overlay' clicked.", is_internal=True)
        self.overlay_instance.stop_overlay()
        self.activate_button.setText("Activate Overlay")
        self.activate_button.setToolTip("Show the performance overlay with the current settings.")

    def _toggle_overlay_visibility_action(self):
        """
        Toggles overlay on/off. Invoked by hotkey (global via keyboard lib, or QShortcut fallback).
        """
        if self.overlay_instance.isVisible():
            self.deactivate_overlay_action()
            GlobalLogger.append("[OverlayCustomizerPage] Overlay toggled OFF via hotkey.", is_internal=True)
        else:
            self.activate_overlay_action()
            GlobalLogger.append("[OverlayCustomizerPage] Overlay toggled ON via hotkey.", is_internal=True)

    def _unregister_hotkey(self):
        """Removes any previously registered hotkey (global or QShortcut)."""
        if self._current_hotkey_obj:
            # If using 'keyboard' library
            if GLOBAL_HOTKEY_LIB_AVAILABLE and not isinstance(self._current_hotkey_obj, QShortcut):
                try:
                    keyboard.remove_hotkey(self.current_hotkey_str)
                    GlobalLogger.append(f"[OverlayCustomizerPage] Removed global hotkey '{self.current_hotkey_str}'.", is_internal=True)
                except Exception as e:
                    GlobalLogger.append(f"[OverlayCustomizerPage] Error removing global hotkey: {e}", is_error=True)
            else:
                # It’s a QShortcut
                try:
                    self._current_hotkey_obj.activated.disconnect(self._toggle_overlay_visibility_action)
                except Exception:
                    pass
                self._current_hotkey_obj.setEnabled(False)
                self._current_hotkey_obj.deleteLater()
                GlobalLogger.append(f"[OverlayCustomizerPage] Disabled QShortcut '{self.current_hotkey_str}'.", is_internal=True)
            self._current_hotkey_obj = None

    def _register_hotkey(self, hotkey_str):
        """
        Attempts to register `hotkey_str` as a global hotkey (if keyboard lib is available),
        or else as a QShortcut (application-focused). Returns True on success.
        """
        self._unregister_hotkey()
        if not hotkey_str:
            GlobalLogger.append("[OverlayCustomizerPage] Hotkey string empty; skipping registration.", is_internal=True)
            return False

        success = False
        if GLOBAL_HOTKEY_LIB_AVAILABLE:
            try:
                # `keyboard.add_hotkey(...)` returns a handle or None
                handler = keyboard.add_hotkey(hotkey_str, self._toggle_overlay_visibility_action, suppress=False)
                if handler is not None:
                    self._current_hotkey_obj = handler  # store the handle
                    GlobalLogger.append(
                        f"[OverlayCustomizerPage] Global hotkey '{hotkey_str}' registered via 'keyboard' library.",
                        is_internal=True
                    )
                    success = True
                else:
                    GlobalLogger.append(
                        f"[OverlayCustomizerPage] keyboard.add_hotkey returned None for '{hotkey_str}'.",
                        is_error=True, is_internal=True
                    )
            except Exception as e:
                GlobalLogger.append(
                    f"[OverlayCustomizerPage] Failed to register global hotkey '{hotkey_str}': {e}. Will try QShortcut.",
                    is_error=True, is_internal=True
                )

        if not success:
            # Fallback to QShortcut (works only when main app is focused)
            try:
                seq = QKeySequence.fromString(hotkey_str, QKeySequence.PortableText)
                if seq.isEmpty():
                    QMessageBox.warning(
                        self,
                        "Hotkey Error",
                        f"Could not parse '{hotkey_str}' as a valid key sequence."
                    )
                    GlobalLogger.append(
                        f"[OverlayCustomizerPage] QKeySequence.fromString failed for '{hotkey_str}'.",
                        is_error=True
                    )
                    return False

                shortcut = QShortcut(seq, self.main_window)
                shortcut.activated.connect(self._toggle_overlay_visibility_action)
                shortcut.setEnabled(True)
                self._current_hotkey_obj = shortcut
                GlobalLogger.append(
                    f"[OverlayCustomizerPage] QShortcut '{hotkey_str}' registered (application-focused).",
                    is_internal=True
                )
                success = True
            except Exception as e:
                GlobalLogger.append(
                    f"[OverlayCustomizerPage] Error registering QShortcut '{hotkey_str}': {e}",
                    is_error=True, is_internal=True
                )
                success = False

        return success

    def configure_hotkey_action(self):
        """
        Called when user clicks “Set/Update Hotkey”. Attempts to register the new hotkey string.
        """
        new_str = self.hotkey_input_field.text().strip()
        GlobalLogger.append(f"[OverlayCustomizerPage] 'Set/Update Hotkey' clicked, trying '{new_str}'.", is_internal=True)

        if not new_str:
            QMessageBox.warning(self, "Hotkey Error", "Hotkey cannot be empty. Please enter a valid combination (e.g. Ctrl+Shift+O).")
            GlobalLogger.append("[OverlayCustomizerPage] Hotkey configuration failed: empty string.", is_error=True)
            return

        if self._register_hotkey(new_str):
            self.current_hotkey_str = new_str
            self.app_settings.setValue("overlay/hotkey", self.current_hotkey_str)
            msg_type = "Global Hotkey" if (GLOBAL_HOTKEY_LIB_AVAILABLE and not isinstance(self._current_hotkey_obj, QShortcut)) else "App‐focused Hotkey"
            QMessageBox.information(self, "Hotkey Updated", f"{msg_type} set to: '{self.current_hotkey_str}'.")
            GlobalLogger.append(f"[OverlayCustomizerPage] {msg_type} registered and saved: '{self.current_hotkey_str}'.", is_internal=True)
        else:
            QMessageBox.critical(
                self,
                "Hotkey Error",
                f"Failed to set hotkey '{new_str}'. Ensure the format is correct and key isn’t already in use."
            )
            GlobalLogger.append(f"[OverlayCustomizerPage] Failed to set hotkey '{new_str}'.", is_error=True)
            self.hotkey_input_field.setText(self.current_hotkey_str)

    def shutdown(self):
        """
        Called when the app is closing. Unregisters the hotkey (global or QShortcut),
        stops and deletes the overlay, and writes final settings to disk.
        """
        GlobalLogger.append("[OverlayCustomizerPage] Shutdown initiated.", is_internal=True)
        self._unregister_hotkey()

        if self.overlay_instance:
            self.overlay_instance.stop_overlay()
            self.overlay_instance.deleteLater()
            GlobalLogger.append("[OverlayCustomizerPage] Overlay instance stopped and deleted.", is_internal=True)

        # Persist last-used settings
        self.app_settings.setValue("overlay/text_color", self.current_text_color)
        self.app_settings.setValue("overlay/theme", self.current_theme)
        self.app_settings.setValue("overlay/position", self.current_position)
        self.app_settings.setValue("overlay/hotkey", self.current_hotkey_str)
        self.app_settings.sync()
        GlobalLogger.append("[OverlayCustomizerPage] Settings saved; shutdown complete.", is_internal=True)


# For standalone testing:
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = OverlayCustomizerPage(main_window_instance=None)
    window.show()
    sys.exit(app.exec())

from __future__ import annotations

import threading
import queue
import sys
from typing import Optional


class StatusDot:
    """
    Cross-platform status indicator with macOS menu bar support.

    Colors: blue (idle) → yellow (crop mode) → green (completed)

    Public API:
    - start(): launch indicator
    - set_idle(), set_pending_crop(), set_done()
    - stop(): close indicator
    """

    # Color constants
    COLORS = {
        "idle": "#2b6cb0",      # blue
        "crop": "#d69e2e",      # yellow  
        "done": "#2f855a"       # green
    }

    def __init__(self, diameter: int = 18, margin: int = 24) -> None:
        self._diameter = diameter
        self._margin = margin
        self._thread: Optional[threading.Thread] = None
        self._cmd_q: "queue.Queue[tuple[str, Optional[str]]]" = queue.Queue()
        self._alive = threading.Event()
        # Label shown to the LEFT of the dot in the tray icon/overlay
        self._label_text: str = ""
        # Style controls (user-tunable)
        self.font_family: str = "SF Pro Text"
        self.font_size: int = 16
        self.text_color: str = "#ffffff"
        self.opacity: float = 1.0  # 0.0..1.0
        self.max_label_chars: int = 24

    def set_idle(self) -> None:
        self._set_color(self.COLORS["idle"])

    def set_pending_crop(self) -> None:
        self._set_color(self.COLORS["crop"])

    def set_done(self) -> None:
        self._set_color(self.COLORS["done"])

    def _set_color(self, color: str) -> None:
        if self._alive.is_set():
            self._cmd_q.put(("color", color))

    def set_label(self, text: str) -> None:
        """Set the short label to render left of the dot."""
        if text is None:
            text = ""
        if self._alive.is_set():
            self._cmd_q.put(("label", text))

    def clear_label(self) -> None:
        if self._alive.is_set():
            self._cmd_q.put(("label", ""))

    def stop(self) -> None:
        if self._alive.is_set():
            self._cmd_q.put(("quit", None))
            self._alive.clear()
            if self._thread is not None:
                self._thread.join(timeout=1.5)

    def start(self) -> None:
        if self._alive.is_set():
            return
        self._alive.set()
        self._thread = threading.Thread(target=self._run_ui, name="StatusDotUI", daemon=True)
        self._thread.start()

    def run_on_current_thread(self) -> None:
        """Run the UI on the calling (main) thread. Blocks until stopped."""
        if self._alive.is_set():
            return
        self._alive.set()
        try:
            self._run_ui()
        finally:
            self._alive.clear()

    def _run_ui(self) -> None:
        if sys.platform == 'darwin':
            try:
                self._run_ui_menubar_macos()
            except Exception:
                self._run_ui_console()
        else:
            self._run_ui_tk()

    def _process_commands_generic(self, update_color_fn, quit_fn, update_label_fn=None):
        """Generic command processor for all UI backends"""
        processed = 0
        while processed < 8:
            try:
                cmd, arg = self._cmd_q.get_nowait()
            except queue.Empty:
                break
            if cmd == "color" and isinstance(arg, str):
                update_color_fn(arg)
            elif cmd == "label" and isinstance(arg, str):
                self._label_text = arg[: self.max_label_chars]
                if update_label_fn is not None:
                    update_label_fn(self._label_text)
            elif cmd == "quit":
                quit_fn()
                return
            processed += 1

    # ---------------- macOS Menu Bar ----------------
    def _run_ui_menubar_macos(self) -> None:
        from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
        from PyQt6.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor, QFont
        from PyQt6.QtCore import Qt, QTimer

        app = QApplication.instance() or QApplication([])

        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("[supy] System tray not available, using console output")
            self._run_ui_console()
            return

        def create_icon(color_hex: str, label_text: str) -> QIcon:
            # Compose an icon with label on the left and a dot on the right
            h = 22
            # Estimate width: char width ~ font_size * 0.6
            est_char_w = max(6, int(self.font_size * 0.6))
            label = (label_text or "")[: self.max_label_chars]
            text_w = est_char_w * len(label) + 6
            dot_w = 22
            total_w = min(256, max(dot_w, text_w + dot_w))

            pixmap = QPixmap(total_w, h)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setOpacity(max(0.0, min(1.0, self.opacity)))

            # Draw label text
            if label:
                font = QFont(self.font_family, self.font_size)
                painter.setFont(font)
                # Text color
                hex_tc = self.text_color.lstrip('#')
                tr, tg, tb = int(hex_tc[0:2], 16), int(hex_tc[2:4], 16), int(hex_tc[4:6], 16)
                painter.setPen(QColor(tr, tg, tb))
                painter.drawText(2, h - 7, label)

            # Draw dot
            hex_color = color_hex.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            painter.setBrush(QBrush(QColor(r, g, b)))
            painter.setPen(Qt.PenStyle.NoPen)
            # Place dot at right side
            painter.drawEllipse(total_w - 19, 3, 16, 16)
            painter.end()

            return QIcon(pixmap)

        status_item = QSystemTrayIcon()
        status_item.setIcon(create_icon(self.COLORS["idle"], self._label_text))
        status_item.setToolTip("Supy Screenshot Tool")
        
        # Context menu
        menu = QMenu()
        menu.addAction("📸 Supy Screenshot Tool")
        menu.addSeparator()
        menu.addAction("⌥⇧Q: Full Screenshot")
        menu.addAction("⌥⇧W: Cropped Screenshot (2-step)")
        menu.addSeparator()
        quit_action = menu.addAction("Quit Supy")
        quit_action.triggered.connect(lambda: self._cmd_q.put(("quit", None)))
        
        status_item.setContextMenu(menu)
        status_item.show()
        print("[supy] Menu bar icon created")

        # Command processing timer
        timer = QTimer()
        timer.timeout.connect(lambda: self._process_commands_generic(
            lambda color: status_item.setIcon(create_icon(color, self._label_text)),
            lambda: (status_item.hide(), app.quit()),
            update_label_fn=lambda _lbl: status_item.setIcon(create_icon(self.COLORS["idle"], self._label_text))
        ))
        timer.start(100)

        app.exec()

    # ---------------- Console Fallback ----------------
    def _run_ui_console(self) -> None:
        """Console-based status indicator as fallback"""
        current_status = "idle"
        print("[supy] Status indicator: Console mode")
        
        status_map = {
            self.COLORS["idle"]: "🔵 IDLE",
            self.COLORS["crop"]: "🟡 CROP MODE", 
            self.COLORS["done"]: "🟢 COMPLETED"
        }
        
        while self._alive.is_set():
            try:
                cmd, arg = self._cmd_q.get(timeout=0.5)
                if cmd == "color":
                    status = status_map.get(arg, f"● {arg}")
                    if status != current_status:
                        print(f"[supy] Status: {status}")
                        current_status = status
                elif cmd == "quit":
                    print("[supy] Status indicator stopped")
                    break
            except queue.Empty:
                continue

    # ---------------- Tk (Windows/Linux) ----------------
    def _run_ui_tk(self) -> None:
        import tkinter as tk
        import tkinter.font as tkfont

        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)

        # Position window
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = screen_w - self._diameter - self._margin
        y = screen_h - self._diameter - self._margin - 60  # Above dock/taskbar
        # Width depends on label length
        est_char_w = max(6, int(self.font_size * 0.6))
        label = (self._label_text or "")[: self.max_label_chars]
        text_w = est_char_w * len(label) + 6
        width = max(self._diameter, min(260, text_w + self._diameter + 8))
        root.geometry(f"{width}x{self._diameter}+{x}+{y}")

        canvas = tk.Canvas(root, width=width, height=self._diameter, 
                          highlightthickness=0, bd=0, bg="#000000")
        canvas.pack(fill=tk.BOTH, expand=True)
        circle = canvas.create_oval(1, 1, self._diameter-1, self._diameter-1, 
                                   fill=self.COLORS["idle"], outline="")
        # Text item
        try:
            fnt = tkfont.Font(family=self.font_family, size=self.font_size)
        except Exception:
            fnt = tkfont.Font(size=self.font_size)
        text_item = canvas.create_text(4, self._diameter//2, anchor='w', fill=self.text_color,
                                       font=fnt, text=label)

        # Windows-specific topmost enforcement
        if sys.platform == 'win32':
            try:
                import ctypes
                hwnd = int(root.winfo_id())
                ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0013)  # TOPMOST | NOMOVE | NOSIZE | NOACTIVATE
            except Exception:
                pass

        # Command processing
        def process_queue():
            def update_color(color):
                canvas.itemconfig(circle, fill=color)
            def update_label(new_label):
                canvas.itemconfig(text_item, text=new_label)
            self._process_commands_generic(update_color, lambda: root.destroy(), update_label_fn=update_label)
            try:
                root.after(100, process_queue)
            except tk.TclError:
                pass

        # Periodic topmost refresh
        def keep_topmost():
            try:
                root.lift()
                root.attributes("-topmost", True)
                root.after(1500, keep_topmost)
            except tk.TclError:
                pass

        process_queue()
        keep_topmost()
        
        try:
            root.mainloop()
        except Exception:
            pass
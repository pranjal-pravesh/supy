from __future__ import annotations

import threading
import time
import os
from typing import Callable

from pynput import keyboard


class GlobalHotkeyListener:
    """
    Listen for Alt/Option + Shift + Q globally and invoke a callback with debounce.
    Works on macOS and Windows (Option on mac maps to Alt in pynput).
    """

    def __init__(self, on_trigger: Callable[[], None], debounce_seconds: float = 0.8) -> None:
        self.on_trigger = on_trigger
        self.debounce_seconds = debounce_seconds
        self._last_trigger_ts: float = 0.0
        self._lock = threading.Lock()
        self._listener: keyboard.Listener | None = None
        self._debug_listener: keyboard.Listener | None = None
        # Modifier and physical-key tracking (independent of layout or Option-modified chars)
        self._alt_down: bool = False
        self._shift_down: bool = False
        self._q_down: bool = False
        # Virtual key codes for 'Q' on macOS and Windows
        self._q_vk_codes = {12, 81}

    def _check_combo(self) -> bool:
        return self._alt_down and self._shift_down and self._q_down

    def _maybe_trigger(self) -> None:
        now = time.monotonic()
        if (now - self._last_trigger_ts) < self.debounce_seconds:
            return
        self._last_trigger_ts = now
        try:
            self.on_trigger()
        except Exception:
            # Silent by design; avoid UI/log spam. Consider adding file logging later.
            pass

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if os.environ.get('SUPY_DEBUG_KEYS') == '1':
            try:
                print(f"[supy] key down: {key}")
            except Exception:
                pass
        with self._lock:
            if key in (keyboard.Key.alt, getattr(keyboard.Key, 'alt_l', None), getattr(keyboard.Key, 'alt_r', None)):
                self._alt_down = True
            if key in (keyboard.Key.shift, getattr(keyboard.Key, 'shift_l', None), getattr(keyboard.Key, 'shift_r', None)):
                self._shift_down = True
            if isinstance(key, keyboard.KeyCode):
                vk = getattr(key, 'vk', None)
                if vk in self._q_vk_codes:
                    self._q_down = True
            if self._check_combo():
                self._maybe_trigger()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if os.environ.get('SUPY_DEBUG_KEYS') == '1':
            try:
                print(f"[supy] key up:   {key}")
            except Exception:
                pass
        with self._lock:
            if key in (keyboard.Key.alt, getattr(keyboard.Key, 'alt_l', None), getattr(keyboard.Key, 'alt_r', None)):
                self._alt_down = False
            if key in (keyboard.Key.shift, getattr(keyboard.Key, 'shift_l', None), getattr(keyboard.Key, 'shift_r', None)):
                self._shift_down = False
            if isinstance(key, keyboard.KeyCode):
                vk = getattr(key, 'vk', None)
                if vk in self._q_vk_codes:
                    self._q_down = False

    def start(self) -> None:
        # Single listener tracks modifier and physical Q by virtual-key code
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()

    def join(self) -> None:
        if self._listener is not None:
            self._listener.join()
        if self._debug_listener is not None:
            self._debug_listener.join()






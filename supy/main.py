from __future__ import annotations

import sys
import time
from typing import Optional, Tuple
from pynput import mouse

from .capture import capture_fullscreen_to_file, capture_region_to_file
from .ocr import run_ocr_to_text
from .hotkey import GlobalHotkeyListener


_pending_crop_start: Optional[Tuple[int, int]] = None
_pending_crop_ts: float = 0.0
_pending_timeout_seconds: float = 12.0


def _on_hotkey() -> None:
    print("[supy] Hotkey detected: capturing full screen…")
    path = capture_fullscreen_to_file()
    print(f"[supy] Saved screenshot to: {path}")
    try:
        txt = run_ocr_to_text(path)
        print(f"[supy] OCR saved to: {txt}")
    except Exception as e:
        print(f"[supy] OCR failed: {e}")


def _on_hotkey_cropped() -> None:
    global _pending_crop_start, _pending_crop_ts
    try:
        controller = mouse.Controller()
        x, y = controller.position
    except Exception:
        print("[supy] Could not read mouse position; falling back to full-screen capture.")
        _on_hotkey()
        return

    now = time.monotonic()
    if _pending_crop_start is None or (now - _pending_crop_ts) > _pending_timeout_seconds:
        _pending_crop_start = (int(x), int(y))
        _pending_crop_ts = now
        print(f"[supy] Cropped step 1 set at ({_pending_crop_start[0]},{_pending_crop_start[1]}). Press Option+Shift+W again for bottom-right.")
        return

    x1, y1 = _pending_crop_start
    x2, y2 = int(x), int(y)
    left = min(x1, x2)
    top = min(y1, y2)
    right = max(x1, x2)
    bottom = max(y1, y2)
    width = max(0, right - left)
    height = max(0, bottom - top)

    print(f"[supy] Cropped step 2 at ({x2},{y2}). Capturing region (left={left}, top={top}, width={width}, height={height})…")
    path = capture_region_to_file(left, top, width, height)
    print(f"[supy] Saved cropped screenshot to: {path}")
    try:
        txt = run_ocr_to_text(path)
        print(f"[supy] OCR saved to: {txt}")
    except Exception as e:
        print(f"[supy] OCR failed: {e}")
    _pending_crop_start = None
    _pending_crop_ts = 0.0


def run() -> None:
    print("[supy] Running. Press Alt/Option + Shift + Q to capture a screenshot.")
    if sys.platform == 'darwin':
        print("[supy] macOS: If hotkey doesn't trigger, grant Accessibility to your terminal app.")
        print("[supy] macOS: If capture fails, grant Screen Recording permission as well.")
    print("[supy] Cropped capture: Alt/Option + Shift + W (two-press: set top-left, then bottom-right)")
    listener = GlobalHotkeyListener(on_trigger=_on_hotkey, debounce_seconds=0.8, on_trigger_cropped=_on_hotkey_cropped)
    listener.start()
    listener.join()


if __name__ == "__main__":
    run()






from __future__ import annotations

import sys
import time
from typing import Optional, Tuple
import threading
from pynput import mouse

from .capture import capture_fullscreen_to_file, capture_region_to_file
from .ocr import run_ocr_to_text
from .ai_analysis import analyze_text_with_ai
from .multimodal_analysis import analyze_image_with_ai
from .hotkey import GlobalHotkeyListener
from .signal import StatusDot


_pending_crop_start: Optional[Tuple[int, int]] = None
_pending_crop_ts: float = 0.0
_pending_timeout_seconds: float = 12.0
_status_dot: Optional[StatusDot] = None

# Toggle between local OCR + text analysis vs direct image analysis
USE_MULTIMODAL_GPT5 = True  # Set to False to use local OCR instead


def _set_done_then_idle(delay_seconds: float = 3.0) -> None:
    if _status_dot is None:
        return
    _status_dot.set_done()
    def _reset() -> None:
        if _status_dot is not None:
            _status_dot.set_idle()
    t = threading.Timer(delay_seconds, _reset)
    t.daemon = True
    t.start()


def _on_hotkey() -> None:
    print("[supy] Hotkey detected: capturing full screen…")
    path = capture_fullscreen_to_file()
    print(f"[supy] Saved screenshot to: {path}")
    
    try:
        if USE_MULTIMODAL_GPT5:
            print("[supy] Using multimodal GPT-5 (direct image analysis)")
            response = analyze_image_with_ai(path)
            print(f"[supy] Multimodal AI analysis saved to: {response}")
        else:
            print("[supy] Using local OCR + text analysis")
            txt = run_ocr_to_text(path)
            print(f"[supy] OCR saved to: {txt}")
            response = analyze_text_with_ai(txt)
            print(f"[supy] AI analysis saved to: {response}")
        
        _maybe_show_answer_label(response)
    except Exception as e:
        print(f"[supy] Analysis failed: {e}")
    else:
        _set_done_then_idle()


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
        if _status_dot is not None:
            _status_dot.set_pending_crop()
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
        if USE_MULTIMODAL_GPT5:
            print("[supy] Using multimodal GPT-5 (direct image analysis)")
            response = analyze_image_with_ai(path)
            print(f"[supy] Multimodal AI analysis saved to: {response}")
        else:
            print("[supy] Using local OCR + text analysis")
            txt = run_ocr_to_text(path)
            print(f"[supy] OCR saved to: {txt}")
            response = analyze_text_with_ai(txt)
            print(f"[supy] AI analysis saved to: {response}")
        
        _maybe_show_answer_label(response)
    except Exception as e:
        print(f"[supy] Analysis failed: {e}")
    
    _pending_crop_start = None
    _pending_crop_ts = 0.0
    _set_done_then_idle()


def _extract_answer_tag(text: str) -> Optional[str]:
    """Return inner text from the first <answer>...</answer> tag if present."""
    start_tag = "<answer>"
    end_tag = "</answer>"
    i = text.find(start_tag)
    j = text.find(end_tag, i + len(start_tag)) if i != -1 else -1
    if i != -1 and j != -1:
        inner = text[i + len(start_tag):j].strip()
        return inner if inner else None
    return None


def _maybe_show_answer_label(response_path) -> None:
    try:
        from pathlib import Path
        rp = Path(response_path)
        body = rp.read_text(encoding='utf-8')
    except Exception:
        return
    ans = _extract_answer_tag(body)
    if ans and _status_dot is not None:
        _status_dot.set_label(ans)


def run() -> None:
    print("[supy] Running. Press Alt/Option + Shift + Q to capture a screenshot.")
    if sys.platform == 'darwin':
        print("[supy] macOS: If hotkey doesn't trigger, grant Accessibility to your terminal app.")
        print("[supy] macOS: If capture fails, grant Screen Recording permission as well.")
    print("[supy] Cropped capture: Alt/Option + Shift + W (two-press: set top-left, then bottom-right)")
    global _status_dot
    _status_dot = StatusDot()
    listener = GlobalHotkeyListener(on_trigger=_on_hotkey, debounce_seconds=0.8, on_trigger_cropped=_on_hotkey_cropped)
    listener.start()
    if sys.platform == 'darwin':
        # Tk must run on the main thread on macOS
        _status_dot.set_idle()
        _status_dot.run_on_current_thread()
    else:
        _status_dot.start()
        _status_dot.set_idle()
        listener.join()


if __name__ == "__main__":
    run()






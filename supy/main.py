from __future__ import annotations

import sys
import sys

from .capture import capture_fullscreen_to_file
from .hotkey import GlobalHotkeyListener


def _on_hotkey() -> None:
    print("[supy] Hotkey detected: capturing full screen…")
    path = capture_fullscreen_to_file()
    print(f"[supy] Saved screenshot to: {path}")


def run() -> None:
    print("[supy] Running. Press Alt/Option + Shift + Q to capture a screenshot.")
    if sys.platform == 'darwin':
        print("[supy] macOS: If hotkey doesn't trigger, grant Accessibility to your terminal app.")
        print("[supy] macOS: If capture fails, grant Screen Recording permission as well.")
    listener = GlobalHotkeyListener(on_trigger=_on_hotkey, debounce_seconds=0.8)
    listener.start()
    listener.join()


if __name__ == "__main__":
    run()






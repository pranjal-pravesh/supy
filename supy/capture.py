from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from mss import mss
from mss.tools import to_png

from .utils.paths import screenshots_dir


def capture_fullscreen_to_file() -> Path:
    """Capture the primary monitor to a PNG file in data/ss and return the path."""
    output_dir = screenshots_dir()
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    out_path = output_dir / f"ss-{timestamp}.png"

    with mss() as sct:
        monitor = sct.monitors[1]
        raw = sct.grab(monitor)
        png_bytes = to_png(raw.rgb, raw.size)
        out_path.write_bytes(png_bytes)

    return out_path




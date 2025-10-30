from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    """Return the project root directory (repository root)."""
    # This file: <repo>/supy/utils/paths.py → parents[2] is <repo>
    return Path(__file__).resolve().parents[2]


def screenshots_dir() -> Path:
    """Return the screenshots directory under data/ss, creating it if missing."""
    root = project_root()
    target = root / "data" / "ss"
    target.mkdir(parents=True, exist_ok=True)
    return target







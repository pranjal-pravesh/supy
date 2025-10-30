from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    """Return the project root directory (where this file's ancestor is the repo root)."""
    return Path(__file__).resolve().parents[3]


def screenshots_dir() -> Path:
    """Return the screenshots directory under data/ss, creating it if missing."""
    root = project_root()
    target = root / "data" / "ss"
    target.mkdir(parents=True, exist_ok=True)
    return target







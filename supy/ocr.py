from __future__ import annotations

from pathlib import Path
from typing import List
import os

from PIL import Image
import pytesseract
from pytesseract import TesseractNotFoundError

# Allow overriding the tesseract binary via env var (e.g., /opt/homebrew/bin/tesseract)
_cmd = os.environ.get('SUPY_TESSERACT_CMD')
if _cmd:
    pytesseract.pytesseract.tesseract_cmd = _cmd


def run_ocr_to_text(image_path: Path) -> Path:
    """Run OCR on an image via Tesseract and save text to <image>.txt."""
    image_path = Path(image_path)
    img = Image.open(image_path)
    try:
        text = pytesseract.image_to_string(img)
    except TesseractNotFoundError as e:
        raise RuntimeError(
            "tesseract is not installed or not in PATH. On macOS: brew install tesseract.\n"
            "Optionally set SUPY_TESSERACT_CMD to the binary path (e.g., /opt/homebrew/bin/tesseract)."
        ) from e
    text_out = image_path.with_suffix('.txt')
    text_out.write_text(text, encoding='utf-8')
    return text_out



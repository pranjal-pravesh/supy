from __future__ import annotations

from pathlib import Path
from typing import List

from PIL import Image

_ocr_engine = None


def _get_ocr():
    """Lazy-load EasyOCR engine"""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            import easyocr
            # Initialize EasyOCR with English language
            _ocr_engine = easyocr.Reader(['en'], gpu=False)
        except ImportError as e:
            raise RuntimeError(
                "EasyOCR not available. Install with:\n"
                "  pip install easyocr"
            ) from e
    return _ocr_engine


def run_ocr_to_text(image_path: Path) -> Path:
    """Run OCR on an image via EasyOCR and save text to <image>.txt."""
    image_path = Path(image_path)
    
    # Run OCR with EasyOCR
    ocr = _get_ocr()
    result = ocr.readtext(str(image_path))
    
    # Extract and organize text from results
    text_blocks = []
    if result:
        # Sort by vertical position (top to bottom) for better reading order
        sorted_results = sorted(result, key=lambda x: x[0][0][1])  # Sort by top-left Y coordinate
        
        for detection in sorted_results:
            box = detection[0]  # Bounding box coordinates
            text = detection[1]  # Detected text
            confidence = detection[2]  # Confidence score
            
            if text.strip() and confidence > 0.5:  # Filter low-confidence results
                clean_text = text.strip()
                text_blocks.append(clean_text)
    
    # Join with newlines and add some basic formatting
    if text_blocks:
        # Group text blocks that might be on the same line
        formatted_lines = []
        current_line = ""
        
        for block in text_blocks:
            # If block looks like it continues a sentence (starts lowercase), join with space
            if (current_line and 
                len(block) > 0 and 
                block[0].islower() and 
                not current_line.endswith('.') and 
                not current_line.endswith('?') and 
                not current_line.endswith('!')):
                current_line += " " + block
            else:
                # Start new line
                if current_line:
                    formatted_lines.append(current_line)
                current_line = block
        
        # Add the last line
        if current_line:
            formatted_lines.append(current_line)
        
        text_content = "\n".join(formatted_lines)
    else:
        text_content = ""
    
    # Save to .txt file
    text_out = image_path.with_suffix('.txt')
    text_out.write_text(text_content, encoding='utf-8')
    
    return text_out



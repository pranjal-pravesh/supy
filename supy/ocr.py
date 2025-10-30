from __future__ import annotations

from pathlib import Path
from typing import List

from PIL import Image

_ocr_engine = None


def _get_ocr():
    """Lazy-load docTR OCR engine with highest accuracy models"""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from doctr.models import ocr_predictor
            # Use highest accuracy model combination
            _ocr_engine = ocr_predictor(
                det_arch="db_resnet50",        # High accuracy detection
                reco_arch="sar_resnet31",      # High accuracy recognition  
                pretrained=True
            )
        except ImportError as e:
            raise RuntimeError(
                "docTR not available. Install with:\n"
                "  pip install 'python-doctr[torch]' torch"
            ) from e
    return _ocr_engine


def run_ocr_to_text(image_path: Path) -> Path:
    """Run OCR on an image via docTR and save text to <image>.txt."""
    image_path = Path(image_path)
    
    # Load document and run OCR with docTR
    from doctr.io import DocumentFile
    
    doc = DocumentFile.from_images(str(image_path))
    ocr = _get_ocr()
    result = ocr(doc)
    
    # Extract text from docTR results
    text_lines = []
    export_data = result.export()
    
    if export_data and "pages" in export_data:
        for page in export_data["pages"]:
            if "blocks" in page:
                for block in page["blocks"]:
                    if "lines" in block:
                        for line in block["lines"]:
                            if "words" in line:
                                # Combine words in a line with spaces
                                line_text = " ".join([
                                    word["value"] for word in line["words"] 
                                    if word.get("confidence", 0) > 0.5  # Filter low confidence
                                ])
                                if line_text.strip():
                                    text_lines.append(line_text.strip())
    
    # Join lines with newlines
    text_content = "\n".join(text_lines) if text_lines else ""
    
    # Save to .txt file
    text_out = image_path.with_suffix('.txt')
    text_out.write_text(text_content, encoding='utf-8')
    
    return text_out



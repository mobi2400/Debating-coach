from __future__ import annotations

from io import BytesIO

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None


def ocr_available() -> bool:
    return requests is not None and Image is not None and pytesseract is not None


def extract_thumbnail_text(url: str, timeout: int = 15) -> str:
    if not ocr_available() or not str(url or "").strip():
        return ""

    try:
        response = requests.get(str(url).strip(), timeout=timeout)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        text = pytesseract.image_to_string(image)
        return " ".join(str(text).split()).strip()
    except Exception:
        return ""

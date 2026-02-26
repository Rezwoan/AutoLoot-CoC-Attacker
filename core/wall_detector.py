"""
core/wall_detector.py

OCR-based wall detection inside the CoC "All Upgradable" popup.

Uses **pytesseract** to read text from screenshots and locate the
word *Wall* so the bot can click on it.

Requires
--------
- Tesseract OCR engine installed on the system.
  Download: https://github.com/UB-Mannheim/tesseract/wiki
- pytesseract Python package (``pip install pytesseract``).
"""

import os
import re
import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pyautogui
import pytesseract
from PIL import Image

# ---------------------------------------------------------------------------
#  Tesseract path — auto-detect common Windows install location
# ---------------------------------------------------------------------------

_COMMON_TESS_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

# Also check if tesseract is on PATH
import shutil as _shutil
_tess_on_path = _shutil.which("tesseract")

_found = False
for _p in _COMMON_TESS_PATHS:
    if os.path.isfile(_p):
        pytesseract.pytesseract.tesseract_cmd = _p
        _found = True
        break

if not _found and _tess_on_path:
    pytesseract.pytesseract.tesseract_cmd = _tess_on_path


# ---------------------------------------------------------------------------
#  Low-level helpers
# ---------------------------------------------------------------------------

def _screenshot_to_gray(
    region: Optional[Tuple[int, int, int, int]] = None,
) -> np.ndarray:
    """Grab a (optionally region-cropped) screenshot as a grayscale array."""
    ss = pyautogui.screenshot(region=region)
    return cv2.cvtColor(np.array(ss), cv2.COLOR_RGB2GRAY)


def _preprocess_for_ocr(gray: np.ndarray) -> np.ndarray:
    """
    Sharpen and threshold the grayscale image for better OCR accuracy.

    Returns a clean binary image where text is black on white.
    """
    # up-scale small images for better recognition
    h, w = gray.shape[:2]
    if h < 300 or w < 400:
        gray = cv2.resize(gray, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    # adaptive threshold handles varying backgrounds
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15,
        C=8,
    )
    return binary


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def find_text_on_screen(
    target: str = "Wall",
    region: Optional[Tuple[int, int, int, int]] = None,
    confidence: int = 60,
) -> Optional[Tuple[int, int]]:
    """
    Search the screen (or a *region*) for *target* text using OCR.

    Parameters
    ----------
    target : str
        The text to look for (case-insensitive substring match).
    region : tuple, optional
        ``(left, top, width, height)`` — limit the OCR area.
    confidence : int
        Minimum pytesseract confidence (0-100) to accept a word.

    Returns
    -------
    (x, y) : tuple[int, int] | None
        Absolute screen coordinates of the text centre, or ``None``.
    """
    gray = _screenshot_to_gray(region)
    processed = _preprocess_for_ocr(gray)

    data = pytesseract.image_to_data(
        processed, output_type=pytesseract.Output.DICT
    )

    target_lower = target.lower()

    for i, word in enumerate(data["text"]):
        if not word or not word.strip():
            continue

        conf = int(data["conf"][i])
        if conf < confidence:
            continue

        if target_lower in word.strip().lower():
            # Calculate centre of bounding box
            bx = data["left"][i] + data["width"][i] // 2
            by = data["top"][i] + data["height"][i] // 2

            # Compensate for any up-scaling done in preprocessing
            h_orig, w_orig = gray.shape[:2]
            h_proc, w_proc = processed.shape[:2]
            scale_x = w_orig / w_proc
            scale_y = h_orig / h_proc
            bx = int(bx * scale_x)
            by = int(by * scale_y)

            # Convert to absolute screen coordinates
            if region:
                bx += region[0]
                by += region[1]

            return (bx, by)

    return None


def find_all_text(
    region: Optional[Tuple[int, int, int, int]] = None,
    confidence: int = 40,
) -> List[Dict]:
    """
    Return all recognised words from a screenshot region.

    Each item is a dict with keys:
    ``text``, ``conf``, ``x``, ``y``, ``w``, ``h``  (absolute coords).

    Useful for debugging / the Test tab.
    """
    gray = _screenshot_to_gray(region)
    processed = _preprocess_for_ocr(gray)

    data = pytesseract.image_to_data(
        processed, output_type=pytesseract.Output.DICT
    )

    h_orig, w_orig = gray.shape[:2]
    h_proc, w_proc = processed.shape[:2]
    sx = w_orig / w_proc
    sy = h_orig / h_proc

    words: List[Dict] = []
    for i, word in enumerate(data["text"]):
        if not word or not word.strip():
            continue
        conf = int(data["conf"][i])
        if conf < confidence:
            continue

        bx = int(data["left"][i] * sx)
        by = int(data["top"][i] * sy)
        bw = int(data["width"][i] * sx)
        bh = int(data["height"][i] * sy)

        if region:
            bx += region[0]
            by += region[1]

        words.append({
            "text": word.strip(),
            "conf": conf,
            "x": bx,
            "y": by,
            "w": bw,
            "h": bh,
        })

    return words


def scroll_and_find_wall(
    scroll_x: int,
    scroll_y: int,
    max_scrolls: int = 10,
    scroll_amount: int = -3,
    pause: float = 0.8,
) -> Optional[Tuple[int, int]]:
    """
    Scroll through the upgrade list and look for "Wall" text.

    Parameters
    ----------
    scroll_x, scroll_y : int
        Screen position to place the mouse while scrolling.
    max_scrolls : int
        Maximum number of scroll steps before giving up.
    scroll_amount : int
        Scroll delta per step (negative = scroll down).
    pause : float
        Seconds to wait after each scroll for the UI to settle.

    Returns
    -------
    (x, y) | None
        Absolute screen coordinates of the "Wall" text if found.
    """
    # First check without scrolling
    pos = find_text_on_screen("Wall")
    if pos:
        return pos

    pyautogui.moveTo(scroll_x, scroll_y, duration=0.1)

    for _ in range(max_scrolls):
        pyautogui.scroll(scroll_amount)
        time.sleep(pause)

        pos = find_text_on_screen("Wall")
        if pos:
            return pos

    return None

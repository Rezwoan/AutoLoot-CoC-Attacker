"""
core/wall_detector.py

Template-matching wall detection inside the CoC "All Upgradable" popup.

Uses **cv2.matchTemplate** (via ``core.detector``) to locate the
"Wall" entry on screen — far more reliable than OCR for CoC's
decorative game fonts.

The user captures a template image of the *Wall* text from the upgrade
list (via the Detection tab in the Setup Panel).  That template is then
matched against a full-screen screenshot to find the Wall entry.
"""

import os
import time
from typing import Optional, Tuple

import pyautogui

from core.detector import find_on_screen


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def find_wall_on_screen(
    template_path: str,
    confidence: float = 0.75,
) -> Optional[Tuple[int, int]]:
    """
    Search the full screen for the "Wall" template image.

    Parameters
    ----------
    template_path : str
        Path to the captured template image (e.g. ``img/wall_text.png``).
    confidence : float
        Minimum match score (0-1).  Default 0.75 is forgiving enough
        for slight UI variations while avoiding false positives.

    Returns
    -------
    (x, y) | None
        Screen coordinates of the centre of the Wall entry, or ``None``.
    """
    if not os.path.isfile(template_path):
        return None
    return find_on_screen(template_path, confidence)


def scroll_and_find_wall(
    template_path: str,
    scroll_x: int,
    scroll_y: int,
    max_scrolls: int = 10,
    scroll_amount: int = -3,
    pause: float = 0.8,
    confidence: float = 0.75,
) -> Optional[Tuple[int, int]]:
    """
    Scroll through the upgrade list and look for the Wall template.

    Parameters
    ----------
    template_path : str
        Path to the captured "Wall" template image.
    scroll_x, scroll_y : int
        Screen position to place the mouse while scrolling.
    max_scrolls : int
        Maximum number of scroll steps before giving up.
    scroll_amount : int
        Scroll delta per step (negative = scroll down).
    pause : float
        Seconds to wait after each scroll for the UI to settle.
    confidence : float
        Minimum template-match score (0-1).

    Returns
    -------
    (x, y) | None
        Screen coordinates of the "Wall" entry if found.
    """
    if not os.path.isfile(template_path):
        return None

    # First check without scrolling
    pos = find_on_screen(template_path, confidence)
    if pos:
        return pos

    pyautogui.moveTo(scroll_x, scroll_y, duration=0.1)

    for _ in range(max_scrolls):
        pyautogui.scroll(scroll_amount)
        time.sleep(pause)

        pos = find_on_screen(template_path, confidence)
        if pos:
            return pos

    return None

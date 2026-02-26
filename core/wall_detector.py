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

from core.clicker import drag_scroll
from core.detector import find_on_screen


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def find_wall_on_screen(
    template_path: str,
    confidence: float = 0.90,
) -> Optional[Tuple[int, int]]:
    """
    Search the full screen for the "Wall" template image.

    Parameters
    ----------
    template_path : str
        Path to the captured template image (e.g. ``img/wall_text.png``).
    confidence : float
        Minimum match score (0-1).  Default 0.90 avoids false positives
        while still matching the Wall entry reliably.

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
    drag_distance: int = 200,
    pause: float = 0.8,
    confidence: float = 0.90,
) -> Optional[Tuple[int, int]]:
    """
    Scroll through the upgrade list and look for the Wall template.

    Uses **click-hold-drag-release** (not mouse wheel) so it works in
    emulators.  Starts at *(scroll_x, scroll_y)*, drags upward by
    *drag_distance* pixels each step to scroll the list down.

    Parameters
    ----------
    template_path : str
        Path to the captured "Wall" template image.
    scroll_x, scroll_y : int
        Screen position where the drag starts (inside the upgrade list).
    max_scrolls : int
        Maximum number of drag-scroll steps before giving up.
    drag_distance : int
        How many pixels to drag upward per step (higher = faster scroll).
    pause : float
        Seconds to wait after each drag for the UI to settle.
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

    for _ in range(max_scrolls):
        drag_scroll(scroll_x, scroll_y, distance=drag_distance)
        time.sleep(pause)

        pos = find_on_screen(template_path, confidence)
        if pos:
            return pos

    return None

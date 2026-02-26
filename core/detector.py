"""
core/detector.py

Template matching for dynamic UI elements (Next button, Return Home, 50 %).

Uses ``cv2.matchTemplate`` on a full-screen screenshot — no hardcoded
regions, works at any resolution.
"""

import os
import time
from typing import Optional, Tuple

import cv2
import numpy as np
import pyautogui


def find_on_screen(
    template_path: str,
    confidence: float = 0.8,
) -> Optional[Tuple[int, int]]:
    """
    Search the **full screen** for *template_path*.

    Returns the *(x, y)* **centre** of the best match when the match
    score ≥ *confidence*, otherwise ``None``.
    """
    if not os.path.isfile(template_path):
        return None

    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        return None

    screenshot = pyautogui.screenshot()
    screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)

    th, tw = template.shape[:2]
    sh, sw = screen_gray.shape[:2]
    if th > sh or tw > sw:
        return None

    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= confidence:
        return (max_loc[0] + tw // 2, max_loc[1] + th // 2)
    return None


def find_in_region(
    template_path: str,
    region: Tuple[int, int, int, int],
    confidence: float = 0.8,
) -> Optional[Tuple[int, int]]:
    """
    Search within a screen *region* ``(left, top, width, height)``.

    Returns **absolute** *(x, y)* centre of the best match, or ``None``.
    """
    if not os.path.isfile(template_path):
        return None

    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template is None:
        return None

    try:
        screenshot = pyautogui.screenshot(region=region)
    except Exception:
        return None

    screen_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)

    th, tw = template.shape[:2]
    sh, sw = screen_gray.shape[:2]
    if th > sh or tw > sw:
        return None

    result = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= confidence:
        cx = max_loc[0] + tw // 2 + region[0]
        cy = max_loc[1] + th // 2 + region[1]
        return (cx, cy)
    return None


def is_visible(
    template_path: str,
    confidence: float = 0.8,
) -> bool:
    """Return ``True`` if *template_path* is visible on screen."""
    return find_on_screen(template_path, confidence) is not None


def wait_for(
    template_path: str,
    timeout: float = 60.0,
    interval: float = 0.5,
    confidence: float = 0.8,
) -> Optional[Tuple[int, int]]:
    """
    Poll until *template_path* appears on screen (or *timeout* elapses).

    Returns *(x, y)* centre on success, ``None`` on timeout.
    """
    end = time.time() + timeout
    while time.time() < end:
        pos = find_on_screen(template_path, confidence)
        if pos:
            return pos
        time.sleep(interval)
    return None

"""
core/screen.py

Screen utilities — size detection and coordinate helpers.
"""

from typing import Tuple

import pyautogui


def get_screen_size() -> Tuple[int, int]:
    """Return *(width, height)* of the primary monitor."""
    return pyautogui.size()

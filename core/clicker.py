"""
core/clicker.py

Thin wrapper around pyautogui mouse operations.
"""

import time

import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def click(
    x: int,
    y: int,
    duration: float = 0.1,
    delay: float = 0.05,
) -> None:
    """Move to *(x, y)*, left-click, then sleep *delay* seconds."""
    pyautogui.moveTo(x, y, duration=duration)
    pyautogui.click()
    time.sleep(delay)


def scroll_at(
    x: int,
    y: int,
    amount: int,
    duration: float = 0.1,
) -> None:
    """Move to *(x, y)* and scroll by *amount* (negative = down)."""
    pyautogui.moveTo(x, y, duration=duration)
    pyautogui.scroll(amount)


def drag_scroll(
    x: int,
    y: int,
    distance: int = 200,
    duration: float = 0.4,
) -> None:
    """
    Scroll by click-hold-drag-release (for emulators that ignore mouse wheel).

    Clicks at *(x, y)*, holds, drags **upward** by *distance* pixels,
    then releases.  Positive *distance* scrolls the list **down**
    (finger moves up).
    """
    pyautogui.moveTo(x, y, duration=0.05)
    pyautogui.mouseDown()
    time.sleep(0.05)
    pyautogui.moveTo(x, y - distance, duration=duration)
    pyautogui.mouseUp()
    time.sleep(0.05)

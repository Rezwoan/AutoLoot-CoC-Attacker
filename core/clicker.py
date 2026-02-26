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

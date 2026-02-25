import time
import sys
import os
from typing import Tuple, Optional

import pyautogui

# On Windows, this lets us play a beep
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# Try to import the specific "not found" exception so we don't log it as an error
try:
    from pyautogui import ImageNotFoundException
except Exception:
    class ImageNotFoundException(Exception):
        pass

# Try OpenCV + NumPy for advanced template matching (for the "5" image)
try:
    import cv2
    HAS_OPENCV = True
except Exception:
    HAS_OPENCV = False

try:
    import numpy as np
    HAS_NUMPY = True
except Exception:
    HAS_NUMPY = False

# ============================================================
#  Module-level root path (project root, one level above core/)
# ============================================================

_MODULE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ============================================================
#  Screen geometry
# ============================================================

SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1200

# Used to define bottom band for NEXT detection
BOTTOM_UPPER = (1075, 1040)

# ============================================================
#  Image template configuration
# ============================================================

NEXT_BUTTON_TEMPLATE_PATH = os.path.join(_MODULE_DIR, "next.png")
FIVE_TEMPLATE_PATH        = os.path.join(_MODULE_DIR, "five.png")

POLL_INTERVAL_SECONDS = 0.5

DETECTION_CONFIDENCE_NEXT = 0.8
FIFTY_DETECTION_THRESHOLD = 0.70  # threshold for "5" match strength

FIVE_TEMPLATE = None
FIVE_TEMPLATE_SHAPE = None
_warned_five_disabled = False

# ============================================================
#  Regions
# ============================================================

def compute_next_button_search_region() -> Tuple[int, int, int, int]:
    """
    Region for NEXT button: bottom band of the screen.
    """
    padding_top = 250
    region_top = max(0, BOTTOM_UPPER[1] - padding_top)
    region_left = 0
    region_width = SCREEN_WIDTH
    region_height = SCREEN_HEIGHT - region_top
    return region_left, region_top, region_width, region_height


def compute_five_search_region() -> Tuple[int, int, int, int]:
    """
    Region for the '5' image, using the 4 points you provided:

        1 = (1799, 1002)
        2 = (1833, 999)
        3 = (1833, 1040)
        4 = (1799, 1043)

    We'll build a rectangle that covers that square region.
    """
    x_coords = [1799, 1833, 1833, 1799]
    y_coords = [1002, 999, 1040, 1043]

    left = min(x_coords)
    right = max(x_coords)
    top = min(y_coords)
    bottom = max(y_coords)

    width = (right - left) + 1
    height = (bottom - top) + 1

    return left, top, width, height

# ============================================================
#  Sound helpers (used only in monitor loop, not in library calls)
# ============================================================

def play_next_found_sound():
    """
    Single beep when NEXT button is detected.
    """
    if not HAS_WINSOUND:
        return
    try:
        winsound.Beep(1200, 300)
    except Exception:
        try:
            winsound.MessageBeep()
        except Exception:
            pass


def play_five_found_sound():
    """
    Double beep when '5' (50%+) is detected.
    """
    if not HAS_WINSOUND:
        return
    try:
        winsound.Beep(1500, 200)
        time.sleep(0.1)
        winsound.Beep(1500, 200)
    except Exception:
        try:
            winsound.MessageBeep()
            time.sleep(0.1)
            winsound.MessageBeep()
        except Exception:
            pass

# ============================================================
#  NEXT button detection
# ============================================================

def next_button_present(region: Optional[Tuple[int, int, int, int]] = None) -> bool:
    """
    Detect the NEXT button via pyautogui.locateOnScreen.
    Returns True if found, False otherwise.
    No printing / sound here: safe to call from other scripts.
    """
    if region is None:
        region = compute_next_button_search_region()

    if not os.path.exists(NEXT_BUTTON_TEMPLATE_PATH):
        # For library usage, just return False if image missing
        return False

    kwargs = {"region": region}
    if HAS_OPENCV:
        kwargs["confidence"] = DETECTION_CONFIDENCE_NEXT

    try:
        loc = pyautogui.locateOnScreen(NEXT_BUTTON_TEMPLATE_PATH, **kwargs)
        return loc is not None
    except ImageNotFoundException:
        return False
    except TypeError:
        # retry without confidence
        try:
            loc = pyautogui.locateOnScreen(NEXT_BUTTON_TEMPLATE_PATH, region=region)
            return loc is not None
        except ImageNotFoundException:
            return False
    except Exception:
        # For library usage, swallow unexpected errors and just say "not found"
        return False

# ============================================================
#  FIVE detection (OpenCV)
# ============================================================

def _ensure_five_template_loaded() -> bool:
    """
    Load five.png as grayscale template for cv2.matchTemplate.
    """
    global FIVE_TEMPLATE, FIVE_TEMPLATE_SHAPE, _warned_five_disabled

    if FIVE_TEMPLATE is not None:
        return True

    if not (HAS_OPENCV and HAS_NUMPY):
        if not _warned_five_disabled:
            print("[WARN] '5' detection disabled (OpenCV/NumPy missing).")
            _warned_five_disabled = True
        return False

    if not os.path.exists(FIVE_TEMPLATE_PATH):
        print(f"[ERROR] five.png missing: {FIVE_TEMPLATE_PATH}")
        return False

    template = cv2.imread(FIVE_TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
    if template is None:
        print("[ERROR] Failed loading five.png")
        return False

    FIVE_TEMPLATE = template
    FIVE_TEMPLATE_SHAPE = template.shape
    return True


def fifty_percent_reached(region: Optional[Tuple[int, int, int, int]] = None) -> bool:
    """
    Use cv2.matchTemplate to detect five.png in the small fixed region
    around the % text.

    Returns True if match score >= FIFTY_DETECTION_THRESHOLD.
    No prints / sounds here (library-safe).
    """
    if region is None:
        region = compute_five_search_region()

    if not _ensure_five_template_loaded():
        return False

    x, y, w, h = region
    try:
        screenshot = pyautogui.screenshot(region=(x, y, w, h))
    except Exception:
        return False

    try:
        img_rgb = np.array(screenshot)
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    except Exception:
        return False

    try:
        res = cv2.matchTemplate(img_gray, FIVE_TEMPLATE, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
    except Exception:
        return False

    return max_val >= FIFTY_DETECTION_THRESHOLD

# ============================================================
#  PUBLIC API: use this from other scripts
# ============================================================

def get_game_status() -> dict:
    """
    Quick status check for external scripts.

    Returns a dict like:
        {
            "next_button": True/False,   # is NEXT visible (base found)?
            "fifty_percent": True/False  # is '5' in % area (>=50% destruction)?
        }

    No printing and no sounds.
    """
    next_region = compute_next_button_search_region()
    five_region = compute_five_search_region()

    has_next = next_button_present(next_region)
    has_five = fifty_percent_reached(five_region)

    return {
        "next_button": has_next,
        "fifty_percent": has_five,
    }

# ============================================================
#  Monitor loop (for running this file directly)
# ============================================================

def monitor_screen():
    """
    CLI monitor: prints states and plays sounds.
    This is only used when running image_recognition.py directly.
    """
    next_region = compute_next_button_search_region()
    five_region = compute_five_search_region()

    print(f"[INFO] Screen size: {pyautogui.size()}")
    print(f"[INFO] NEXT region: {next_region}")
    print(f"[INFO] 5 region:    {five_region}")
    print("[INFO] Monitoring started. Press CTRL+C to stop.\n")

    last_next = None
    last_five = None

    while True:
        # NEXT button
        found_next = next_button_present(next_region)
        if found_next != last_next:
            if found_next:
                print("[STATE] NEXT button detected -> Base found.")
                play_next_found_sound()
            else:
                print("[STATE] NEXT button not detected -> Searching...")
            last_next = found_next

        # 5 detection (50%+ destruction)
        found_five = fifty_percent_reached(five_region)
        if found_five != last_five:
            if found_five:
                print("[STATE] 5 detected in % area -> >= 50% destruction.")
                play_five_found_sound()
            else:
                print("[STATE] 5 not detected in % area.")
            last_five = found_five

        time.sleep(POLL_INTERVAL_SECONDS)

# ============================================================

def main():
    pyautogui.FAILSAFE = True
    try:
        _ = pyautogui.size()
    except Exception:
        print("[ERROR] pyautogui failure")
        sys.exit(1)

    try:
        monitor_screen()
    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()

import os
import time
from typing import Optional, Tuple

import pyautogui

# Optional OCR support for text detection of "Wall"
try:
    from PIL import Image  # noqa: F401
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None  # type: ignore


# ============================================
#  PyAutoGUI Global Settings
# ============================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


# ============================================
#  Screen & Upgrade UI Geometry
# ============================================

# Button to open the "All upgradable" list
ALL_UPGRADABLE_BUTTON: Tuple[int, int] = (878, 30)

# Upgradable window bounding box (corners you provided)
UPGRADABLE_TOP_LEFT: Tuple[int, int] = (656, 140)
UPGRADABLE_TOP_RIGHT: Tuple[int, int] = (1296, 146)
UPGRADABLE_BOTTOM_RIGHT: Tuple[int, int] = (1301, 761)
UPGRADABLE_BOTTOM_LEFT: Tuple[int, int] = (659, 761)

UPGRADABLE_REGION = (
    UPGRADABLE_TOP_LEFT[0],
    UPGRADABLE_TOP_LEFT[1],
    UPGRADABLE_BOTTOM_RIGHT[0] - UPGRADABLE_TOP_LEFT[0],
    UPGRADABLE_BOTTOM_RIGHT[1] - UPGRADABLE_TOP_LEFT[1],
)

# Buttons on the wall upgrade UI
SELECT_MULTIPLE_WALLS: Tuple[int, int] = (963, 944)
UPGRADE_WITH_GOLD: Tuple[int, int] = (1128, 949)
UPGRADE_WITH_ELIXIR: Tuple[int, int] = (1301, 969)
UPGRADE_OKAY_BUTTON: Tuple[int, int] = (1161, 747)


# ============================================
#  Image paths
# ============================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(SCRIPT_DIR, "img")

WALL_IMAGE_NAME = "Wall.png"

# Prefer img/Wall.png; fall back to script folder if not there
WALL_IMAGE_PATH = os.path.join(IMG_DIR, WALL_IMAGE_NAME)
if not os.path.isfile(WALL_IMAGE_PATH):
    alt_path = os.path.join(SCRIPT_DIR, WALL_IMAGE_NAME)
    if os.path.isfile(alt_path):
        WALL_IMAGE_PATH = alt_path

WALL_IMAGE_AVAILABLE = os.path.isfile(WALL_IMAGE_PATH)
if not WALL_IMAGE_AVAILABLE:
    print(
        f"[WARN] '{WALL_IMAGE_NAME}' not found in 'img/' or script folder. "
        f"Image-based Wall detection will NOT work."
    )

if not OCR_AVAILABLE:
    print(
        "[WARN] OCR libraries (Pillow + pytesseract) not available. "
        "Text-based Wall detection will be skipped."
    )


# ============================================
#  Tunable parameters
# ============================================

NUM_WALLS_PER_GOLD_UPGRADE = 3       # how many walls to select for gold upgrade
NUM_WALLS_PER_ELIXIR_UPGRADE = 3     # how many walls to select for elixir upgrade

MAX_WALL_SCROLL_ATTEMPTS = 25        # how many scroll 'ticks' to look for 'Wall'
SCROLL_AMOUNT_PER_TICK = -350        # negative scroll = scroll DOWN
SCROLL_DELAY = 0.40                  # pause after each scroll

OCR_MIN_CONFIDENCE = 40.0            # minimal tesseract confidence to accept 'Wall'


Point = Tuple[int, int]


# ============================================
#  Utility: Mouse helper
# ============================================

def move_and_click(
    x: int,
    y: int,
    move_duration: float = 0.15,
    post_delay: float = 0.10
) -> None:
    """
    Move the mouse to (x, y), click, then sleep for post_delay seconds.
    """
    pyautogui.moveTo(x, y, duration=move_duration)
    pyautogui.click()
    time.sleep(post_delay)


# ============================================
#  Utility: Wall item location helpers
# ============================================

def locate_wall_by_image(confidence: float = 0.80) -> Optional[Point]:
    """
    Try to find the 'Wall' text inside the upgradables window using Wall.png.

    Returns (x, y) of the center if found, else None.
    """
    if not WALL_IMAGE_AVAILABLE:
        return None

    try:
        box = pyautogui.locateOnScreen(
            WALL_IMAGE_PATH,
            confidence=confidence,
            region=UPGRADABLE_REGION,
            grayscale=True,
        )
    except Exception as e:
        print(f"[WARN] Error locating Wall.png: {e}")
        return None

    if not box:
        return None

    center = pyautogui.center(box)
    return center.x, center.y


def locate_wall_by_text() -> Optional[Point]:
    """
    Use OCR to scan the upgradables region and find any word containing 'wall'.

    Returns (x, y) of the center of that word if found; otherwise None.
    """
    if not OCR_AVAILABLE:
        return None

    # Take screenshot of the upgradable list region
    try:
        screenshot = pyautogui.screenshot(region=UPGRADABLE_REGION)
    except Exception as e:
        print(f"[WARN] Error taking screenshot for OCR: {e}")
        return None

    try:
        data = pytesseract.image_to_data(
            screenshot,
            output_type=pytesseract.Output.DICT
        )
    except Exception as e:
        print(f"[WARN] Error during OCR (pytesseract): {e}")
        return None

    region_x, region_y, _, _ = UPGRADABLE_REGION

    best_match: Optional[Point] = None
    best_conf = -1.0

    n_boxes = len(data.get("text", []))
    for i in range(n_boxes):
        text = data["text"][i]
        if not text:
            continue

        if "wall" not in text.lower():
            continue

        # Tesseract conf is a string; parse to float
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1.0

        if conf < OCR_MIN_CONFIDENCE:
            continue

        left = data["left"][i]
        top = data["top"][i]
        width = data["width"][i]
        height = data["height"][i]

        cx = region_x + left + width / 2
        cy = region_y + top + height / 2

        if conf > best_conf:
            best_conf = conf
            best_match = (int(cx), int(cy))

    if best_match:
        print(f"[OCR] Found 'Wall' via text at {best_match} (conf={best_conf:.1f}).")
    return best_match


def find_and_click_wall_entry(max_scrolls: int = MAX_WALL_SCROLL_ATTEMPTS) -> bool:
    """
    Scrolls through the upgradables window, trying to find the 'Wall' entry.

    After each scroll:
      - Try image detection (Wall.png) inside UPGRADABLE_REGION
      - Then try OCR text detection for 'Wall'

    Once found, clicks on it and returns True.
    If not found after max_scrolls scroll steps, returns False.
    """
    center_x = UPGRADABLE_TOP_LEFT[0] + (UPGRADABLE_BOTTOM_RIGHT[0] - UPGRADABLE_TOP_LEFT[0]) // 2
    center_y = UPGRADABLE_TOP_LEFT[1] + (UPGRADABLE_BOTTOM_RIGHT[1] - UPGRADABLE_TOP_LEFT[1]) // 2

    def _try_find_once() -> Optional[Point]:
        # 1) Try image detection first
        pos = locate_wall_by_image(confidence=0.95)
        if pos:
            print("[UPGRADE] Found 'Wall' via image detection.")
            return pos

        # 2) If that fails, try OCR text detection
        pos = locate_wall_by_text()
        if pos:
            print("[UPGRADE] Found 'Wall' via OCR text detection.")
            return pos

        return None

    # Check once before any scrolling
    pos = _try_find_once()
    if pos:
        move_and_click(pos[0], pos[1], move_duration=0.18, post_delay=0.40)
        return True

    # Scroll & search
    for i in range(max_scrolls):
        # Move mouse into the list window and scroll
        pyautogui.moveTo(center_x, center_y, duration=0.10)
        pyautogui.scroll(SCROLL_AMOUNT_PER_TICK)
        time.sleep(SCROLL_DELAY)

        pos = _try_find_once()
        if pos:
            print(f"[UPGRADE] Found 'Wall' after scroll {i + 1}.")
            move_and_click(pos[0], pos[1], move_duration=0.18, post_delay=0.40)
            return True

    print("[UPGRADE] Could not find 'Wall' entry after scrolling.")
    return False


# ============================================
#  High-level upgrade helpers
# ============================================

def open_upgradables_window() -> None:
    """
    Clicks the All Upgradables button and waits a bit for the window to appear.
    """
    print("[UPGRADE] Opening 'All upgradable' window...")
    move_and_click(ALL_UPGRADABLE_BUTTON[0], ALL_UPGRADABLE_BUTTON[1],
                   move_duration=0.18, post_delay=0.7)


def select_multiple_walls(count: int) -> None:
    """
    Clicks the 'Select multiple walls' button 'count' times to select that many walls.
    """
    if count <= 0:
        return

    print(f"[UPGRADE] Selecting {count} wall(s) using the 'Select multiple walls' button...")
    for i in range(count):
        move_and_click(SELECT_MULTIPLE_WALLS[0], SELECT_MULTIPLE_WALLS[1],
                       move_duration=0.16, post_delay=0.28)
        print(f"[UPGRADE]   -> Selected wall #{i + 1}")


def confirm_upgrade() -> None:
    """
    Clicks the OKAY button to confirm the wall upgrade.
    """
    print("[UPGRADE] Confirming upgrade (OKAY button)...")
    move_and_click(UPGRADE_OKAY_BUTTON[0], UPGRADE_OKAY_BUTTON[1],
                   move_duration=0.18, post_delay=1.5)


def upgrade_walls_with_gold(num_walls: int = NUM_WALLS_PER_GOLD_UPGRADE) -> bool:
    """
    Opens the upgradables window, finds the Wall entry (image + OCR),
    selects num_walls walls, and upgrades them with GOLD.

    Returns True if we *think* the upgrade happened, False if we could not
    locate the wall entry (probably no walls left).
    """
    print("[UPGRADE] Starting GOLD wall upgrade...")
    open_upgradables_window()

    if not find_and_click_wall_entry():
        print("[UPGRADE] No 'Wall' entry found for GOLD upgrade. Maybe no walls left.")
        return False

    time.sleep(0.8)
    select_multiple_walls(num_walls)

    print("[UPGRADE] Clicking 'Upgrade with GOLD' button...")
    move_and_click(UPGRADE_WITH_GOLD[0], UPGRADE_WITH_GOLD[1],
                   move_duration=0.18, post_delay=0.6)

    confirm_upgrade()
    print("[UPGRADE] GOLD wall upgrade sequence finished.")
    return True


def upgrade_walls_with_elixir(num_walls: int = NUM_WALLS_PER_ELIXIR_UPGRADE) -> bool:
    """
    Opens the upgradables window, finds the Wall entry (image + OCR),
    selects num_walls walls, and upgrades them with ELIXIR.

    Returns True if we *think* the upgrade happened, False if we could not
    locate the wall entry (probably no walls left).
    """
    print("[UPGRADE] Starting ELIXIR wall upgrade...")
    open_upgradables_window()

    if not find_and_click_wall_entry():
        print("[UPGRADE] No 'Wall' entry found for ELIXIR upgrade. Maybe no walls left.")
        return False

    time.sleep(0.8)
    select_multiple_walls(num_walls)

    print("[UPGRADE] Clicking 'Upgrade with ELIXIR' button...")
    move_and_click(UPGRADE_WITH_ELIXIR[0], UPGRADE_WITH_ELIXIR[1],
                   move_duration=0.18, post_delay=0.6)

    confirm_upgrade()
    print("[UPGRADE] ELIXIR wall upgrade sequence finished.")
    return True


def upgrade_walls_full_cycle(
    gold_walls: int = NUM_WALLS_PER_GOLD_UPGRADE,
    elixir_walls: int = NUM_WALLS_PER_ELIXIR_UPGRADE
) -> Tuple[bool, bool]:
    """
    Performs one full upgrade cycle:
      - First upgrades 'gold_walls' walls with GOLD
      - Then upgrades 'elixir_walls' walls with ELIXIR

    Returns (gold_success, elixir_success).
    """
    print("\n========== WALL UPGRADE FULL CYCLE ==========")

    gold_success = upgrade_walls_with_gold(num_walls=gold_walls)
    time.sleep(2.0)
    elixir_success = upgrade_walls_with_elixir(num_walls=elixir_walls)

    print(f"[UPGRADE] Full cycle finished. GOLD success={gold_success}, "
          f"ELIXIR success={elixir_success}")
    return gold_success, elixir_success


def main() -> None:
    """
    Example entry point:
      - waits 5 seconds so you can focus the CoC window,
      - then runs a single GOLD+ELIXIR wall upgrade cycle.

    In your real automation, you will typically import this module and call
    `upgrade_walls_full_cycle()` after your auto-loot / auto-attack step.
    """
    print(
        "[INFO] wall_upgrade.py will automatically search for 'Wall' using "
        "both image and OCR and try to upgrade walls with GOLD and ELIXIR."
    )
    print("[INFO] Starting in 5 seconds... switch to CoC window now.")
    time.sleep(5.0)

    upgrade_walls_full_cycle()


if __name__ == "__main__":
    main()

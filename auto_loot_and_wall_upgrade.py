import os
import time
from typing import List, Tuple, Optional

import pyautogui

from imageRec import get_game_status
from location_cache import load_locations, save_locations


# ============================================
#  PyAutoGUI Global Settings
# ============================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

Point = Tuple[int, int]


# ============================================
#  Screen & Geometry (Attack / Battle)
# ============================================

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1200

# Battlefield edges for deployments
LEFT_LEFT    = (181, 592)
LEFT_BOTTOM  = (823, 1075)
RIGHT_BOTTOM = (1156, 1075)
RIGHT_RIGHT  = (1787, 590)
RIGHT_UP     = (1070, 60)
LEFT_UP      = (878, 70)

# Bottom bar search region (for troops/spells/heroes/siege)
# 1 = (476,1087), 2 = (473,1192), 3 = (1435,1189), 4 = (1433,1086)
BAR_LEFT   = 473
BAR_TOP    = 1086
BAR_RIGHT  = 1435
BAR_BOTTOM = 1192
BAR_WIDTH  = BAR_RIGHT - BAR_LEFT     # 962
BAR_HEIGHT = BAR_BOTTOM - BAR_TOP     # 106
BAR_REGION = (BAR_LEFT, BAR_TOP, BAR_WIDTH, BAR_HEIGHT)


# ============================================
#  Buttons (fixed screen UI)
# ============================================

ATTACK_MENU_BUTTON = (126, 1092)   # Home screen attack button
FIND_MATCH_BUTTON  = (301, 847)    # "Find a Match" in the attack menu
ATTACK_BUTTON      = (1646, 988)   # Troop selection Attack button

NEXT_BUTTON        = (1780, 988)   # Used only for detection via imageRec

SURRENDER_BUTTON   = (117, 1021)
CONFIRM_OK_BUTTON  = (1170, 763)
RETURN_HOME_BUTTON = (945, 1025)


# ============================================
#  Paths & image names
# ============================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR    = os.path.join(SCRIPT_DIR, "img")

# ReturnHome.png is in the ROOT folder (alongside five.png)
RETURN_HOME_IMAGE_NAME = "ReturnHome.png"
RETURN_HOME_IMAGE_PATH = os.path.join(SCRIPT_DIR, RETURN_HOME_IMAGE_NAME)
RETURN_HOME_IMAGE_AVAILABLE = os.path.isfile(RETURN_HOME_IMAGE_PATH)
if not RETURN_HOME_IMAGE_AVAILABLE:
    print(f"[WARN] '{RETURN_HOME_IMAGE_NAME}' not found in script folder. "
          f"Early battle end detection via image will be disabled.")

# Image names inside img/ for bar buttons
BUTTON_IMAGES = {
    "valk":        "VALKARIE.png",
    "siege":       "SIEGE.png",
    "earthquake":  "EARTHQUAKE.png",
    "hero_king":   "HERO_KING.png",       # Hero 1
    "hero_champ":  "HERO_CHAMPION.png",   # Hero 2
    "hero_minion": "HERO_MINION.png",     # Hero 3
    "hero_warden": "HERO_WARDEN.png",     # Hero 4 (warden)
}

# Optional fallback positions if detection fails completely
BUTTON_FALLBACKS = {
    "valk":        (520, 1140),
    "siege":       (617, 1132),
    "earthquake":  (888, 1142),
    "hero_king":   (711, 1136),
    "hero_champ":  (783, 1146),
    "hero_minion": (868, 1145),
    "hero_warden": (950, 1145),
}


# ============================================
#  Location cache (loaded/saved via location_cache.py)
# ============================================

LOCATION_CACHE: dict = {}
CACHE_MODE = "use"  # "use" or "update"
# structure:
# {
#   "buttons": {
#       "valk": [x,y],
#       "siege": [x,y],
#       ...
#   },
#   "valk_positions": [[x,y], [x,y], ...]
# }

_missing_image_warned = set()  # avoid spamming warnings per image


def init_location_cache_mode():
    """
    Load locations_cache.json and ask user whether to use it or update it.
    """
    global LOCATION_CACHE, CACHE_MODE

    data = load_locations()
    if not isinstance(data, dict):
        data = {}

    data.setdefault("buttons", {})
    data.setdefault("valk_positions", None)

    LOCATION_CACHE = data

    if LOCATION_CACHE.get("buttons") or LOCATION_CACHE.get("valk_positions"):
        choice = input(
            "Use saved button/valk locations from cache file? "
            "[Y = use saved, anything else = re-detect/update]: "
        ).strip().lower()
        if choice == "y":
            CACHE_MODE = "use"
            print("[INFO] Using cached locations from file.")
        else:
            CACHE_MODE = "update"
            print("[INFO] Will update cache: buttons/valk positions will be re-detected.")
    else:
        CACHE_MODE = "update"
        print("[INFO] No cached locations found. Will detect and create cache.")


def save_location_cache():
    """Save LOCATION_CACHE dict to JSON file."""
    save_locations(LOCATION_CACHE)


# ============================================
#  Troop / Spell target positions on battlefield
# ============================================

LEFT_EARTH   = (635, 567)   # 3 quakes
RIGHT_EARTH  = (1245, 581)  # 4 quakes
BUTTON_EARTH = (951, 783)   # 4 quakes


# ============================================
#  Utility: Mouse helper
# ============================================

def move_and_click(x: int, y: int, move_duration: float = 0.1, post_delay: float = 0.05):
    pyautogui.moveTo(x, y, duration=move_duration)
    pyautogui.click()
    time.sleep(post_delay)


# ============================================
#  Utility: Locate button on bottom bar (limited region)
# ============================================

def locate_button_center(
    key: str,
    confidence: float = 0.8,
    max_tries: int = 5,
    retry_delay: float = 0.2
) -> Optional[Tuple[int, int]]:
    """
    Locate a bar button by its image in img/ and return its center (x, y).

    - Searches only within BAR_REGION for speed.
    - Uses LOCATION_CACHE depending on CACHE_MODE ("use" or "update").
    - Falls back to BUTTON_FALLBACKS[key] if detection fails.
    """
    global LOCATION_CACHE

    buttons = LOCATION_CACHE.setdefault("buttons", {})

    # 1) If we are allowed to use cache and we have it
    if CACHE_MODE == "use" and key in buttons:
        pos = buttons[key]
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            return int(pos[0]), int(pos[1])

    image_name = BUTTON_IMAGES.get(key)
    if not image_name:
        print(f"[ERROR] No image mapping for key '{key}'.")
        return None

    image_path = os.path.join(IMG_DIR, image_name)

    # If the image file itself is missing, warn once and fallback
    if not os.path.isfile(image_path):
        if image_name not in _missing_image_warned:
            print(f"[WARN] Image '{image_name}' not found in img/. "
                  f"Using fallback for '{key}' if available.")
            _missing_image_warned.add(image_name)
        fallback = BUTTON_FALLBACKS.get(key)
        if fallback:
            return fallback
        return None

    detected_pos: Optional[Tuple[int, int]] = None

    for _ in range(max_tries):
        try:
            box = pyautogui.locateOnScreen(
                image_path,
                confidence=confidence,
                region=BAR_REGION  # restricted search region
            )
        except Exception as e:
            print(f"[WARN] Error locating '{image_name}': {e}")
            break

        if box:
            center = pyautogui.center(box)
            detected_pos = (center.x, center.y)
            break

        time.sleep(retry_delay)

    if detected_pos:
        buttons[key] = [int(detected_pos[0]), int(detected_pos[1])]
        save_location_cache()
        return detected_pos

    # If detection failed, but cache has an older value, use it
    if key in buttons:
        old_pos = buttons[key]
        if isinstance(old_pos, (list, tuple)) and len(old_pos) == 2:
            print(f"[WARN] Could not re-detect '{image_name}', using cached value for '{key}': {old_pos}")
            return int(old_pos[0]), int(old_pos[1])

    # Fall back to hard-coded position if it exists
    fallback = BUTTON_FALLBACKS.get(key)
    if fallback:
        print(f"[WARN] Could not detect '{image_name}' on screen. Using fallback for '{key}': {fallback}")
        return fallback

    print(f"[ERROR] Could not detect '{image_name}' and no fallback for '{key}'.")
    return None


# ============================================
#  Utility: Zoom Out for X Seconds
# ============================================

def center_mouse_and_scroll_out(duration_seconds: float = 1.2, scroll_strength: int = -800):
    print("[INFO] Zooming out...")
    center_x = SCREEN_WIDTH // 2
    center_y = SCREEN_HEIGHT // 2
    pyautogui.moveTo(center_x, center_y, duration=0.2)

    start_time = time.time()
    while time.time() - start_time < duration_seconds:
        pyautogui.scroll(scroll_strength)
        time.sleep(0.02)


# ============================================
#  Click Attack → Find Match → Troop Attack
# ============================================

def click_attack_and_find_match():
    print("[INFO] Opening attack menu...")
    move_and_click(ATTACK_MENU_BUTTON[0], ATTACK_MENU_BUTTON[1],
                   move_duration=0.18, post_delay=0.7)

    print("[INFO] Clicking Find a Match...")
    move_and_click(FIND_MATCH_BUTTON[0], FIND_MATCH_BUTTON[1],
                   move_duration=0.18, post_delay=0.7)

    print("[INFO] Confirming troops & starting search...")
    move_and_click(ATTACK_BUTTON[0], ATTACK_BUTTON[1],
                   move_duration=0.18, post_delay=1.5)


# ============================================
#  Wait for Base Found (NEXT button visible)
# ============================================

def wait_for_base_found(timeout_seconds: float = 60.0, poll_interval: float = 0.5) -> bool:
    print("[INFO] Waiting for base...")
    start = time.time()
    while time.time() - start < timeout_seconds:
        status = get_game_status()
        if status.get("next_button"):
            print("[INFO] Base found.")
            return True
        time.sleep(poll_interval)

    print("[WARN] Base not detected within timeout, proceeding anyway.")
    return False


# ============================================
#  Spell Deployment (Earthquake)
# ============================================

def cast_earthquakes():
    print("[INFO] Deploying Earthquakes...")

    earth_btn = locate_button_center("earthquake")
    if not earth_btn:
        print("[ERROR] Cannot deploy Earthquakes (button not found).")
        return

    move_and_click(earth_btn[0], earth_btn[1],
                   move_duration=0.1, post_delay=0.15)

    for _ in range(3):
        move_and_click(LEFT_EARTH[0], LEFT_EARTH[1],
                       move_duration=0.06, post_delay=0.08)

    for _ in range(4):
        move_and_click(RIGHT_EARTH[0], RIGHT_EARTH[1],
                       move_duration=0.06, post_delay=0.08)

    for _ in range(4):
        move_and_click(BUTTON_EARTH[0], BUTTON_EARTH[1],
                       move_duration=0.06, post_delay=0.08)


# ============================================
#  Siege Machine Deployment
# ============================================

def deploy_siege_machine():
    print("[INFO] Deploying Siege Machine...")

    siege_btn = locate_button_center("siege")
    if not siege_btn:
        print("[ERROR] Cannot deploy Siege Machine (button not found).")
        return

    move_and_click(siege_btn[0], siege_btn[1],
                   move_duration=0.1, post_delay=0.15)
    move_and_click(LEFT_LEFT[0], LEFT_LEFT[1],
                   move_duration=0.16, post_delay=0.2)


# ============================================
#  Valkyrie Deployment along the base
# ============================================

def generate_points_on_segment(start: Point, end: Point, num_points: int) -> List[Point]:
    if num_points <= 1:
        return [start]

    points: List[Point] = []
    for i in range(num_points):
        t = i / (num_points - 1)
        x = int(round(start[0] + (end[0] - start[0]) * t))
        y = int(round(start[1] + (end[1] - start[1]) * t))
        points.append((x, y))
    return points


def generate_valk_positions_raw() -> List[Point]:
    segments = [
        (LEFT_BOTTOM, LEFT_LEFT),
        (LEFT_LEFT, LEFT_UP),
        (RIGHT_UP, RIGHT_RIGHT),
        (RIGHT_RIGHT, RIGHT_BOTTOM),
    ]

    seg_point_counts = [12, 11, 11, 11]  # total 45, with overlaps removed → 42

    positions: List[Point] = []

    for seg_idx, ((x1, y1), (x2, y2)) in enumerate(segments):
        n = seg_point_counts[seg_idx]
        seg_points = generate_points_on_segment((x1, y1), (x2, y2), n)

        if seg_idx > 0:
            seg_points = seg_points[1:]  # avoid duplicate endpoints

        positions.extend(seg_points)

    return positions


def get_valk_positions() -> List[Point]:
    """
    Returns Valkyrie deployment points, possibly cached in LOCATION_CACHE.
    """
    global LOCATION_CACHE

    cached = LOCATION_CACHE.get("valk_positions")
    if CACHE_MODE == "use" and cached:
        try:
            return [(int(x), int(y)) for x, y in cached]
        except Exception:
            pass  # fall back to recompute

    pos = generate_valk_positions_raw()
    LOCATION_CACHE["valk_positions"] = [[int(x), int(y)] for (x, y) in pos]
    save_location_cache()
    return pos


def deploy_valkyries(num_valks: int = 42, click_delay: float = 0.05):
    print("[INFO] Deploying Valkyries...")

    valk_btn = locate_button_center("valk")
    if not valk_btn:
        print("[ERROR] Cannot deploy Valkyries (button not found).")
        return

    all_positions = get_valk_positions()
    total_positions = len(all_positions)
    deploy_count = min(num_valks, total_positions)

    move_and_click(valk_btn[0], valk_btn[1],
                   move_duration=0.1, post_delay=0.15)

    for idx in range(deploy_count):
        x, y = all_positions[idx]
        move_and_click(x, y, move_duration=0.05, post_delay=click_delay)


# ============================================
#  Hero Deployment & Ability
# ============================================

def deploy_heroes():
    """
    Deploys up to four heroes using image detection.
    If any hero is not found (e.g., upgrading), it is simply skipped.

    Left side (midpoint of LEFT_LEFT -> LEFT_BOTTOM):
        - hero_king
        - hero_warden

    Right side (midpoint of RIGHT_RIGHT -> RIGHT_BOTTOM):
        - hero_champ
        - hero_minion
    """
    print("[INFO] Deploying heroes...")

    hero_king   = locate_button_center("hero_king")
    hero_champ  = locate_button_center("hero_champ")
    hero_minion = locate_button_center("hero_minion")
    hero_warden = locate_button_center("hero_warden")

    left_mid_x = (LEFT_LEFT[0] + LEFT_BOTTOM[0]) // 2
    left_mid_y = (LEFT_LEFT[1] + LEFT_BOTTOM[1]) // 2

    right_mid_x = (RIGHT_RIGHT[0] + RIGHT_BOTTOM[0]) // 2
    right_mid_y = (RIGHT_RIGHT[1] + RIGHT_BOTTOM[1]) // 2

    # Left side heroes
    if hero_king:
        move_and_click(hero_king[0], hero_king[1],
                       move_duration=0.1, post_delay=0.15)
        move_and_click(left_mid_x, left_mid_y,
                       move_duration=0.16, post_delay=0.15)

    if hero_warden:
        move_and_click(hero_warden[0], hero_warden[1],
                       move_duration=0.1, post_delay=0.15)
        move_and_click(left_mid_x, left_mid_y,
                       move_duration=0.16, post_delay=0.15)

    # Right side heroes
    if hero_champ:
        move_and_click(hero_champ[0], hero_champ[1],
                       move_duration=0.1, post_delay=0.15)
        move_and_click(right_mid_x, right_mid_y,
                       move_duration=0.16, post_delay=0.15)

    if hero_minion:
        move_and_click(hero_minion[0], hero_minion[1],
                       move_duration=0.1, post_delay=0.15)
        move_and_click(right_mid_x, right_mid_y,
                       move_duration=0.16, post_delay=0.15)


def activate_hero_abilities(delay_before: float = 0.25):
    """
    Tries to trigger abilities for any heroes that exist.
    If a hero button isn't found (e.g., hero under upgrade), it is skipped.
    """
    if delay_before > 0:
        time.sleep(delay_before)

    print("[INFO] Activating hero abilities...")

    hero_king   = locate_button_center("hero_king")
    hero_champ  = locate_button_center("hero_champ")
    hero_minion = locate_button_center("hero_minion")
    hero_warden = locate_button_center("hero_warden")

    if not any([hero_king, hero_champ, hero_minion, hero_warden]):
        print("[WARN] No hero buttons found to activate abilities.")
        return

    for btn in [hero_king, hero_warden, hero_champ, hero_minion]:
        if btn:
            move_and_click(btn[0], btn[1],
                           move_duration=0.06, post_delay=0.03)


# ============================================
#  Helper: Detect Return Home button by image
# ============================================

def locate_return_home_button(confidence: float = 0.8):
    """
    Look for ReturnHome.png on the WHOLE screen.
    """
    if not RETURN_HOME_IMAGE_AVAILABLE:
        return None

    try:
        box = pyautogui.locateOnScreen(RETURN_HOME_IMAGE_PATH, confidence=confidence)
        return box
    except Exception as e:
        print(f"[WARN] Error locating '{RETURN_HOME_IMAGE_NAME}': {e}")
        return None


# ============================================
#  Wait for 50% destruction OR early Return Home
# ============================================

def wait_for_50_percent_or_return_home(
    max_wait_seconds: float = 90.0,
    poll_interval: float = 0.5
) -> str:
    """
    Checks BOTH:
        - get_game_status()['fifty_percent']   (via five.png)
        - ReturnHome.png on the screen

    If ReturnHome is detected BEFORE 50%, clicks it and returns 'return_home'.
    If 50% hit first, returns '50%'.
    After max_wait_seconds (fail-safe 90s), returns 'timeout' so we can
    surrender and move on instead of hanging forever.
    """
    print("[INFO] Waiting for 50% or battle end...")
    start = time.time()

    while time.time() - start < max_wait_seconds:
        status = get_game_status()
        if status.get("fifty_percent"):
            print("[INFO] 50% destruction reached.")
            return "50%"

        box = locate_return_home_button(confidence=0.8)
        if box:
            center = pyautogui.center(box)
            print("[INFO] Return Home detected before 50%. Ending battle early.")
            move_and_click(center.x, center.y,
                           move_duration=0.22, post_delay=1.5)
            return "return_home"

        time.sleep(poll_interval)

    print("[WARN] 90s timeout waiting for 50% or Return Home.")
    return "timeout"


# ============================================
#  End Battle (Surrender)
# ============================================

def end_battle_and_return_home():
    print("[INFO] Ending battle (surrender)...")

    move_and_click(SURRENDER_BUTTON[0], SURRENDER_BUTTON[1],
                   move_duration=0.18, post_delay=0.8)

    move_and_click(CONFIRM_OK_BUTTON[0], CONFIRM_OK_BUTTON[1],
                   move_duration=0.18, post_delay=1.2)

    move_and_click(RETURN_HOME_BUTTON[0], RETURN_HOME_BUTTON[1],
                   move_duration=0.18, post_delay=1.2)


# ============================================
#  Full Attack Routine (single attack)
# ============================================

def run_full_attack(initial_wait: float = 0.0):
    """
    Runs ONE full attack.

    initial_wait: seconds to wait before starting (for debug/manual mode).
                  In auto-loop, we usually pass 0 and handle a single global
                  wait before the whole loop.
    """
    if initial_wait > 0:
        print(f"[INFO] Starting attack in {initial_wait:.1f} seconds... "
              f"switch to CoC window now.")
        time.sleep(initial_wait)

    center_mouse_and_scroll_out(duration_seconds=1.2)

    click_attack_and_find_match()

    base_found = wait_for_base_found(timeout_seconds=60.0, poll_interval=0.5)

    if base_found:
        print("[INFO] Waiting briefly for base to fully load...")
        time.sleep(2.5)
    else:
        time.sleep(2.0)

    cast_earthquakes()
    time.sleep(1.0)

    deploy_siege_machine()
    deploy_valkyries(num_valks=42, click_delay=0.05)
    deploy_heroes()
    activate_hero_abilities(delay_before=0.25)

    # 90s fail-safe; exits early as soon as ReturnHome or 50% is seen
    battle_status = wait_for_50_percent_or_return_home(max_wait_seconds=90.0,
                                                       poll_interval=0.5)

    if battle_status == "50%":
        end_battle_and_return_home()
    elif battle_status == "return_home":
        print("[INFO] Already back home, no surrender needed.")
    else:
        end_battle_and_return_home()

    print("[INFO] Attack finished.")


# ===================================================================
#  WALL UPGRADE SECTION (image-only, Wall.png @ 0.95 confidence)
# ===================================================================

# Button to open the "All upgradable" list
ALL_UPGRADABLE_BUTTON: Point = (878, 30)

# Upgradable window bounding box (corners you provided)
UPGRADABLE_TOP_LEFT: Point = (656, 140)
UPGRADABLE_TOP_RIGHT: Point = (1296, 146)
UPGRADABLE_BOTTOM_RIGHT: Point = (1301, 761)
UPGRADABLE_BOTTOM_LEFT: Point = (659, 761)

UPGRADABLE_REGION = (
    UPGRADABLE_TOP_LEFT[0],
    UPGRADABLE_TOP_LEFT[1],
    UPGRADABLE_BOTTOM_RIGHT[0] - UPGRADABLE_TOP_LEFT[0],
    UPGRADABLE_BOTTOM_RIGHT[1] - UPGRADABLE_TOP_LEFT[1],
)

# Buttons on the wall upgrade UI
SELECT_MULTIPLE_WALLS: Point = (963, 944)
UPGRADE_WITH_GOLD: Point = (1128, 949)
UPGRADE_WITH_ELIXIR: Point = (1301, 969)
UPGRADE_OKAY_BUTTON: Point = (1161, 747)

# Image for Wall text
WALL_IMAGE_NAME = "Wall.png"
WALL_CONFIDENCE = 0.95

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

# Tunable parameters
NUM_WALLS_PER_GOLD_UPGRADE = 4       # how many walls to select for gold upgrade
NUM_WALLS_PER_ELIXIR_UPGRADE = 4     # how many walls to select for elixir upgrade

MAX_WALL_SCROLL_ATTEMPTS = 25        # how many scroll 'ticks' to look for 'Wall'
SCROLL_AMOUNT_PER_TICK = -350        # negative scroll = scroll DOWN
SCROLL_DELAY = 0.40                  # pause after each scroll


def locate_wall_by_image(confidence: float = WALL_CONFIDENCE) -> Optional[Point]:
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


def find_and_click_wall_entry(max_scrolls: int = MAX_WALL_SCROLL_ATTEMPTS) -> bool:
    """
    Scrolls through the upgradables window, trying to find the 'Wall' entry.

    After each scroll:
      - Try image detection (Wall.png) inside UPGRADABLE_REGION

    Once found, clicks on it and returns True.
    If not found after max_scrolls scroll steps, returns False.
    """
    if not WALL_IMAGE_AVAILABLE:
        print("[UPGRADE] Wall image not available; cannot search for 'Wall'.")
        return False

    center_x = UPGRADABLE_TOP_LEFT[0] + (UPGRADABLE_BOTTOM_RIGHT[0] - UPGRADABLE_TOP_LEFT[0]) // 2
    center_y = UPGRADABLE_TOP_LEFT[1] + (UPGRADABLE_BOTTOM_RIGHT[1] - UPGRADABLE_TOP_LEFT[1]) // 2

    # Try once before scrolling
    for attempt in range(max_scrolls + 1):
        pos = locate_wall_by_image(confidence=WALL_CONFIDENCE)
        if pos:
            print(f"[UPGRADE] Found 'Wall' entry at {pos} on attempt {attempt}. Clicking...")
            move_and_click(pos[0], pos[1], move_duration=0.18, post_delay=0.40)
            return True

        if attempt < max_scrolls:
            # Move mouse into the list window and scroll a bit
            pyautogui.moveTo(center_x, center_y, duration=0.10)
            pyautogui.scroll(SCROLL_AMOUNT_PER_TICK)
            time.sleep(SCROLL_DELAY)

    print("[UPGRADE] Could not find 'Wall' entry after scrolling.")
    return False


# ============================================
#  High-level wall upgrade helpers
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
    Opens the upgradables window, finds the Wall entry (image only),
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
    Opens the upgradables window, finds the Wall entry (image only),
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


# ===================================================================
#  ORCHESTRATION: Loot + Wall Upgrades + Debug
# ===================================================================

def run_loot_cycle(attacks_per_cycle: int) -> None:
    """
    Runs exactly 'attacks_per_cycle' attacks back-to-back.
    """
    print(f"[ORCH] Starting loot cycle: {attacks_per_cycle} attack(s).")

    for i in range(attacks_per_cycle):
        print(f"\n========== ATTACK {i + 1}/{attacks_per_cycle} ==========")
        # In auto-mode we don't need extra wait here; we already did a global wait.
        run_full_attack(initial_wait=0.0)
        if i < attacks_per_cycle - 1:
            print("[ORCH] Preparing next attack...")
            time.sleep(1.5)

    print("[ORCH] Loot cycle finished.")


def loot_and_upgrade_loop(attacks_per_cycle: int = 30) -> None:
    """
    Main auto mode loop:

      LOOP:
        1) Run 'attacks_per_cycle' attacks to gather loot.
        2) Upgrade 3 walls with GOLD.
        3) Upgrade 3 walls with ELIXIR.
      UNTIL:
        Both GOLD and ELIXIR upgrades fail in the same cycle
        (no walls to upgrade / not upgradable).
    """
    cycle_index = 0

    while True:
        cycle_index += 1
        print("\n====================================================")
        print(f"  LOOT + WALL UPGRADE CYCLE {cycle_index}")
        print("====================================================")

        # 1) LOOT PHASE
        run_loot_cycle(attacks_per_cycle)

        # Give game a moment to fully return home after last attack
        print("[ORCH] Waiting 3 seconds for game to settle at home screen...")
        time.sleep(3.0)

        # 2) WALL UPGRADE PHASE
        gold_success, elixir_success = upgrade_walls_full_cycle(
            gold_walls=NUM_WALLS_PER_GOLD_UPGRADE,
            elixir_walls=NUM_WALLS_PER_ELIXIR_UPGRADE,
        )

        # If both failed, there's nothing more to upgrade at this moment
        if not gold_success and not elixir_success:
            print("[ORCH] No successful wall upgrades in this cycle.")
            print("[ORCH] Probably no walls left to upgrade (or not upgradable).")
            print("[ORCH] Stopping automation loop.")
            break

        # Otherwise, continue to the next cycle
        print("[ORCH] Cycle finished with some successful upgrades.")
        print("[ORCH] Starting next loot+upgrade cycle shortly...")
        time.sleep(5.0)


# ============================================
#  DEBUG MENU
# ============================================

def debug_menu() -> None:
    """
    Simple debug menu to test individual parts:

      1) Single full attack
      2) Just open upgradable window & find/click Wall once
      3) GOLD wall upgrade only (3 walls)
      4) ELIXIR wall upgrade only (3 walls)
      5) Full wall upgrade cycle (3 gold + 3 elixir)
      6) Exit debug
    """
    while True:
        print("\n================ DEBUG MENU ================")
        print("1) Run ONE full attack")
        print("2) Test: find & click 'Wall' only (no upgrade)")
        print("3) Test: GOLD wall upgrade only")
        print("4) Test: ELIXIR wall upgrade only")
        print("5) Test: FULL wall upgrade cycle (GOLD + ELIXIR)")
        print("6) Exit debug menu")
        choice = input("Choose an option [1-6] (default 6): ").strip()

        if choice == "1":
            print("[DEBUG] Running ONE full attack in 5 seconds...")
            time.sleep(5.0)
            run_full_attack(initial_wait=0.0)  # we already waited 5s here
        elif choice == "2":
            print("[DEBUG] Testing Wall find-only in 5 seconds...")
            time.sleep(5.0)
            open_upgradables_window()
            found = find_and_click_wall_entry()
            print(f"[DEBUG] Wall find-only result: {found}")
        elif choice == "3":
            print("[DEBUG] Testing GOLD wall upgrade in 5 seconds...")
            time.sleep(5.0)
            result = upgrade_walls_with_gold()
            print(f"[DEBUG] GOLD upgrade result: {result}")
        elif choice == "4":
            print("[DEBUG] Testing ELIXIR wall upgrade in 5 seconds...")
            time.sleep(5.0)
            result = upgrade_walls_with_elixir()
            print(f"[DEBUG] ELIXIR upgrade result: {result}")
        elif choice == "5":
            print("[DEBUG] Testing FULL wall upgrade cycle in 5 seconds...")
            time.sleep(5.0)
            result = upgrade_walls_full_cycle()
            print(f"[DEBUG] Full cycle result: {result}")
        else:
            print("[DEBUG] Exiting debug menu.")
            break


# ============================================
#  MAIN ENTRY
# ============================================

def main():
    init_location_cache_mode()

    print("====================================================")
    print("   Auto Loot + Wall Upgrade SUPER SCRIPT")
    print("====================================================")
    print("Modes:")
    print("  1) FULL AUTO:   N attacks + 3 GOLD walls + 3 ELIXIR walls,")
    print("                  repeat until no walls are upgradable.")
    print("  2) DEBUG MODE:  Manually test attacks / wall upgrades.")
    print("")

    mode = input("Select mode [1 = full auto, 2 = debug] (default 1): ").strip()

    if mode == "2":
        debug_menu()
        return

    # FULL AUTO MODE
    try:
        attacks_input = input("How many attacks per cycle? (default 30): ").strip()
        attacks_per_cycle = int(attacks_input) if attacks_input else 30
    except ValueError:
        print("[WARN] Invalid input, defaulting attacks per cycle to 30.")
        attacks_per_cycle = 30

    if attacks_per_cycle < 1:
        print("[WARN] Attacks per cycle < 1, forcing to 1.")
        attacks_per_cycle = 1

    print("\n[ORCH] Configuration:")
    print(f"  Attacks per cycle : {attacks_per_cycle}")
    print(f"  Walls per GOLD    : {NUM_WALLS_PER_GOLD_UPGRADE}")
    print(f"  Walls per ELIXIR  : {NUM_WALLS_PER_ELIXIR_UPGRADE}")
    print("  Stop condition    : Both GOLD and ELIXIR upgrades fail in a cycle.")
    print("\n[ORCH] Starting in 5 seconds... switch to CoC window now.")
    time.sleep(5.0)

    loot_and_upgrade_loop(attacks_per_cycle=attacks_per_cycle)

    print("\n[ORCH] Automation finished. You can close this window now.")


if __name__ == "__main__":
    main()

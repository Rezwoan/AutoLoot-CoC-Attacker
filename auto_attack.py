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


# ============================================
#  Screen & Geometry
# ============================================

SCREEN_WIDTH  = 1920
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
    "hero_warden": "HERO_WARDEN.png",     # New hero
}

# Optional fallback positions if detection fails completely
BUTTON_FALLBACKS = {
    "valk":        (520, 1140),
    "siege":       (617, 1132),
    "earthquake":  (888, 1142),
    "hero_king":   (711, 1136),
    "hero_champ":  (783, 1146),
    "hero_minion": (868, 1145),
    "hero_warden": (950, 1145),   # guess; mostly used only if detection fails
}

# ============================================
#  Location cache (loaded/saved via location_cache.py)
# ============================================

LOCATION_CACHE = {}
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
#  Utility: Mouse helpers
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

Point = Tuple[int, int]


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
#  Full Attack Routine
# ============================================

def run_full_attack():
    print("[INFO] Starting attack in 5 seconds... switch to CoC window now.")
    time.sleep(5)

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


# ============================================
#  Main
# ============================================

def main():
    init_location_cache_mode()

    try:
        user_input = input("How many attacks do you want to run? (default 1): ").strip()
        num_attacks = int(user_input) if user_input else 1
    except ValueError:
        print("[WARN] Invalid number, defaulting to 1 attack.")
        num_attacks = 1

    if num_attacks < 1:
        print("[WARN] Non-positive number of attacks, forcing to 1.")
        num_attacks = 1

    print(f"[INFO] Running {num_attacks} attack(s).")

    for i in range(num_attacks):
        print(f"\n========== ATTACK {i+1}/{num_attacks} ==========")
        run_full_attack()
        if i < num_attacks - 1:
            print("[INFO] Preparing next attack...")
            time.sleep(1.5)


if __name__ == "__main__":
    main()

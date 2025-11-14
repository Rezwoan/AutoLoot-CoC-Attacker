import time
from typing import List, Tuple

import pyautogui

# Import the game status helper from your imageRec.py
# Make sure imageRec.py is in the same folder.
from imageRec import get_game_status

# ============================================
#  PyAutoGUI Global Settings
# ============================================

pyautogui.FAILSAFE = True      # Move mouse to a screen corner to abort
pyautogui.PAUSE = 0.05         # Small delay between actions


# ============================================
#  Screen & Geometry
# ============================================

SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1200

SCREEN_TOP_LEFT     = (0, 0)
SCREEN_TOP_RIGHT    = (SCREEN_WIDTH - 1, 0)
SCREEN_BOTTOM_LEFT  = (0, SCREEN_HEIGHT - 1)
SCREEN_BOTTOM_RIGHT = (SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1)

# Old edges (kept for reference if needed)
EDGE_LEFT   = (173, 564)
EDGE_RIGHT  = (1737, 568)

BOTTOM_CENTER_1 = (999, 1071)
BOTTOM_CENTER_2 = (912, 1067)
BOTTOM_UPPER    = (1075, 1040)

# NEW deployment geometry
LEFT_LEFT    = (181, 592)
LEFT_BOTTOM  = (823, 1075)
RIGHT_BOTTOM = (1156, 1075)
RIGHT_RIGHT  = (1787, 590)
RIGHT_UP     = (1070, 60)
LEFT_UP      = (878, 70)


# ============================================
#  Buttons (Screen UI)
# ============================================

ATTACK_BUTTON      = (126, 1092)
FIND_MATCH         = (301, 847)
NEXT_BUTTON        = (1780, 988)     # (detection done in imageRec via template)

SURRENDER_BUTTON   = (117, 1021)
CONFIRM_OK_BUTTON  = (1170, 763)
RETURN_HOME_BUTTON = (945, 1025)


# ============================================
#  Troop/Spell/Hero Bar Slots (bottom bar)
# ============================================

VALKARIE_BUTTON      = (520, 1140)
SIEGE_BUTTON         = (617, 1132)
HERO1_BUTTON         = (711, 1136)   # Grand Warden
HERO2_BUTTON         = (783, 1146)   # Royal Champion
EARTHQUAKE_BUTTON    = (888, 1142)

# Earthquake target positions on battlefield
LEFT_EARTH   = (635, 567)   # 3 quakes
RIGHT_EARTH  = (1245, 581)  # 4 quakes
BUTTON_EARTH = (951, 783)   # 4 quakes


# ============================================
#  Utility: Mouse helpers
# ============================================

def move_and_click(x: int, y: int, move_duration: float = 0.1, post_delay: float = 0.05):
    """Move to (x, y) and click."""
    pyautogui.moveTo(x, y, duration=move_duration)
    pyautogui.click()
    time.sleep(post_delay)


# ============================================
#  Utility: Zoom Out for X Seconds
# ============================================

def center_mouse_and_scroll_out(duration_seconds: float = 2.0, scroll_strength: int = -800):
    """
    Moves mouse to the center of the screen and scrolls DOWN continuously
    for the specified duration to ensure full zoom-out.
    """
    center_x = SCREEN_WIDTH // 2
    center_y = SCREEN_HEIGHT // 2

    print(f"[INFO] Moving mouse to center: ({center_x}, {center_y})")
    pyautogui.moveTo(center_x, center_y, duration=0.3)

    print(f"[INFO] Zooming OUT for {duration_seconds} seconds...")
    start_time = time.time()

    while time.time() - start_time < duration_seconds:
        pyautogui.scroll(scroll_strength)
        time.sleep(0.03)

    print("[INFO] Zoom-out complete.")


# ============================================
#  Click Attack → Find Match
# ============================================

def click_attack_and_find_match():
    """
    Navigates the CoC home screen:
    - Clicks the Attack button
    - Waits for the Attack menu to appear
    - Clicks Find Match
    """
    print("[INFO] Clicking Attack button...")
    move_and_click(ATTACK_BUTTON[0], ATTACK_BUTTON[1], move_duration=0.25, post_delay=1.5)

    print("[INFO] Clicking Find Match...")
    move_and_click(FIND_MATCH[0], FIND_MATCH[1], move_duration=0.25, post_delay=3.0)

    print("[INFO] Searching for base...")


# ============================================
#  Wait for Base Found (NEXT button visible)
# ============================================

def wait_for_base_found(timeout_seconds: float = 60.0, poll_interval: float = 0.5) -> bool:
    """
    Uses get_game_status() from imageRec to wait until NEXT button is visible,
    meaning a base has been found.

    Returns True if base found within timeout, False otherwise.
    """
    print(f"[INFO] Waiting for base (NEXT button) for up to {timeout_seconds} seconds...")

    start = time.time()
    while time.time() - start < timeout_seconds:
        status = get_game_status()
        if status.get("next_button"):
            print("[INFO] Base found! NEXT button detected.")
            return True
        time.sleep(poll_interval)

    print("[WARN] Base not detected within timeout, proceeding anyway.")
    return False


# ============================================
#  Spell Deployment (Earthquake)
# ============================================

def cast_earthquakes():
    """
    Casts earthquakes using the bar slot:
        - Click EARTHQUAKE_BUTTON to select quake spell
        - 3 clicks at LEFT_EARTH
        - 4 clicks at RIGHT_EARTH
        - 4 clicks at BUTTON_EARTH
    """
    print("[INFO] Casting Earthquake spells...")

    # Select earthquake spell from bar
    print(f"  [SELECT] Earthquake slot at {EARTHQUAKE_BUTTON}")
    move_and_click(EARTHQUAKE_BUTTON[0], EARTHQUAKE_BUTTON[1],
                   move_duration=0.15, post_delay=0.25)

    # 3 quakes at LEFT_EARTH
    for i in range(3):
        print(f"  [EARTH] LEFT {i+1}/3 at {LEFT_EARTH}")
        move_and_click(LEFT_EARTH[0], LEFT_EARTH[1], move_duration=0.1, post_delay=0.15)

    # 4 quakes at RIGHT_EARTH
    for i in range(4):
        print(f"  [EARTH] RIGHT {i+1}/4 at {RIGHT_EARTH}")
        move_and_click(RIGHT_EARTH[0], RIGHT_EARTH[1], move_duration=0.1, post_delay=0.15)

    # 4 quakes at BUTTON_EARTH
    for i in range(4):
        print(f"  [EARTH] BUTTON {i+1}/4 at {BUTTON_EARTH}")
        move_and_click(BUTTON_EARTH[0], BUTTON_EARTH[1], move_duration=0.1, post_delay=0.15)

    print("[INFO] Earthquake spells deployed.")


# ============================================
#  Siege Machine Deployment
# ============================================

def deploy_siege_machine():
    """
    Select siege machine from bar (SIEGE_BUTTON) and drop it on LEFT_LEFT.
    """
    print("[INFO] Deploying Siege Machine...")

    # Select siege from bar
    print(f"  [SELECT] Siege slot at {SIEGE_BUTTON}")
    move_and_click(SIEGE_BUTTON[0], SIEGE_BUTTON[1],
                   move_duration=0.15, post_delay=0.25)

    # Drop on left side of base
    move_and_click(LEFT_LEFT[0], LEFT_LEFT[1], move_duration=0.25, post_delay=0.3)
    print(f"[INFO] Siege Machine deployed at LEFT_LEFT: {LEFT_LEFT}.")


# ============================================
#  Valkyrie Deployment along the base
# ============================================

Point = Tuple[int, int]

def generate_points_on_segment(start: Point, end: Point, num_points: int) -> List[Point]:
    """
    Returns 'num_points' evenly spaced points from start -> end (inclusive).
    """
    if num_points <= 1:
        return [start]

    points: List[Point] = []
    for i in range(num_points):
        t = i / (num_points - 1)
        x = int(round(start[0] + (end[0] - start[0]) * t))
        y = int(round(start[1] + (end[1] - start[1]) * t))
        points.append((x, y))
    return points


def generate_valk_positions() -> List[Point]:
    """
    Generates ~42 positions along these four lines:
        1) LEFT_BOTTOM  -> LEFT_LEFT
        2) LEFT_LEFT    -> LEFT_UP
        3) RIGHT_UP     -> RIGHT_RIGHT
        4) RIGHT_RIGHT  -> RIGHT_BOTTOM

    We allocate points per segment as [12, 11, 11, 11] and avoid
    duplicating the shared endpoints between segments, so total
    unique positions = 42.
    """
    segments = [
        (LEFT_BOTTOM, LEFT_LEFT),   # seg 0
        (LEFT_LEFT, LEFT_UP),       # seg 1
        (RIGHT_UP, RIGHT_RIGHT),    # seg 2
        (RIGHT_RIGHT, RIGHT_BOTTOM) # seg 3
    ]

    # Number of interpolation samples per segment
    # sum = 45 → after skipping overlapping endpoints, we get 42 points
    seg_point_counts = [12, 11, 11, 11]

    positions: List[Point] = []

    for seg_idx, ((x1, y1), (x2, y2)) in enumerate(segments):
        n = seg_point_counts[seg_idx]
        seg_points = generate_points_on_segment((x1, y1), (x2, y2), n)

        if seg_idx > 0:
            # Skip the first point of this segment to avoid duplicates
            seg_points = seg_points[1:]

        positions.extend(seg_points)

    print(f"[DEBUG] Generated {len(positions)} Valkyrie positions.")
    return positions


def deploy_valkyries(num_valks: int = 42, click_delay: float = 0.12):
    """
    Deploys Valkyries along the four lines described above.

    Steps:
        - Generates positions along the lines.
        - Clicks VALKARIE_BUTTON to select Valkyries.
        - Clicks on up to 'num_valks' positions.
    """
    all_positions = generate_valk_positions()
    total_positions = len(all_positions)

    deploy_count = min(num_valks, total_positions)

    print(f"[INFO] Deploying {deploy_count} Valkyries (have {num_valks}, {total_positions} positions).")

    # Select valkyries from bar
    print(f"  [SELECT] Valkarie slot at {VALKARIE_BUTTON}")
    move_and_click(VALKARIE_BUTTON[0], VALKARIE_BUTTON[1],
                   move_duration=0.15, post_delay=0.25)

    for idx in range(deploy_count):
        x, y = all_positions[idx]
        print(f"  [VALK] {idx+1}/{deploy_count} at ({x}, {y})")
        move_and_click(x, y, move_duration=0.08, post_delay=click_delay)

    print("[INFO] Valkyrie deployment complete.")


# ============================================
#  Hero Deployment & Ability
# ============================================

def deploy_heroes():
    """
    Deploys two heroes:
        - Hero1 (Grand Warden) at midpoint of LEFT_LEFT -> LEFT_BOTTOM
        - Hero2 (Champion) at midpoint of RIGHT_RIGHT -> RIGHT_BOTTOM
    """
    print("[INFO] Deploying heroes...")

    # Midpoint between LEFT_LEFT and LEFT_BOTTOM
    hero1_x = (LEFT_LEFT[0] + LEFT_BOTTOM[0]) // 2
    hero1_y = (LEFT_LEFT[1] + LEFT_BOTTOM[1]) // 2

    # Midpoint between RIGHT_RIGHT and RIGHT_BOTTOM
    hero2_x = (RIGHT_RIGHT[0] + RIGHT_BOTTOM[0]) // 2
    hero2_y = (RIGHT_RIGHT[1] + RIGHT_BOTTOM[1]) // 2

    # Deploy Hero 1 (Grand Warden)
    print(f"  [SELECT HERO1] Bar slot at {HERO1_BUTTON}")
    move_and_click(HERO1_BUTTON[0], HERO1_BUTTON[1],
                   move_duration=0.15, post_delay=0.25)
    print(f"  [HERO1] Deploy at ({hero1_x}, {hero1_y})")
    move_and_click(hero1_x, hero1_y, move_duration=0.2, post_delay=0.3)

    # Deploy Hero 2 (Champion)
    print(f"  [SELECT HERO2] Bar slot at {HERO2_BUTTON}")
    move_and_click(HERO2_BUTTON[0], HERO2_BUTTON[1],
                   move_duration=0.15, post_delay=0.25)
    print(f"  [HERO2] Deploy at ({hero2_x}, {hero2_y})")
    move_and_click(hero2_x, hero2_y, move_duration=0.2, post_delay=0.3)

    print("[INFO] Heroes deployed.")


def activate_hero_abilities(delay_before: float = 5.0):
    """
    After heroes are on the field, waits a bit and then
    clicks their bar buttons ONCE AGAIN to trigger abilities.
    """
    print(f"[INFO] Waiting {delay_before} seconds before activating hero abilities...")
    time.sleep(delay_before)

    print("[INFO] Activating hero abilities via bar buttons...")
    print("  [HERO1 ABILITY] Clicking HERO1_BUTTON again")
    move_and_click(HERO1_BUTTON[0], HERO1_BUTTON[1],
                   move_duration=0.15, post_delay=0.2)

    print("  [HERO2 ABILITY] Clicking HERO2_BUTTON again")
    move_and_click(HERO2_BUTTON[0], HERO2_BUTTON[1],
                   move_duration=0.15, post_delay=0.2)

    print("[INFO] Hero abilities activated.")


# ============================================
#  Wait for 50% destruction
# ============================================

def wait_for_50_percent(max_wait_seconds: float = 120.0, poll_interval: float = 1.0) -> bool:
    """
    Uses get_game_status() to wait until 'fifty_percent' becomes True,
    or until max_wait_seconds passes.

    Returns True if 50% detected, False if timed out.
    """
    print(f"[INFO] Waiting for 50% destruction (up to {max_wait_seconds} sec)...")
    start = time.time()

    while time.time() - start < max_wait_seconds:
        status = get_game_status()
        if status.get("fifty_percent"):
            print("[INFO] 50% destruction reached!")
            return True
        time.sleep(poll_interval)

    print("[WARN] 50% not detected within timeout.")
    return False


# ============================================
#  End Battle (Surrender)
# ============================================

def end_battle_and_return_home():
    """
    Ends the attack by:
        - Clicking surrender
        - Confirming OK
        - Clicking Return Home
    """
    print("[INFO] Ending battle...")

    # Click SURRENDER
    print("  [SURRENDER] Clicking surrender button...")
    move_and_click(SURRENDER_BUTTON[0], SURRENDER_BUTTON[1], move_duration=0.25, post_delay=1.0)

    # Confirm OK
    print("  [CONFIRM] Clicking OK button...")
    move_and_click(CONFIRM_OK_BUTTON[0], CONFIRM_OK_BUTTON[1], move_duration=0.25, post_delay=2.0)

    # Return Home
    print("  [HOME] Clicking Return Home button...")
    move_and_click(RETURN_HOME_BUTTON[0], RETURN_HOME_BUTTON[1], move_duration=0.25, post_delay=2.0)

    print("[INFO] Returned to home village.")


# ============================================
#  Full Attack Routine
# ============================================

def run_full_attack():
    """
    Full sequence for ONE attack:
        1) Zoom out
        2) Attack -> Find Match
        3) Wait for base (NEXT button)
        4) Small delay so troops bar fully loads
        5) Deploy spells (earthquake)
        6) Deploy siege
        7) Deploy valkyries (up to 42)
        8) Deploy heroes
        9) Activate hero abilities (click hero buttons again)
        10) Wait for 50%
        11) Surrender and return home
    """
    print("[INFO] Starting full attack in 3 seconds... Switch to CoC window now!")
    time.sleep(3)

    # 1) Fully zoom out
    center_mouse_and_scroll_out(duration_seconds=2.0)

    # 2) Click Attack → Find Match
    click_attack_and_find_match()

    # 3) Wait for base found (NEXT button)
    base_found = wait_for_base_found(timeout_seconds=60.0, poll_interval=0.5)

    # Extra delay after base is found so UI and troop bar fully load
    if base_found:
        print("[INFO] Base confirmed. Waiting 1 second for UI to settle before selecting troops/spells.")
        time.sleep(1.0)
    else:
        # Even if not confirmed, wait a bit before trying anything
        time.sleep(2.0)

    # 4) Earthquakes
    cast_earthquakes()

    # 5) Siege machine
    deploy_siege_machine()

    # 6) Valkyries
    deploy_valkyries(num_valks=42, click_delay=0.12)

    # 7) Heroes
    deploy_heroes()

    # 8) Hero abilities
    activate_hero_abilities(delay_before=5.0)

    # 9) Wait for 50% destruction
    wait_for_50_percent(max_wait_seconds=120.0, poll_interval=1.0)

    # 10) End battle and return home
    end_battle_and_return_home()

    print("[INFO] Attack sequence complete.")


# ============================================
#  Main (ask how many attacks)
# ============================================

def main():
    try:
        user_input = input("How many attacks do you want to run? (default 1): ").strip()
        num_attacks = int(user_input) if user_input else 1
    except ValueError:
        print("[WARN] Invalid number, defaulting to 1 attack.")
        num_attacks = 1

    if num_attacks < 1:
        print("[WARN] Non-positive number of attacks, forcing to 1.")
        num_attacks = 1

    print(f"[INFO] Will run {num_attacks} attack(s).")

    for i in range(num_attacks):
        print(f"\n================= ATTACK {i+1}/{num_attacks} =================")
        run_full_attack()
        # Short pause between attacks in case you need it
        if i < num_attacks - 1:
            print("[INFO] Preparing for next attack...")
            time.sleep(3)


if __name__ == "__main__":
    main()

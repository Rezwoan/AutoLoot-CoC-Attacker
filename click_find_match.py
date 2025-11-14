import pyautogui
import time

# ============================================
#  PyAutoGUI Global Settings
# ============================================

pyautogui.FAILSAFE = True      # Move mouse to a screen corner to abort
pyautogui.PAUSE = 0.05         # Optional small delay between actions


# ============================================
#  Screen & Geometry
# ============================================

SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1200

SCREEN_TOP_LEFT     = (0, 0)
SCREEN_TOP_RIGHT    = (SCREEN_WIDTH - 1, 0)
SCREEN_BOTTOM_LEFT  = (0, SCREEN_HEIGHT - 1)
SCREEN_BOTTOM_RIGHT = (SCREEN_WIDTH - 1, SCREEN_HEIGHT - 1)

EDGE_LEFT   = (173, 564)
EDGE_RIGHT  = (1737, 568)

BOTTOM_CENTER_1 = (999, 1071)
BOTTOM_CENTER_2 = (912, 1067)
BOTTOM_UPPER    = (1075, 1040)


# ============================================
#  Buttons
# ============================================

ATTACK_BUTTON      = (126, 1092)
FIND_MATCH         = (301, 847)
NEXT_BUTTON        = (1780, 988)     # <-- NEW BUTTON SAVED HERE

SURRENDER_BUTTON   = (117, 1021)
CONFIRM_OK_BUTTON  = (1170, 763)
RETURN_HOME_BUTTON = (945, 1025)


# ============================================
#  Troops / Heroes / Spells
# ============================================

TROOP_VALKYRIE_SLOT = 1

HERO_WARDEN_KEY    = 'q'
HERO_CHAMPION_KEY  = 'w'

SPELL_EARTHQUAKE_KEY = 'a'


# ============================================
#  Utility: Zoom Out for X Seconds
# ============================================

def center_mouse_and_scroll_out(duration_seconds=2, scroll_strength=-800):
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
    pyautogui.moveTo(ATTACK_BUTTON[0], ATTACK_BUTTON[1], duration=0.25)
    pyautogui.click()
    time.sleep(1.5)

    print("[INFO] Clicking Find Match...")
    pyautogui.moveTo(FIND_MATCH[0], FIND_MATCH[1], duration=0.25)
    pyautogui.click()
    time.sleep(3)  # Wait for matchmaking UI to load


# ============================================
#  Main
# ============================================

def main():
    print("[INFO] Script starting in 3 seconds...")
    time.sleep(3)

    # Step 1: Fully zoom out
    center_mouse_and_scroll_out(duration_seconds=2)

    # Step 2: Click Attack → Find Match
    click_attack_and_find_match()

    print("[INFO] Attack sequence initiated. NEXT_BUTTON saved for later use.")


if __name__ == "__main__":
    main()

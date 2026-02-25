"""
core/attack_engine.py

Shared, OOP-based attack engine for the CoC automation scripts.

Classes
-------
ScreenConfig     – All screen geometry, button positions, and image filenames.
Clicker          – Thin pyautogui wrapper; single place to change timing.
ButtonDetector   – Image-based bar-button detection with JSON location cache.
TroopDeployer    – Deploys valkyries, siege, heroes and casts earthquake spells.
BattleController – High-level battle flow: matchmaking, battle-end detection,
                   surrender.
AttackSession    – Composes one full attack from start to finish.
"""

import os
import time
from typing import Dict, List, Optional, Tuple

import pyautogui

from core.image_recognition import get_game_status
from core.location_cache import load_locations, save_locations

# ---------------------------------------------------------------------------
#  Type alias
# ---------------------------------------------------------------------------

Point = Tuple[int, int]


# ===========================================================================
#  ScreenConfig
# ===========================================================================

class ScreenConfig:
    """
    All hard-coded screen coordinates, regions and image filenames.

    Edit only this class when your game resolution or UI layout changes.
    """

    # --- Screen resolution -------------------------------------------------
    WIDTH:  int = 1920
    HEIGHT: int = 1200

    # --- Battlefield deployment edges --------------------------------------
    LEFT_LEFT:    Point = (181,  592)
    LEFT_BOTTOM:  Point = (823,  1075)
    LEFT_UP:      Point = (878,  70)
    RIGHT_UP:     Point = (1070, 60)
    RIGHT_RIGHT:  Point = (1787, 590)
    RIGHT_BOTTOM: Point = (1156, 1075)

    # --- Earthquake drop points --------------------------------------------
    LEFT_EARTH:   Point = (635,  567)   # 3 quakes
    RIGHT_EARTH:  Point = (1245, 581)   # 4 quakes
    BUTTON_EARTH: Point = (951,  783)   # 4 quakes

    # --- Bottom bar search region (troops/spells/heroes/siege) -------------
    #   Corners: (476,1087) (473,1192) (1435,1189) (1433,1086)
    BAR_LEFT:   int = 473
    BAR_TOP:    int = 1086
    BAR_RIGHT:  int = 1435
    BAR_BOTTOM: int = 1192

    @classmethod
    def bar_region(cls) -> Tuple[int, int, int, int]:
        """(left, top, width, height) tuple for pyautogui region arg."""
        return (
            cls.BAR_LEFT,
            cls.BAR_TOP,
            cls.BAR_RIGHT  - cls.BAR_LEFT,
            cls.BAR_BOTTOM - cls.BAR_TOP,
        )

    # --- Home-screen / UI buttons ------------------------------------------
    ATTACK_MENU_BUTTON: Point = (126,  1092)   # main "Attack" button
    FIND_MATCH_BUTTON:  Point = (301,  847)    # "Find a Match" in attack menu
    ATTACK_BTN:         Point = (1646, 988)    # confirm troops / start search

    SURRENDER_BUTTON:   Point = (117,  1021)
    CONFIRM_OK_BUTTON:  Point = (1170, 763)
    RETURN_HOME_BUTTON: Point = (945,  1025)

    # --- Bar button image filenames (inside img/) --------------------------
    BUTTON_IMAGES: Dict[str, str] = {
        "valk":        "troop_valkyrie.png",
        "siege":       "troop_siege.png",
        "earthquake":  "spell_earthquake.png",
        "hero_king":   "hero_king.png",
        "hero_queen":  "hero_queen.png",
        "hero_warden": "hero_warden.png",
        "hero_champ":  "hero_champion.png",
        "hero_minion": "hero_minion.png",
    }

    # --- Ordered list of all heroes (priority order for deployment) --------
    #   Only the first ``num_heroes`` entries are deployed each attack.
    HERO_ORDER: List[str] = [
        "hero_king",
        "hero_queen",
        "hero_warden",
        "hero_champ",
        "hero_minion",
    ]

    # --- Which heroes deploy on the left vs right side of the base --------
    HERO_SIDE: Dict[str, str] = {
        "hero_king":   "left",
        "hero_queen":  "left",
        "hero_warden": "left",
        "hero_champ":  "right",
        "hero_minion": "right",
    }

    # --- Fallback positions if image detection completely fails ------------
    BUTTON_FALLBACKS: Dict[str, Point] = {
        "valk":        (520, 1140),
        "siege":       (617, 1132),
        "earthquake":  (888, 1142),
        "hero_king":   (711, 1136),
        "hero_queen":  (783, 1136),
        "hero_warden": (868, 1145),
        "hero_champ":  (868, 1146),
        "hero_minion": (950, 1145),
    }

    # --- Return-home image (inside img/) -----------------------------------
    RETURN_HOME_IMAGE: str = "ui_return_home.png"


# ===========================================================================
#  Clicker
# ===========================================================================

class Clicker:
    """
    Thin wrapper around pyautogui mouse operations.

    Centralises timing so it's easy to speed up / slow down the whole bot.
    """

    def __init__(self, move_duration: float = 0.1, post_delay: float = 0.05):
        self.move_duration = move_duration
        self.post_delay    = post_delay
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE    = 0.05

    def click(
        self,
        x: int,
        y: int,
        move_duration: Optional[float] = None,
        post_delay:    Optional[float] = None,
    ) -> None:
        """Move to (x, y), left-click, then sleep."""
        pyautogui.moveTo(
            x, y,
            duration=move_duration if move_duration is not None else self.move_duration,
        )
        pyautogui.click()
        time.sleep(post_delay if post_delay is not None else self.post_delay)

    def scroll_out(self, duration_seconds: float = 1.2, strength: int = -800) -> None:
        """Scroll down (zoom out) continuously for the given duration."""
        cx = ScreenConfig.WIDTH  // 2
        cy = ScreenConfig.HEIGHT // 2
        pyautogui.moveTo(cx, cy, duration=0.2)
        end = time.time() + duration_seconds
        while time.time() < end:
            pyautogui.scroll(strength)
            time.sleep(0.02)


# ===========================================================================
#  ButtonDetector
# ===========================================================================

class ButtonDetector:
    """
    Locates bar buttons by their `img/` template images.

    Maintains an in-memory + JSON cache so that once a button is located it
    doesn't need to be re-scanned every attack (unless the user asks to
    refresh).

    Usage:
        detector = ButtonDetector(img_dir, cache_mode)
        pos = detector.locate("valk")   # returns (x, y) or None
    """

    def __init__(self, img_dir: str, cache_mode: str = "use"):
        """
        Parameters
        ----------
        img_dir    : absolute path to the ``img/`` folder
        cache_mode : ``"use"``    – use JSON cache when available
                     ``"update"`` – always re-detect and overwrite cache
        """
        self._img_dir    = img_dir
        self._cache_mode = cache_mode
        self._cache:     dict = {}
        self._warned:    set  = set()

        self._return_home_path: str  = os.path.join(img_dir, ScreenConfig.RETURN_HOME_IMAGE)
        self._return_home_ok:   bool = os.path.isfile(self._return_home_path)
        if not self._return_home_ok:
            print(f"[WARN] '{ScreenConfig.RETURN_HOME_IMAGE}' not found in img/. "
                  "Return-Home image detection disabled.")

    # ------------------------------------------------------------------
    #  Cache helpers
    # ------------------------------------------------------------------

    def load_cache(self) -> None:
        """Populate internal cache from locations_cache.json."""
        data = load_locations()
        if not isinstance(data, dict):
            data = {}
        data.setdefault("buttons", {})
        data.setdefault("valk_positions", None)
        self._cache = data

    def save_cache(self) -> None:
        """Persist internal cache to locations_cache.json."""
        save_locations(self._cache)

    def ask_cache_mode(self) -> None:
        """
        Prompt user: re-use saved locations or re-detect everything?
        Sets ``self._cache_mode`` accordingly.
        """
        has_data = bool(
            self._cache.get("buttons") or self._cache.get("valk_positions")
        )
        if not has_data:
            self._cache_mode = "update"
            print("[INFO] No cached locations found. Will detect and create cache.")
            return

        choice = input(
            "Use saved button/valk locations from cache? "
            "[Y = use saved, anything else = re-detect]: "
        ).strip().lower()
        if choice == "y":
            self._cache_mode = "use"
            print("[INFO] Using cached locations.")
        else:
            self._cache_mode = "update"
            print("[INFO] Will re-detect and update cache.")

    # ------------------------------------------------------------------
    #  Bar button lookup
    # ------------------------------------------------------------------

    def locate(
        self,
        key:         str,
        confidence:  float = 0.8,
        max_tries:   int   = 5,
        retry_delay: float = 0.2,
    ) -> Optional[Point]:
        """
        Return *(x, y)* for *key* by checking (in order):

        1. In-memory cache (if mode is ``"use"``).
        2. pyautogui template match within ``BAR_REGION``.
        3. Stale cache value (if mode is ``"update"`` but detection failed).
        4. Hard-coded fallback from ``ScreenConfig.BUTTON_FALLBACKS``.
        """
        buttons: dict = self._cache.setdefault("buttons", {})

        # 1) Cache hit
        if self._cache_mode == "use" and key in buttons:
            pos = buttons[key]
            if isinstance(pos, (list, tuple)) and len(pos) == 2:
                return int(pos[0]), int(pos[1])

        # 2) Image detection
        image_name = ScreenConfig.BUTTON_IMAGES.get(key)
        if not image_name:
            print(f"[ERROR] No image mapping for key '{key}'.")
            return None

        image_path = os.path.join(self._img_dir, image_name)

        if not os.path.isfile(image_path):
            if image_name not in self._warned:
                print(f"[WARN] '{image_name}' missing in img/. Using fallback for '{key}'.")
                self._warned.add(image_name)
            return ScreenConfig.BUTTON_FALLBACKS.get(key)

        detected: Optional[Point] = None
        for _ in range(max_tries):
            try:
                box = pyautogui.locateOnScreen(
                    image_path, confidence=confidence, region=ScreenConfig.bar_region()
                )
            except Exception as exc:
                print(f"[WARN] Error locating '{image_name}': {exc}")
                break
            if box:
                c = pyautogui.center(box)
                detected = (c.x, c.y)
                break
            time.sleep(retry_delay)

        if detected:
            buttons[key] = [int(detected[0]), int(detected[1])]
            self.save_cache()
            return detected

        # 3) Stale cache fallback
        if key in buttons:
            pos = buttons[key]
            if isinstance(pos, (list, tuple)) and len(pos) == 2:
                print(f"[WARN] Could not re-detect '{image_name}'; using stale cache for '{key}'.")
                return int(pos[0]), int(pos[1])

        # 4) Hard-coded fallback
        fb = ScreenConfig.BUTTON_FALLBACKS.get(key)
        if fb:
            print(f"[WARN] Detection failed for '{key}'; using hard-coded fallback {fb}.")
            return fb

        print(f"[ERROR] Cannot locate '{key}' – no image, no cache, no fallback.")
        return None

    # ------------------------------------------------------------------
    #  Return-home button
    # ------------------------------------------------------------------

    def locate_return_home(self, confidence: float = 0.8):
        """Return pyautogui box if ReturnHome image is found; else ``None``."""
        if not self._return_home_ok:
            return None
        try:
            return pyautogui.locateOnScreen(self._return_home_path, confidence=confidence)
        except Exception as exc:
            print(f"[WARN] Error locating return-home image: {exc}")
            return None

    # ------------------------------------------------------------------
    #  Valk position cache
    # ------------------------------------------------------------------

    @property
    def valk_positions(self) -> Optional[List[Point]]:
        raw = self._cache.get("valk_positions")
        if raw:
            try:
                return [(int(x), int(y)) for x, y in raw]
            except Exception:
                pass
        return None

    @valk_positions.setter
    def valk_positions(self, positions: List[Point]) -> None:
        self._cache["valk_positions"] = [[int(x), int(y)] for x, y in positions]
        self.save_cache()


# ===========================================================================
#  TroopDeployer
# ===========================================================================

class TroopDeployer:
    """
    Deploys all troops, heroes and spells during a battle.

    Depends on a :class:`Clicker` for mouse actions and a
    :class:`ButtonDetector` for locating bar buttons.
    """

    def __init__(self, clicker: Clicker, detector: ButtonDetector):
        self._click    = clicker
        self._detector = detector

    # ------------------------------------------------------------------
    #  Valkyrie positions
    # ------------------------------------------------------------------

    def _generate_valk_positions(self) -> List[Point]:
        """Compute ~42 evenly-spaced deployment points around the base edges."""
        def lerp(start: Point, end: Point, n: int) -> List[Point]:
            if n <= 1:
                return [start]
            return [
                (
                    int(round(start[0] + (end[0] - start[0]) * i / (n - 1))),
                    int(round(start[1] + (end[1] - start[1]) * i / (n - 1))),
                )
                for i in range(n)
            ]

        cfg = ScreenConfig
        segments = [
            (cfg.LEFT_BOTTOM, cfg.LEFT_LEFT),
            (cfg.LEFT_LEFT,   cfg.LEFT_UP),
            (cfg.RIGHT_UP,    cfg.RIGHT_RIGHT),
            (cfg.RIGHT_RIGHT, cfg.RIGHT_BOTTOM),
        ]
        counts = [12, 11, 11, 11]   # 45 raw → 42 after dedup endpoints

        positions: List[Point] = []
        for idx, (start, end) in enumerate(segments):
            pts = lerp(start, end, counts[idx])
            if idx > 0:
                pts = pts[1:]   # skip duplicated shared endpoint
            positions.extend(pts)
        return positions

    def get_valk_positions(self) -> List[Point]:
        """Return cached valk positions, generating and caching if necessary."""
        cached = self._detector.valk_positions
        if self._detector._cache_mode == "use" and cached:
            return cached
        positions = self._generate_valk_positions()
        self._detector.valk_positions = positions
        return positions

    # ------------------------------------------------------------------
    #  Deployment methods
    # ------------------------------------------------------------------

    def cast_earthquakes(self) -> None:
        """Cast 3+4+4 earthquake spells across the base."""
        print("[INFO] Deploying Earthquakes...")

        btn = self._detector.locate("earthquake")
        if not btn:
            print("[ERROR] Earthquake button not found.")
            return

        self._click.click(*btn, move_duration=0.1, post_delay=0.15)

        cfg = ScreenConfig
        for _ in range(3):
            self._click.click(*cfg.LEFT_EARTH,   move_duration=0.06, post_delay=0.08)
        for _ in range(4):
            self._click.click(*cfg.RIGHT_EARTH,  move_duration=0.06, post_delay=0.08)
        for _ in range(4):
            self._click.click(*cfg.BUTTON_EARTH, move_duration=0.06, post_delay=0.08)

    def deploy_siege_machine(self) -> None:
        """Select siege machine and drop it on the left edge."""
        print("[INFO] Deploying Siege Machine...")

        btn = self._detector.locate("siege")
        if not btn:
            print("[ERROR] Siege Machine button not found.")
            return

        self._click.click(*btn, move_duration=0.1, post_delay=0.15)
        self._click.click(*ScreenConfig.LEFT_LEFT, move_duration=0.16, post_delay=0.2)

    def deploy_valkyries(self, count: int = 42, click_delay: float = 0.05) -> None:
        """Select valkyries and spread them along the four edge segments."""
        print("[INFO] Deploying Valkyries...")

        btn = self._detector.locate("valk")
        if not btn:
            print("[ERROR] Valkyrie button not found.")
            return

        positions  = self.get_valk_positions()
        to_deploy  = min(count, len(positions))

        self._click.click(*btn, move_duration=0.1, post_delay=0.15)
        for x, y in positions[:to_deploy]:
            self._click.click(x, y, move_duration=0.05, post_delay=click_delay)

    def deploy_heroes(self, num_heroes: int = 4) -> None:
        """
        Deploy the first *num_heroes* heroes from ``ScreenConfig.HERO_ORDER``.

        With 5 heroes total only 4 can be active at a time.  Pass the actual
        number currently available (0-4).  Heroes are deployed in priority
        order (king → queen → warden → champ → minion); left-side heroes drop
        on the left edge, right-side heroes on the right edge.  Any hero
        whose button cannot be located is silently skipped.
        """
        num_heroes = max(0, min(4, num_heroes))
        if num_heroes == 0:
            print("[INFO] No heroes to deploy (num_heroes=0).")
            return

        print(f"[INFO] Deploying {num_heroes} hero(es)...")

        cfg = ScreenConfig
        left_mid = (
            (cfg.LEFT_LEFT[0]   + cfg.LEFT_BOTTOM[0]) // 2,
            (cfg.LEFT_LEFT[1]   + cfg.LEFT_BOTTOM[1]) // 2,
        )
        right_mid = (
            (cfg.RIGHT_RIGHT[0] + cfg.RIGHT_BOTTOM[0]) // 2,
            (cfg.RIGHT_RIGHT[1] + cfg.RIGHT_BOTTOM[1]) // 2,
        )

        active_heroes = cfg.HERO_ORDER[:num_heroes]
        for key in active_heroes:
            drop_pos = left_mid if cfg.HERO_SIDE.get(key) == "left" else right_mid
            btn = self._detector.locate(key)
            if btn:
                self._click.click(*btn,      move_duration=0.1,  post_delay=0.15)
                self._click.click(*drop_pos, move_duration=0.16, post_delay=0.15)

    def activate_hero_abilities(
        self,
        num_heroes:   int   = 4,
        delay_before: float = 0.25,
    ) -> None:
        """Re-click the first *num_heroes* hero bar buttons to trigger abilities."""
        if delay_before > 0:
            time.sleep(delay_before)

        num_heroes = max(0, min(4, num_heroes))
        if num_heroes == 0:
            return

        print("[INFO] Activating hero abilities...")

        keys    = ScreenConfig.HERO_ORDER[:num_heroes]
        buttons = [self._detector.locate(k) for k in keys]

        if not any(buttons):
            print("[WARN] No hero buttons found.")
            return

        for btn in buttons:
            if btn:
                self._click.click(*btn, move_duration=0.06, post_delay=0.03)


# ===========================================================================
#  BattleController
# ===========================================================================

class BattleController:
    """
    Manages the high-level battle lifecycle:

    * Navigating to the matchmaking screen.
    * Waiting for a base to be found.
    * Detecting 50% destruction or early Return-Home.
    * Ending the battle (surrender flow).
    """

    def __init__(self, clicker: Clicker, detector: ButtonDetector):
        self._click    = clicker
        self._detector = detector

    def click_attack_and_find_match(self) -> None:
        """Open the attack menu, choose 'Find a Match', confirm troops."""
        print("[INFO] Opening attack menu...")
        cfg = ScreenConfig
        self._click.click(*cfg.ATTACK_MENU_BUTTON, move_duration=0.18, post_delay=0.7)

        print("[INFO] Clicking Find a Match...")
        self._click.click(*cfg.FIND_MATCH_BUTTON,  move_duration=0.18, post_delay=0.7)

        print("[INFO] Confirming troops & starting search...")
        self._click.click(*cfg.ATTACK_BTN,         move_duration=0.18, post_delay=1.5)

    def wait_for_base(
        self,
        timeout:  float = 60.0,
        interval: float = 0.5,
    ) -> bool:
        """
        Poll until the NEXT button appears (base found) or *timeout* elapses.
        Returns ``True`` if a base was found.
        """
        print("[INFO] Waiting for base...")
        end = time.time() + timeout
        while time.time() < end:
            if get_game_status().get("next_button"):
                print("[INFO] Base found.")
                return True
            time.sleep(interval)
        print("[WARN] Base not detected within timeout; proceeding anyway.")
        return False

    def wait_for_battle_end(
        self,
        max_wait: float = 90.0,
        interval: float = 0.5,
    ) -> str:
        """
        Wait for battle to reach a concluding state.

        Returns one of:

        * ``"50%"``          – 50 % destruction detected.
        * ``"return_home"``  – Return Home button appeared early (already won).
        * ``"timeout"``      – Safeguard: 90 s elapsed with neither condition.
        """
        print("[INFO] Waiting for 50% or battle end...")
        end = time.time() + max_wait

        while time.time() < end:
            if get_game_status().get("fifty_percent"):
                print("[INFO] 50% destruction reached.")
                return "50%"

            box = self._detector.locate_return_home(confidence=0.8)
            if box:
                center = pyautogui.center(box)
                print("[INFO] Return Home detected early – ending battle.")
                self._click.click(center.x, center.y, move_duration=0.22, post_delay=1.5)
                return "return_home"

            time.sleep(interval)

        print("[WARN] 90 s timeout – forcing surrender.")
        return "timeout"

    def surrender_and_return_home(self) -> None:
        """Click through the surrender → OK → Return Home sequence."""
        print("[INFO] Ending battle (surrender)...")
        cfg = ScreenConfig
        self._click.click(*cfg.SURRENDER_BUTTON,   move_duration=0.18, post_delay=0.8)
        self._click.click(*cfg.CONFIRM_OK_BUTTON,  move_duration=0.18, post_delay=1.2)
        self._click.click(*cfg.RETURN_HOME_BUTTON, move_duration=0.18, post_delay=1.2)


# ===========================================================================
#  AttackSession
# ===========================================================================

class AttackSession:
    """
    Composes Clicker, ButtonDetector, TroopDeployer and BattleController
    into a single *run()* call that executes one full attack.

    Parameters
    ----------
    img_dir    : absolute path to the ``img/`` folder
    cache_mode : initial cache mode (``"use"`` / ``"update"``)
    """

    def __init__(self, img_dir: str, cache_mode: str = "use", num_heroes: int = 4):
        self.clicker    = Clicker()
        self.detector   = ButtonDetector(img_dir, cache_mode)
        self.deployer   = TroopDeployer(self.clicker, self.detector)
        self.controller = BattleController(self.clicker, self.detector)
        self.num_heroes: int = max(0, min(4, num_heroes))

    def run(self, initial_wait: float = 0.0) -> None:
        """
        Execute one full attack:

        1. Optional wait (to let the user switch windows).
        2. Zoom out.
        3. Navigate to matchmaking.
        4. Wait for base found.
        5. Deploy earthquakes, siege, valkyries, heroes and activate abilities.
        6. Wait for 50% destruction or Return Home.
        7. Surrender if needed.
        """
        if initial_wait > 0:
            print(f"[INFO] Starting in {initial_wait:.0f}s… switch to CoC now.")
            time.sleep(initial_wait)

        self.clicker.scroll_out(duration_seconds=1.2)
        self.controller.click_attack_and_find_match()

        base_found = self.controller.wait_for_base(timeout=60.0)
        time.sleep(2.5 if base_found else 2.0)

        self.deployer.cast_earthquakes()
        time.sleep(1.0)

        self.deployer.deploy_siege_machine()
        self.deployer.deploy_valkyries(count=42, click_delay=0.05)
        self.deployer.deploy_heroes(num_heroes=self.num_heroes)
        self.deployer.activate_hero_abilities(num_heroes=self.num_heroes, delay_before=0.25)

        result = self.controller.wait_for_battle_end(max_wait=90.0)

        if result in ("50%", "timeout"):
            self.controller.surrender_and_return_home()

        print("[INFO] Attack finished.")

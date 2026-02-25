"""
auto_loot_and_wall_upgrade.py

Fully-automated loop that:

  1. Runs N attacks to farm loot.
  2. Upgrades walls with Gold and Elixir.
  3. Repeats until no walls can be upgraded.

This script is the entry point; attack logic lives in ``core/attack_engine``.

Usage
-----
    python auto_loot_and_wall_upgrade.py

or via start.bat.
"""

import os
import time
from typing import Optional, Tuple

import pyautogui

from core.attack_engine import AttackSession, Clicker


# ---------------------------------------------------------------------------
#  Paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_IMG_DIR    = os.path.join(_SCRIPT_DIR, "img")

Point = Tuple[int, int]


# ===========================================================================
#  WallConfig
# ===========================================================================

class WallConfig:
    """
    All screen coordinates and tunable parameters for wall upgrading.

    Edit only this class when UI positions or upgrade counts change.
    """

    # --- "All upgradable" window -------------------------------------------
    ALL_UPGRADABLE_BUTTON: Point = (878, 30)

    UPGRADABLE_TOP_LEFT:     Point = (656,  140)
    UPGRADABLE_TOP_RIGHT:    Point = (1296, 146)
    UPGRADABLE_BOTTOM_RIGHT: Point = (1301, 761)
    UPGRADABLE_BOTTOM_LEFT:  Point = (659,  761)

    @classmethod
    def upgradable_region(cls) -> Tuple[int, int, int, int]:
        """(left, top, width, height) for pyautogui region arg."""
        return (
            cls.UPGRADABLE_TOP_LEFT[0],
            cls.UPGRADABLE_TOP_LEFT[1],
            cls.UPGRADABLE_BOTTOM_RIGHT[0] - cls.UPGRADABLE_TOP_LEFT[0],
            cls.UPGRADABLE_BOTTOM_RIGHT[1] - cls.UPGRADABLE_TOP_LEFT[1],
        )

    # --- Wall upgrade UI buttons -------------------------------------------
    SELECT_MULTIPLE_WALLS: Point = (875,  956)
    UPGRADE_WITH_GOLD:     Point = (1047, 965)
    UPGRADE_WITH_ELIXIR:   Point = (1216, 961)
    UPGRADE_OKAY_BUTTON:   Point = (1161, 747)

    # --- Wall image template -----------------------------------------------
    WALL_IMAGE: str = "ui_wall.png"
    WALL_CONFIDENCE: float = 0.95

    # --- Tunable parameters ------------------------------------------------
    WALLS_PER_GOLD_UPGRADE:   int   = 4
    WALLS_PER_ELIXIR_UPGRADE: int   = 4
    MAX_SCROLL_ATTEMPTS:      int   = 25
    SCROLL_AMOUNT:            int   = -350   # negative = down
    SCROLL_DELAY:             float = 0.50   # seconds after each scroll tick


# ===========================================================================
#  WallUpgrader
# ===========================================================================

class WallUpgrader:
    """
    Finds the Wall entry in the "All upgradable" list and upgrades walls.

    Depends on a :class:`core.attack_engine.Clicker` for mouse actions.

    Public API
    ----------
    upgrade_with_gold(count)    -> bool
    upgrade_with_elixir(count)  -> bool
    run_full_cycle()            -> (gold_ok, elixir_ok)
    """

    def __init__(self, clicker: Clicker, img_dir: str) -> None:
        self._click   = clicker
        self._img_dir = img_dir

        wall_path = os.path.join(img_dir, WallConfig.WALL_IMAGE)
        self._wall_image_path = wall_path
        self._wall_image_ok   = os.path.isfile(wall_path)

        if not self._wall_image_ok:
            print(f"[WARN] '{WallConfig.WALL_IMAGE}' not found in img/. "
                  "Wall image detection will NOT work.")

    # ------------------------------------------------------------------
    #  Window helpers
    # ------------------------------------------------------------------

    def _open_upgradables_window(self) -> None:
        print("[UPGRADE] Opening 'All upgradable' window...")
        btn = WallConfig.ALL_UPGRADABLE_BUTTON
        self._click.click(*btn, move_duration=0.18, post_delay=0.7)

    def _confirm_upgrade(self) -> None:
        print("[UPGRADE] Confirming upgrade (OK button)...")
        self._click.click(
            *WallConfig.UPGRADE_OKAY_BUTTON,
            move_duration=0.18, post_delay=1.5,
        )

    def _select_multiple_walls(self, count: int) -> None:
        if count <= 0:
            return
        print(f"[UPGRADE] Selecting {count} wall(s)...")
        for i in range(count):
            self._click.click(
                *WallConfig.SELECT_MULTIPLE_WALLS,
                move_duration=0.16, post_delay=0.28,
            )
            print(f"[UPGRADE]   -> Wall #{i + 1} selected")

    # ------------------------------------------------------------------
    #  Wall detection
    # ------------------------------------------------------------------

    def _locate_wall_in_region(self, confidence: float) -> Optional[Point]:
        """Search for ui_wall.png inside the upgradable region. Returns (x,y) or None."""
        if not self._wall_image_ok:
            return None

        try:
            box = pyautogui.locateOnScreen(
                self._wall_image_path,
                confidence=confidence,
                region=WallConfig.upgradable_region(),
                grayscale=True,
            )
        except Exception as exc:
            print(f"[WARN] Error locating wall image: {exc}")
            return None

        if not box:
            return None

        c = pyautogui.center(box)
        return c.x, c.y

    def _find_and_click_wall_entry(self) -> bool:
        """
        Scroll through the upgradables list to find the Wall entry and click it.

        Returns ``True`` on success, ``False`` if not found after all scroll
        attempts.
        """
        if not self._wall_image_ok:
            print("[UPGRADE] Wall image unavailable; cannot search.")
            return False

        cfg = WallConfig
        scroll_center = (
            cfg.UPGRADABLE_TOP_LEFT[0] + (cfg.UPGRADABLE_BOTTOM_RIGHT[0] - cfg.UPGRADABLE_TOP_LEFT[0]) // 2,
            cfg.UPGRADABLE_TOP_LEFT[1] + (cfg.UPGRADABLE_BOTTOM_RIGHT[1] - cfg.UPGRADABLE_TOP_LEFT[1]) // 2,
        )

        for attempt in range(cfg.MAX_SCROLL_ATTEMPTS + 1):
            # Try to locate
            pos = self._locate_wall_in_region(cfg.WALL_CONFIDENCE)
            if pos:
                print(f"[UPGRADE] Found 'Wall' at {pos} (attempt {attempt}).")
                # Re-check after a short pause so list animation settles
                time.sleep(0.5)
                confirm_pos = self._locate_wall_in_region(cfg.WALL_CONFIDENCE)
                final = confirm_pos or pos
                self._click.click(*final, move_duration=0.18, post_delay=0.40)
                return True

            if attempt < cfg.MAX_SCROLL_ATTEMPTS:
                pyautogui.moveTo(*scroll_center, duration=0.10)
                pyautogui.scroll(cfg.SCROLL_AMOUNT)
                time.sleep(cfg.SCROLL_DELAY)

        print("[UPGRADE] 'Wall' not found after scrolling.")
        return False

    # ------------------------------------------------------------------
    #  Upgrade actions
    # ------------------------------------------------------------------

    def upgrade_with_gold(self, count: int = WallConfig.WALLS_PER_GOLD_UPGRADE) -> bool:
        """Upgrade *count* walls using Gold. Returns True if upgrade triggered."""
        print("[UPGRADE] Starting GOLD wall upgrade...")
        self._open_upgradables_window()

        if not self._find_and_click_wall_entry():
            print("[UPGRADE] No Wall entry found for GOLD upgrade.")
            return False

        time.sleep(0.8)
        self._select_multiple_walls(count)
        self._click.click(*WallConfig.UPGRADE_WITH_GOLD, move_duration=0.18, post_delay=0.6)
        self._confirm_upgrade()
        print("[UPGRADE] GOLD wall upgrade finished.")
        return True

    def upgrade_with_elixir(self, count: int = WallConfig.WALLS_PER_ELIXIR_UPGRADE) -> bool:
        """Upgrade *count* walls using Elixir. Returns True if upgrade triggered."""
        print("[UPGRADE] Starting ELIXIR wall upgrade...")
        self._open_upgradables_window()

        if not self._find_and_click_wall_entry():
            print("[UPGRADE] No Wall entry found for ELIXIR upgrade.")
            return False

        time.sleep(0.8)
        self._select_multiple_walls(count)
        self._click.click(*WallConfig.UPGRADE_WITH_ELIXIR, move_duration=0.18, post_delay=0.6)
        self._confirm_upgrade()
        print("[UPGRADE] ELIXIR wall upgrade finished.")
        return True

    def run_full_cycle(
        self,
        gold_count:   int = WallConfig.WALLS_PER_GOLD_UPGRADE,
        elixir_count: int = WallConfig.WALLS_PER_ELIXIR_UPGRADE,
    ) -> Tuple[bool, bool]:
        """
        Run one complete Gold + Elixir upgrade cycle.

        Returns *(gold_success, elixir_success)*.
        """
        print("\n========== WALL UPGRADE FULL CYCLE ==========")
        gold_ok   = self.upgrade_with_gold(gold_count)
        time.sleep(2.0)
        elixir_ok = self.upgrade_with_elixir(elixir_count)
        print(f"[UPGRADE] Cycle done. GOLD={gold_ok}, ELIXIR={elixir_ok}")
        return gold_ok, elixir_ok


# ===========================================================================
#  LootAndWallBot
# ===========================================================================

class LootAndWallBot:
    """
    Main orchestrator: farm loot with N attacks, then upgrade walls, repeat.

    The loop stops when both Gold and Elixir upgrades fail in the same cycle
    (i.e. no more walls can be upgraded at this time).

    Public API
    ----------
    setup()
    run(attacks_per_cycle)
    """

    def __init__(self) -> None:
        self._session:  AttackSession | None = None
        self._upgrader: WallUpgrader  | None = None

    # ------------------------------------------------------------------
    #  Setup
    # ------------------------------------------------------------------

    def setup(self) -> None:
        """Initialise session and load/ask about location cache."""
        num_heroes = _ask_num_heroes()
        session = AttackSession(_IMG_DIR, cache_mode="update", num_heroes=num_heroes)
        session.detector.load_cache()
        session.detector.ask_cache_mode()
        self._session  = session
        self._upgrader = WallUpgrader(session.clicker, _IMG_DIR)

    # ------------------------------------------------------------------
    #  Loot phase
    # ------------------------------------------------------------------

    def _run_loot_phase(self, attacks_per_cycle: int) -> None:
        print(f"[ORCH] Starting loot phase: {attacks_per_cycle} attack(s).")
        for i in range(attacks_per_cycle):
            print(f"\n{'='*48}")
            print(f"  ATTACK {i + 1} / {attacks_per_cycle}")
            print(f"{'='*48}")
            self._session.run(initial_wait=0.0)
            if i < attacks_per_cycle - 1:
                print("[ORCH] Preparing next attack...")
                time.sleep(1.5)
        print("[ORCH] Loot phase finished.")

    # ------------------------------------------------------------------
    #  Main loop
    # ------------------------------------------------------------------

    def run(self, attacks_per_cycle: int = 30) -> None:
        """
        Continuously run loot + upgrade cycles until no walls remain.

        Parameters
        ----------
        attacks_per_cycle : attacks to run before each wall upgrade attempt.
        """
        if self._session is None or self._upgrader is None:
            raise RuntimeError("Call setup() before run().")

        print("[ORCH] Starting in 5 seconds… switch to CoC window now.")
        time.sleep(5.0)

        cycle = 0
        while True:
            cycle += 1
            print(f"\n{'='*52}")
            print(f"  LOOT + WALL UPGRADE CYCLE {cycle}")
            print(f"{'='*52}")

            # 1) Farm loot
            self._run_loot_phase(attacks_per_cycle)

            # 2) Let game settle back at home screen
            print("[ORCH] Waiting 3 s for game to settle...")
            time.sleep(3.0)

            # 3) Upgrade walls
            gold_ok, elixir_ok = self._upgrader.run_full_cycle()

            if not gold_ok and not elixir_ok:
                print("[ORCH] No successful wall upgrades – no walls left to upgrade.")
                print("[ORCH] Stopping automation.")
                break

            print("[ORCH] Cycle complete. Starting next cycle shortly...")
            time.sleep(5.0)

        print("\n[ORCH] Automation finished. You can close this window.")

    # ------------------------------------------------------------------
    #  Debug menu
    # ------------------------------------------------------------------

    def debug_menu(self) -> None:
        """Interactive menu to test individual components."""
        if self._session is None or self._upgrader is None:
            raise RuntimeError("Call setup() before debug_menu().")

        options = {
            "1": ("Run ONE full attack",                  self._debug_single_attack),
            "2": ("Find & click Wall only (no upgrade)",  self._debug_find_wall),
            "3": ("GOLD wall upgrade only",               self._debug_gold_upgrade),
            "4": ("ELIXIR wall upgrade only",             self._debug_elixir_upgrade),
            "5": ("Full wall upgrade cycle (GOLD+ELIXIR)",self._debug_full_cycle),
        }

        while True:
            print("\n================ DEBUG MENU ================")
            for k, (label, _) in options.items():
                print(f"  {k}) {label}")
            print("  6) Exit")
            choice = input("Choose [1-6] (default 6): ").strip()
            if choice not in options:
                break
            _, fn = options[choice]
            fn()

    def _debug_single_attack(self) -> None:
        print("[DEBUG] Running one attack in 5 s...")
        time.sleep(5.0)
        self._session.run(initial_wait=0.0)

    def _debug_find_wall(self) -> None:
        print("[DEBUG] Finding Wall in 5 s...")
        time.sleep(5.0)
        self._upgrader._open_upgradables_window()
        found = self._upgrader._find_and_click_wall_entry()
        print(f"[DEBUG] Wall found: {found}")

    def _debug_gold_upgrade(self) -> None:
        print("[DEBUG] GOLD upgrade in 5 s...")
        time.sleep(5.0)
        print(f"[DEBUG] Result: {self._upgrader.upgrade_with_gold()}")

    def _debug_elixir_upgrade(self) -> None:
        print("[DEBUG] ELIXIR upgrade in 5 s...")
        time.sleep(5.0)
        print(f"[DEBUG] Result: {self._upgrader.upgrade_with_elixir()}")

    def _debug_full_cycle(self) -> None:
        print("[DEBUG] Full wall cycle in 5 s...")
        time.sleep(5.0)
        print(f"[DEBUG] Result: {self._upgrader.run_full_cycle()}")


# ===========================================================================
#  Entry point
# ===========================================================================

def _ask_num_heroes() -> int:
    try:
        raw = input("How many heroes are available? (0-4, default 4): ").strip()
        n   = int(raw) if raw else 4
    except ValueError:
        print("[WARN] Invalid input, defaulting to 4.")
        n = 4
    return max(0, min(4, n))


def _ask_mode() -> str:
    return input(
        "Select mode  [1 = full auto, 2 = debug]  (default 1): "
    ).strip()


def _ask_attacks_per_cycle() -> int:
    try:
        raw = input("How many attacks per cycle? (default 30): ").strip()
        n   = int(raw) if raw else 30
    except ValueError:
        print("[WARN] Invalid input, defaulting to 30.")
        n = 30
    return max(1, n)


def main() -> None:
    print("====================================================")
    print("   Auto Loot + Wall Upgrade")
    print("====================================================")
    print("  1) FULL AUTO  – attack N times, upgrade walls, repeat")
    print("  2) DEBUG MODE – manually test each component")
    print()

    bot = LootAndWallBot()
    bot.setup()

    mode = _ask_mode()

    if mode == "2":
        bot.debug_menu()
        return

    attacks_per_cycle = _ask_attacks_per_cycle()

    print(f"\n[ORCH] Configuration:")
    print(f"  Attacks per cycle : {attacks_per_cycle}")
    print(f"  Walls per GOLD    : {WallConfig.WALLS_PER_GOLD_UPGRADE}")
    print(f"  Walls per ELIXIR  : {WallConfig.WALLS_PER_ELIXIR_UPGRADE}")

    bot.run(attacks_per_cycle)


if __name__ == "__main__":
    main()

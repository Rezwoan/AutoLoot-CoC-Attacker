"""
auto_attack.py

Run N fully-automated Clash of Clans attacks using the Valkyrie/hero
strategy.  This script is the entry point; all logic lives in the
``core/`` package.

Usage
-----
    python auto_attack.py

or via start.bat.
"""

import os
import time

from core.attack_engine import AttackSession


# ---------------------------------------------------------------------------
#  Paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_IMG_DIR    = os.path.join(_SCRIPT_DIR, "img")


# ===========================================================================
#  AttackBot
# ===========================================================================

class AttackBot:
    """
    Orchestrates one or many back-to-back attacks.

    Responsibilities
    ----------------
    * Ask the user how many attacks to run.
    * Ask whether to use or refresh the button/position cache.
    * Delegate each individual attack to :class:`core.attack_engine.AttackSession`.
    """

    def __init__(self) -> None:
        self._session: AttackSession | None = None

    # ------------------------------------------------------------------
    #  Setup
    # ------------------------------------------------------------------

    def setup(self) -> None:
        """
        Load the location cache and ask the user how to proceed.
        Must be called once before :meth:`run`.
        """
        session = AttackSession(_IMG_DIR, cache_mode="update")
        session.detector.load_cache()
        session.detector.ask_cache_mode()
        self._session = session

    # ------------------------------------------------------------------
    #  Run
    # ------------------------------------------------------------------

    def run(self, num_attacks: int) -> None:
        """
        Execute *num_attacks* full attacks in sequence.

        Parameters
        ----------
        num_attacks : how many attacks to perform (minimum 1).
        """
        if self._session is None:
            raise RuntimeError("Call setup() before run().")

        num_attacks = max(1, num_attacks)
        print(f"\n[INFO] Running {num_attacks} attack(s).")

        for i in range(num_attacks):
            print(f"\n{'='*48}")
            print(f"  ATTACK {i + 1} / {num_attacks}")
            print(f"{'='*48}")

            # Only the very first attack gets the 5-second global wait
            wait = 5.0 if i == 0 else 0.0
            self._session.run(initial_wait=wait)

            if i < num_attacks - 1:
                print("[INFO] Preparing next attack...")
                time.sleep(1.5)

        print("\n[INFO] All attacks finished.")


# ===========================================================================
#  Entry point
# ===========================================================================

def _ask_num_attacks() -> int:
    try:
        raw = input("How many attacks do you want to run? (default 1): ").strip()
        n   = int(raw) if raw else 1
    except ValueError:
        print("[WARN] Invalid input, defaulting to 1.")
        n = 1
    return max(1, n)


def main() -> None:
    bot = AttackBot()
    bot.setup()
    num = _ask_num_attacks()
    bot.run(num)


if __name__ == "__main__":
    main()

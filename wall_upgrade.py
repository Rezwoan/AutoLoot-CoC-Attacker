"""
wall_upgrade.py

Automates wall upgrading in Clash of Clans.

Flow
----
1. Click **All Upgradable** button  → opens the scrollable upgrade list.
2. Scroll through the list, using OCR to find the word **"Wall"**.
3. Click on the Wall entry → enters wall upgrade mode.
4. Click **Select Multiple Walls** to enable multi-select.
5. Click **Upgrade with Gold** or **Upgrade with Elixir**.
6. Click **Confirm OK** to complete.

All positions come from ``config.json`` (set via the Setup Panel).
"""

import time
from typing import Any, Callable, Dict, Optional

from core.clicker import click, scroll_at
from core.config import load_config
from core.wall_detector import scroll_and_find_wall


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _pos(config: Dict[str, Any], key: str):
    """Return ``(x, y)`` from config positions or ``None``."""
    val = config["positions"].get(key)
    if val and isinstance(val, (list, tuple)) and len(val) == 2:
        return tuple(val)
    return None


# ---------------------------------------------------------------------------
#  Wall upgrade routine
# ---------------------------------------------------------------------------

def upgrade_walls(
    config: Optional[Dict[str, Any]] = None,
    resource: str = "gold",
    max_scrolls: int = 10,
    log: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Run one wall-upgrade cycle.

    Parameters
    ----------
    config : dict, optional
        Bot config.  Loaded from disk if not supplied.
    resource : str
        ``"gold"`` or ``"elixir"`` — which resource to use.
    max_scrolls : int
        How many times to scroll the upgrade list looking for Wall.
    log : callable, optional
        ``log(message)`` for status output. Defaults to ``print``.

    Returns
    -------
    bool
        ``True`` if wall was found and upgrade was attempted,
        ``False`` if wall was not found or a required position is missing.
    """
    if log is None:
        log = print

    if config is None:
        config = load_config()

    # ── Validate required positions ───────────────────────────────────
    upgradable = _pos(config, "wall_upgradable")
    scroll_pos = _pos(config, "wall_scroll_pos")
    select_multi = _pos(config, "wall_select_multi")
    gold = _pos(config, "wall_gold")
    elixir = _pos(config, "wall_elixir")
    ok_btn = _pos(config, "wall_ok")

    resource_btn = gold if resource == "gold" else elixir

    missing = []
    if not upgradable:
        missing.append("wall_upgradable")
    if not scroll_pos:
        missing.append("wall_scroll_pos")
    if not resource_btn:
        missing.append(f"wall_{resource}")
    if not ok_btn:
        missing.append("wall_ok")

    if missing:
        log(f"Missing positions: {', '.join(missing)}")
        return False

    # ── Step 1 — Open upgrade list ────────────────────────────────────
    log("Opening upgrade list...")
    click(*upgradable)
    time.sleep(1.0)

    # ── Step 2 — Scroll and find "Wall" ───────────────────────────────
    log("Searching for 'Wall' in upgrade list...")
    wall_pos = scroll_and_find_wall(
        scroll_x=scroll_pos[0],
        scroll_y=scroll_pos[1],
        max_scrolls=max_scrolls,
    )

    if not wall_pos:
        log("Wall not found in upgrade list.")
        return False

    log(f"Wall found at ({wall_pos[0]}, {wall_pos[1]})")

    # ── Step 3 — Click on the Wall entry ──────────────────────────────
    click(*wall_pos)
    time.sleep(0.8)

    # ── Step 4 — Select Multiple (if position is set) ─────────────────
    if select_multi:
        log("Clicking Select Multiple...")
        click(*select_multi)
        time.sleep(0.5)

    # ── Step 5 — Choose resource ──────────────────────────────────────
    log(f"Upgrading with {resource}...")
    click(*resource_btn)
    time.sleep(0.5)

    # ── Step 6 — Confirm ──────────────────────────────────────────────
    log("Confirming upgrade...")
    click(*ok_btn)
    time.sleep(0.5)

    log("Wall upgrade complete.")
    return True


# ---------------------------------------------------------------------------
#  Entry point (for standalone testing)
# ---------------------------------------------------------------------------

def main() -> None:
    """Run a single wall upgrade cycle with default settings."""
    import sys

    resource = "gold"
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("gold", "elixir"):
        resource = sys.argv[1].lower()

    print(f"Starting wall upgrade (resource={resource})...")
    print("You have 3 seconds to switch to the game window.\n")
    time.sleep(3)

    success = upgrade_walls(resource=resource)
    if success:
        print("\nDone!")
    else:
        print("\nWall upgrade failed. Check positions in the Setup Panel.")


if __name__ == "__main__":
    main()

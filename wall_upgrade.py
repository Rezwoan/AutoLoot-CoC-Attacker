"""
wall_upgrade.py

Automates wall upgrading in Clash of Clans.

Full Cycle
----------
1. Click **All Upgradable** button  → opens the scrollable upgrade list.
2. Scroll through the list, using template matching to find **"Wall"**.
3. Click on the Wall entry → enters wall upgrade mode.
4. Click **Select Multiple Walls** (upgrade more) to enable multi-select.
5. Click **Upgrade with Gold** → Confirm OK.
6. Re-open the upgrade list and find Wall again.
7. Click **Select Multiple Walls** again.
8. Click **Upgrade with Elixir** → Confirm OK.

Both resources are used in a single call to ``upgrade_walls_full_cycle()``.
All positions come from ``config.json`` (set via the Setup Panel).
"""

import os
import time
from typing import Any, Callable, Dict, Optional, Tuple

from core.clicker import click, scroll_at
from core.config import load_config
from core.wall_detector import scroll_and_find_wall

# Default template path (set via Setup Panel → Detection tab)
_WALL_TEMPLATE = os.path.join("img", "wall_text.png")


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _pos(config: Dict[str, Any], key: str) -> Optional[Tuple[int, int]]:
    """Return ``(x, y)`` from config positions or ``None``."""
    val = config["positions"].get(key)
    if val and isinstance(val, (list, tuple)) and len(val) == 2:
        return tuple(val)
    return None


def _open_upgrade_list_and_find_wall(
    upgradable: Tuple[int, int],
    scroll_pos: Tuple[int, int],
    max_scrolls: int,
    log: Callable,
) -> Optional[Tuple[int, int]]:
    """Click All Upgradable, scroll, and return Wall position or None."""
    log("Opening upgrade list...")
    click(*upgradable)
    time.sleep(1.0)

    if not os.path.isfile(_WALL_TEMPLATE):
        log(f"Wall template not found: {_WALL_TEMPLATE}")
        log("Capture it via Setup Panel → Detection tab → 'Wall Text'.")
        return None

    log("Searching for 'Wall' in upgrade list...")
    wall_pos = scroll_and_find_wall(
        template_path=_WALL_TEMPLATE,
        scroll_x=scroll_pos[0],
        scroll_y=scroll_pos[1],
        max_scrolls=max_scrolls,
    )

    if not wall_pos:
        log("Wall not found in upgrade list.")
    else:
        log(f"Wall found at ({wall_pos[0]}, {wall_pos[1]})")

    return wall_pos


def _do_single_upgrade(
    wall_pos: Tuple[int, int],
    select_multi: Optional[Tuple[int, int]],
    resource_btn: Tuple[int, int],
    ok_btn: Tuple[int, int],
    resource_name: str,
    log: Callable,
) -> bool:
    """Click Wall → Select Multiple → Resource → OK for one resource."""
    # Click on the Wall entry
    log("Clicking Wall entry...")
    click(*wall_pos)
    time.sleep(0.8)

    # Select Multiple Walls (click 3 times to queue more upgrades)
    if select_multi:
        log("Clicking Select Multiple (×3)...")
        for _ in range(3):
            click(*select_multi)
            time.sleep(0.3)

    # Choose resource
    log(f"Upgrading with {resource_name}...")
    click(*resource_btn)
    time.sleep(0.5)

    # Confirm
    log("Confirming upgrade...")
    click(*ok_btn)
    time.sleep(0.8)

    log(f"Wall upgrade with {resource_name} complete.")
    return True


# ---------------------------------------------------------------------------
#  Full wall upgrade cycle
# ---------------------------------------------------------------------------

def upgrade_walls_full_cycle(
    config: Optional[Dict[str, Any]] = None,
    max_scrolls: int = 10,
    log: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Run a **full** wall-upgrade cycle: Gold first, then Elixir.

    Steps per resource:
      open list → scroll & find Wall → click Wall → select multiple →
      upgrade with resource → confirm OK

    Parameters
    ----------
    config : dict, optional
        Bot config.  Loaded from disk if not supplied.
    max_scrolls : int
        How many times to scroll the upgrade list looking for Wall.
    log : callable, optional
        ``log(message)`` for status output. Defaults to ``print``.

    Returns
    -------
    bool
        ``True`` if at least one upgrade was performed,
        ``False`` if Wall was never found or required positions are missing.
    """
    if log is None:
        log = print

    if config is None:
        config = load_config()

    # ── Validate required positions ───────────────────────────────────
    upgradable  = _pos(config, "wall_upgradable")
    scroll_pos  = _pos(config, "wall_scroll_pos")
    select_multi = _pos(config, "wall_select_multi")
    gold_btn    = _pos(config, "wall_gold")
    elixir_btn  = _pos(config, "wall_elixir")
    ok_btn      = _pos(config, "wall_ok")

    missing = []
    if not upgradable:   missing.append("wall_upgradable")
    if not scroll_pos:   missing.append("wall_scroll_pos")
    if not gold_btn:     missing.append("wall_gold")
    if not elixir_btn:   missing.append("wall_elixir")
    if not ok_btn:       missing.append("wall_ok")

    if missing:
        log(f"Missing positions: {', '.join(missing)}")
        return False

    any_success = False

    # ── Pass 1 — Upgrade with GOLD ────────────────────────────────────
    log("═══ Pass 1: Upgrade with Gold ═══")
    wall_pos = _open_upgrade_list_and_find_wall(
        upgradable, scroll_pos, max_scrolls, log,
    )
    if wall_pos:
        _do_single_upgrade(
            wall_pos, select_multi, gold_btn, ok_btn, "Gold", log,
        )
        any_success = True
        time.sleep(1.0)
    else:
        log("Skipping Gold upgrade — Wall not found.")

    # ── Pass 2 — Upgrade with ELIXIR ─────────────────────────────────
    log("═══ Pass 2: Upgrade with Elixir ═══")
    wall_pos = _open_upgrade_list_and_find_wall(
        upgradable, scroll_pos, max_scrolls, log,
    )
    if wall_pos:
        _do_single_upgrade(
            wall_pos, select_multi, elixir_btn, ok_btn, "Elixir", log,
        )
        any_success = True
    else:
        log("Skipping Elixir upgrade — Wall not found.")

    # ── Summary ───────────────────────────────────────────────────────
    if any_success:
        log("Full wall upgrade cycle finished.")
    else:
        log("No walls were upgraded this cycle.")

    return any_success


# ---------------------------------------------------------------------------
#  Single-resource upgrade (kept for flexibility / standalone use)
# ---------------------------------------------------------------------------

def upgrade_walls(
    config: Optional[Dict[str, Any]] = None,
    resource: str = "gold",
    max_scrolls: int = 10,
    log: Optional[Callable[[str], None]] = None,
) -> bool:
    """
    Run a **single** wall-upgrade pass with one resource.

    Use ``upgrade_walls_full_cycle`` for the standard Gold+Elixir flow.
    """
    if log is None:
        log = print

    if config is None:
        config = load_config()

    upgradable  = _pos(config, "wall_upgradable")
    scroll_pos  = _pos(config, "wall_scroll_pos")
    select_multi = _pos(config, "wall_select_multi")
    resource_btn = _pos(config, f"wall_{resource}")
    ok_btn       = _pos(config, "wall_ok")

    missing = []
    if not upgradable:   missing.append("wall_upgradable")
    if not scroll_pos:   missing.append("wall_scroll_pos")
    if not resource_btn: missing.append(f"wall_{resource}")
    if not ok_btn:       missing.append("wall_ok")

    if missing:
        log(f"Missing positions: {', '.join(missing)}")
        return False

    wall_pos = _open_upgrade_list_and_find_wall(
        upgradable, scroll_pos, max_scrolls, log,
    )
    if not wall_pos:
        return False

    return _do_single_upgrade(
        wall_pos, select_multi, resource_btn, ok_btn, resource.title(), log,
    )


# ---------------------------------------------------------------------------
#  Entry point (for standalone testing)
# ---------------------------------------------------------------------------

def main() -> None:
    """Run a full wall upgrade cycle (Gold + Elixir)."""
    print("Starting full wall upgrade cycle (Gold + Elixir)...")
    print("You have 3 seconds to switch to the game window.\n")
    time.sleep(3)

    success = upgrade_walls_full_cycle()
    if success:
        print("\nDone!")
    else:
        print("\nWall upgrade failed. Check positions in the Setup Panel.")


if __name__ == "__main__":
    main()

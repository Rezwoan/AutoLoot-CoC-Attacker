"""
attack.py

Full attack automation for Clash of Clans.

Single Attack Cycle
-------------------
1.  **Zoom out**       — centre mouse + scroll down.
2.  **Attack menu**    — click the Attack button.
3.  **Find a Match**   — click Find Match.
4.  **Confirm attack** — click Confirm / Search.
5.  **Deploy spells**  — click spell slot, then drop at 3 locations.
6.  **Deploy siege**   — click siege slot, then drop at siege position.
7.  **Deploy troops**  — click troop slot, then distribute *troop_count*
     taps evenly across 4 deployment edges.
8.  **Deploy heroes**  — for each hero slot, click slot then deploy pos.
9.  **Activate heroes** — click each hero slot again (ability).
10. **Wait for 50 %**  — poll for the 50 % template. If detected, wait
     3 s extra then surrender.  If 90 s elapse without 50 %, surrender.
11. **Surrender → OK → Return Home**.

After the cycle, the caller (``setup_panel._bot_loop``) decides whether
to do a wall upgrade or loop another attack.
"""

import math
import os
import random
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

import pyautogui

from core.clicker import click
from core.config import load_config
from core.detector import find_on_screen, wait_for, is_visible
from core.screen import get_screen_size

_IMG_DIR = "img"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _pos(config: Dict[str, Any], key: str) -> Optional[Tuple[int, int]]:
    """Return ``(x, y)`` from config or ``None``."""
    val = config["positions"].get(key)
    if val and isinstance(val, (list, tuple)) and len(val) == 2:
        return tuple(val)
    return None


def _tpl(config: Dict[str, Any], key: str) -> Optional[str]:
    """Return full path to a template image, or ``None``."""
    fname = config["templates"].get(key)
    if fname:
        path = os.path.join(_IMG_DIR, fname)
        if os.path.isfile(path):
            return path
    return None


def _interpolate_positions(
    p1: Tuple[int, int],
    p2: Tuple[int, int],
    count: int,
) -> List[Tuple[int, int]]:
    """
    Return *count* evenly-spaced points along the line from *p1* to *p2*.
    """
    if count <= 1:
        mx = (p1[0] + p2[0]) // 2
        my = (p1[1] + p2[1]) // 2
        return [(mx, my)]
    points = []
    for i in range(count):
        t = i / (count - 1)
        x = int(p1[0] + t * (p2[0] - p1[0]))
        y = int(p1[1] + t * (p2[1] - p1[1]))
        points.append((x, y))
    return points


# ---------------------------------------------------------------------------
#  Zoom out
# ---------------------------------------------------------------------------

def zoom_out(log: Callable) -> None:
    """Move mouse to screen centre and scroll down to zoom out."""
    sw, sh = get_screen_size()
    cx, cy = sw // 2, sh // 2
    pyautogui.moveTo(cx, cy, duration=0.15)
    time.sleep(0.2)
    for _ in range(5):
        pyautogui.scroll(-3)
        time.sleep(0.15)
    log("Zoomed out")
    time.sleep(0.3)


# ---------------------------------------------------------------------------
#  Single attack cycle
# ---------------------------------------------------------------------------

def run_single_attack(
    config: Dict[str, Any],
    log: Callable[[str], None],
    stop_event: threading.Event,
    pause_event: threading.Event,
) -> bool:
    """
    Execute one full attack cycle.

    Returns ``True`` if 50 %+ destruction was achieved, ``False`` otherwise.
    """

    def _check_stop() -> bool:
        return stop_event.is_set()

    def _honour_pause() -> None:
        while pause_event.is_set() and not stop_event.is_set():
            time.sleep(0.2)

    # ── Zoom out ──────────────────────────────────────────────────────
    zoom_out(log)
    if _check_stop():
        return False

    # ── 1. Click Attack menu ──────────────────────────────────────────
    attack_menu = _pos(config, "attack_menu")
    if not attack_menu:
        log("✗ attack_menu position missing")
        return False

    log("Clicking Attack menu...")
    click(*attack_menu)
    time.sleep(1.0)
    _honour_pause()
    if _check_stop():
        return False

    # ── 2. Find a Match ───────────────────────────────────────────────
    find_match = _pos(config, "find_match")
    if not find_match:
        log("✗ find_match position missing")
        return False

    log("Clicking Find Match...")
    click(*find_match)
    time.sleep(1.0)
    _honour_pause()
    if _check_stop():
        return False

    # ── 3. Confirm attack ─────────────────────────────────────────────
    confirm = _pos(config, "confirm_attack")
    if not confirm:
        log("✗ confirm_attack position missing")
        return False

    log("Confirming attack...")
    click(*confirm)
    time.sleep(3.0)  # wait for battle to load
    _honour_pause()
    if _check_stop():
        return False

    # ── 4. Deploy spells ──────────────────────────────────────────────
    spell_slot = _pos(config, "spell")
    spell_targets = [
        ("left",   _pos(config, "spell_target_left")),
        ("center", _pos(config, "spell_target_center")),
        ("right",  _pos(config, "spell_target_right")),
    ]
    spell_targets = [(name, pos) for name, pos in spell_targets if pos]
    spell_count = config.get("settings", {}).get("spell_count", 11)
    siege_deploy = _pos(config, "siege_deploy")

    if spell_slot and spell_targets and spell_count > 0:
        num_targets = len(spell_targets)

        # Sort targets by distance to siege deploy (closest last = gets remainder)
        if siege_deploy:
            def _dist(t):
                pos = t[1]
                return math.hypot(pos[0] - siege_deploy[0], pos[1] - siege_deploy[1])
            spell_targets.sort(key=_dist, reverse=True)  # farthest first
            # Now closest to siege is last — it gets the smaller share
            # We want closest to get MORE, so: closest first for remainder
            # Reverse: closest first gets extra via remainder distribution
            spell_targets.sort(key=_dist)  # closest first

        # Distribute: e.g. 11 across 3 → 4+4+3, closest side gets extra
        base = spell_count // num_targets
        remainder = spell_count % num_targets
        distribution = []
        for i, (name, pos) in enumerate(spell_targets):
            count = base + (1 if i < remainder else 0)
            distribution.append((name, pos, count))

        log(f"Deploying {spell_count} spells: {', '.join(f'{c}×{n}' for n, _, c in distribution)}")
        click(*spell_slot)
        time.sleep(0.3)
        for name, pos, count in distribution:
            for _ in range(count):
                click(*pos, duration=0.02, delay=0.08)
            time.sleep(0.15)
        time.sleep(0.3)
    _honour_pause()
    if _check_stop():
        return False

    # ── 5. Deploy siege ───────────────────────────────────────────────
    siege_slot = _pos(config, "siege")

    if siege_slot and siege_deploy:
        log("Deploying siege machine...")
        click(*siege_slot)
        time.sleep(0.3)
        click(*siege_deploy)
        time.sleep(0.3)
    _honour_pause()
    if _check_stop():
        return False

    # ── 6. Deploy troops ──────────────────────────────────────────────
    troop_slot = _pos(config, "troop")
    troop_count = config.get("settings", {}).get("troop_count", 40)

    # Gather the 4 deployment edges (each edge = 2 corner points)
    edges = [
        ("deploy_left_up",     "deploy_left_left"),    # left-top  → left-left
        ("deploy_left_left",   "deploy_left_bottom"),  # left-left → left-bottom
        ("deploy_right_up",    "deploy_right_right"),  # right-top → right-right
        ("deploy_right_right", "deploy_right_bottom"), # right-right → right-bottom
    ]

    edge_pairs: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
    for k1, k2 in edges:
        p1, p2 = _pos(config, k1), _pos(config, k2)
        if p1 and p2:
            edge_pairs.append((p1, p2))

    if troop_slot and edge_pairs:
        num_sides = len(edge_pairs)
        base_per_side = troop_count // num_sides
        remainder = troop_count % num_sides

        log(f"Deploying {troop_count} troops across {num_sides} sides...")
        click(*troop_slot)
        time.sleep(0.3)

        for i, (p1, p2) in enumerate(edge_pairs):
            # Distribute remainder across first few sides
            side_count = base_per_side + (1 if i < remainder else 0)
            if side_count <= 0:
                continue

            positions = _interpolate_positions(p1, p2, side_count)
            for px, py in positions:
                if _check_stop():
                    return False
                click(px, py, duration=0.02, delay=0.03)

        time.sleep(0.3)
        log("Troops deployed")
    _honour_pause()
    if _check_stop():
        return False

    # ── 7. Deploy heroes ──────────────────────────────────────────────
    hero_slots = []
    for n in range(1, 5):
        slot = _pos(config, f"hero_{n}")
        deploy = _pos(config, f"hero_{n}_deploy")
        if slot and deploy:
            hero_slots.append((n, slot, deploy))

    if hero_slots:
        log(f"Deploying {len(hero_slots)} heroes...")
        for n, slot, deploy in hero_slots:
            click(*slot)
            time.sleep(0.3)
            click(*deploy)
            time.sleep(0.3)

    _honour_pause()
    if _check_stop():
        return False

    # ── 8. Activate hero abilities ────────────────────────────────────
    if hero_slots:
        time.sleep(1.5)  # small wait before activating
        log("Activating hero abilities...")
        for n, slot, _ in hero_slots:
            click(*slot)
            time.sleep(0.3)

    _honour_pause()
    if _check_stop():
        return False

    # ── 9. Wait for 50 % destruction (90 s timeout) ──────────────────
    fifty_tpl = _tpl(config, "fifty_percent")
    got_fifty = False

    if fifty_tpl:
        log("Waiting for 50% destruction (90 s timeout)...")
        start = time.time()
        timeout = 90.0

        while time.time() - start < timeout:
            if _check_stop():
                break
            _honour_pause()
            if is_visible(fifty_tpl, confidence=0.93):
                got_fifty = True
                elapsed = time.time() - start
                wait = random.uniform(5.0, 10.0)
                log(f"✓ 50% detected after {elapsed:.0f}s — waiting {wait:.1f}s...")
                time.sleep(wait)
                break
            time.sleep(1.0)

        if not got_fifty and not _check_stop():
            elapsed = time.time() - start
            log(f"✗ 50% not reached after {elapsed:.0f}s — surrendering")
    else:
        log("⚠ No 50% template — waiting 30 s then surrendering")
        time.sleep(30.0)

    if _check_stop():
        return got_fifty

    # ── 10. Surrender → OK ────────────────────────────────────────────
    surrender = _pos(config, "surrender")
    confirm_ok = _pos(config, "confirm_ok")

    if surrender:
        log("Surrendering...")
        click(*surrender)
        time.sleep(1.0)

    if confirm_ok:
        log("Clicking OK...")
        click(*confirm_ok)
        time.sleep(2.0)

    # ── 11. Return Home ───────────────────────────────────────────────
    return_tpl = _tpl(config, "return_home")

    if return_tpl:
        log("Waiting for Return Home button...")
        pos = wait_for(return_tpl, timeout=30.0, interval=1.0, confidence=0.85)
        if pos:
            click(*pos)
            log("Returning home...")
            time.sleep(3.0)
        else:
            log("⚠ Return Home not found — continuing")
    else:
        log("⚠ No return_home template — waiting 5 s")
        time.sleep(5.0)

    return got_fifty


# ---------------------------------------------------------------------------
#  Multi-attack runner  (called from the bot loop)
# ---------------------------------------------------------------------------

def run_attacks(
    config: Dict[str, Any],
    total: int,
    stop_event: threading.Event,
    pause_event: threading.Event,
    wall_enabled: bool = False,
    wall_every: int = 5,
    on_attack_done: Optional[Callable[[int, bool], None]] = None,
    log: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Run *total* attack cycles, optionally doing wall upgrades.

    Parameters
    ----------
    on_attack_done : callable(attack_number, got_fifty)
        Called after each attack finishes.
    """
    if log is None:
        log = print

    for i in range(1, total + 1):
        if stop_event.is_set():
            break

        # Honour pause
        while pause_event.is_set() and not stop_event.is_set():
            time.sleep(0.2)

        if stop_event.is_set():
            break

        log(f"━━━ Attack {i}/{total} ━━━")
        got_fifty = run_single_attack(config, log, stop_event, pause_event)

        if on_attack_done:
            on_attack_done(i, got_fifty)

        # Wall upgrade check
        if wall_enabled and i % wall_every == 0 and not stop_event.is_set():
            log("⚒ Running wall upgrade cycle...")
            try:
                from wall_upgrade import upgrade_walls_full_cycle
                upgrade_walls_full_cycle(config=config, log=log)
            except Exception as exc:
                log(f"Wall upgrade error: {exc}")

        if stop_event.is_set():
            break

        # Brief pause between attacks
        time.sleep(2.0)

    log("All attacks completed." if not stop_event.is_set() else "Bot stopped.")

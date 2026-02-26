"""
core/config.py

Configuration management for the CoC Bot.

Defines the schema of all configurable positions and detection templates,
and handles loading / saving ``config.json``.
"""

import json
import os
from typing import Any, Dict

CONFIG_FILE = "config.json"

# ---------------------------------------------------------------------------
#  Schema — positions the user clicks to set
# ---------------------------------------------------------------------------
# Ordered dict of {group_label: {key: human_label, ...}, ...}

POSITION_SCHEMA: Dict[str, Dict[str, str]] = {
    "Attack UI": {
        "attack_menu":    "Attack Menu Button",
        "find_match":     "Find Match Button",
        "confirm_attack": "Confirm Attack / Search",
        "surrender":      "Surrender Button",
        "confirm_ok":     "Confirm OK Button",
    },
    "Army Bar": {
        "troop":  "Main Troop",
        "spell":  "Spell",
        "siege":  "Siege Machine",
        "hero_1": "Hero Slot 1",
        "hero_2": "Hero Slot 2",
        "hero_3": "Hero Slot 3",
        "hero_4": "Hero Slot 4",
        "hero_5": "Hero Slot 5",
    },
    "Deployment Edges": {
        "deploy_left_up":      "Left Edge — Top",
        "deploy_left_left":    "Left Edge — Left",
        "deploy_left_bottom":  "Left Edge — Bottom",
        "deploy_right_up":     "Right Edge — Top",
        "deploy_right_right":  "Right Edge — Right",
        "deploy_right_bottom": "Right Edge — Bottom",
    },
    "Spell Targets": {
        "spell_target_left":  "Spell Drop — Left",
        "spell_target_right": "Spell Drop — Right",
    },
    "Wall Upgrade": {
        "wall_upgradable":   "All Upgradable Button",
        "wall_select_multi": "Select Multiple Walls",
        "wall_gold":         "Upgrade with Gold",
        "wall_elixir":       "Upgrade with Elixir",
        "wall_ok":           "Upgrade Confirm OK",
    },
}

# ---------------------------------------------------------------------------
#  Schema — detection template images (captured via screenshot region)
# ---------------------------------------------------------------------------

TEMPLATE_SCHEMA: Dict[str, Dict[str, str]] = {
    "Detection Images": {
        "next_button":   "Next Button",
        "return_home":   "Return Home Button",
        "fifty_percent": "50% Destruction",
    },
}


# ---------------------------------------------------------------------------
#  Config helpers
# ---------------------------------------------------------------------------

def default_config() -> Dict[str, Any]:
    """Return a fresh config with every position and template set to ``None``."""
    positions: Dict[str, Any] = {}
    for group in POSITION_SCHEMA.values():
        for key in group:
            positions[key] = None

    templates: Dict[str, Any] = {}
    for group in TEMPLATE_SCHEMA.values():
        for key in group:
            templates[key] = None  # filename when set

    return {
        "positions": positions,
        "templates": templates,
    }


def load_config(path: str = CONFIG_FILE) -> Dict[str, Any]:
    """Load config from *path*, merged with defaults for any missing keys."""
    config = default_config()

    if os.path.isfile(path):
        try:
            with open(path, "r") as fh:
                saved = json.load(fh)
            for section in ("positions", "templates"):
                if section in saved and isinstance(saved[section], dict):
                    for key, val in saved[section].items():
                        if key in config[section]:
                            config[section][key] = val
        except (json.JSONDecodeError, Exception) as exc:
            print(f"[WARN] Failed to load config: {exc}")

    return config


def save_config(config: Dict[str, Any], path: str = CONFIG_FILE) -> None:
    """Persist *config* to *path* as pretty-printed JSON."""
    with open(path, "w") as fh:
        json.dump(config, fh, indent=2)

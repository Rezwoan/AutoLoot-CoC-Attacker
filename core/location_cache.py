import json
import os

# JSON file stored in the project root (one level above this module's directory)
CACHE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "locations_cache.json"
)


def load_locations() -> dict:
    """
    Load cached locations from JSON file.

    Returns an empty dict if file is missing or invalid.
    """
    if not os.path.isfile(CACHE_FILE):
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}


def save_locations(data: dict) -> None:
    """
    Save locations dict to JSON file.
    """
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save locations cache: {e}")

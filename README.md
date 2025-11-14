# AutoLoot CoC Attacker 🛡️⚔️

Automated Clash of Clans attack script using Python and `pyautogui`.

This project controls your mouse and keyboard to:

- Zoom out the village
- Click **Attack → Find Match**
- Detect when a **base has been found** using screen image recognition
- Deploy:
  - Earthquake spells
  - Siege machine
  - Valkyries along a custom-defined path
  - Two heroes + automatically trigger their abilities
- Monitor the raid until **50% destruction**
- **Surrender and return home** automatically
- Repeat for a **user-defined number of attacks**

> ⚠️ **Disclaimer:**  
> This project is for learning and personal use. Automating gameplay may violate the game’s Terms of Service and could result in penalties on your account. Use at your own risk.

---

## 📁 Project Structure

Recommended layout:

```text
AutoLoot/
├─ auto_attack.py      # Main script that runs full attacks in a loop
├─ imageRec.py         # Screen/image recognition helpers (NEXT & 50% detection)
├─ next.png            # Template image of the "NEXT" button
├─ five.png            # Template image of the "5" from the % (for 50% detection)
└─ README.md           # This file
```

---

## 🔧 What Each Script Does

### `imageRec.py`

Handles **image recognition** and exposes a clean API:

- Detects if the **NEXT** button is visible → means a base has been found.
- Detects if **50% destruction** has been reached by matching a `five.png` template in a small region of the screen.
- Exports:

```python
def get_game_status() -> dict:
    # {
    #   "next_button": True/False,
    #   "fifty_percent": True/False
    # }
```

`auto_attack.py` uses this function to know when to start deploying troops and when to surrender.

> Uses `pyautogui` for screenshots and optionally `OpenCV` + `NumPy` for more robust matching.

---

### `auto_attack.py`

The **main attack logic**:

- Asks: **“How many attacks do you want to run?”**
- For each attack:

  1. **Zooms out** fully.
  2. Clicks **Attack → Find Match**.
  3. Waits until `get_game_status()["next_button"] == True`.
  4. Waits a short moment so the troop bar is fully loaded.
  5. **Casts Earthquake spells** at three specific battlefield locations.
  6. **Deploys Siege Machine** at a predefined left-side location.
  7. **Deploys 42 Valkyries** along four diagonal/edge paths using evenly spaced points:
     - `LEFT_BOTTOM → LEFT_LEFT`
     - `LEFT_LEFT → LEFT_UP`
     - `RIGHT_UP → RIGHT_RIGHT`
     - `RIGHT_RIGHT → RIGHT_BOTTOM`
  8. **Deploys two heroes**:
     - Hero 1 (e.g. Warden): midpoint of `LEFT_LEFT → LEFT_BOTTOM`
     - Hero 2 (e.g. Champion): midpoint of `RIGHT_RIGHT → RIGHT_BOTTOM`
  9. After a short delay, **clicks the hero bar buttons again** to activate both abilities.
  10. Uses `get_game_status()` to wait until **50% destruction**.
  11. Clicks **Surrender → Confirm OK → Return Home**.
  12. Moves on to the next attack (if any).

All troop/spell/hero selection is done **by clicking on their bar positions**, not by keypresses.

---

## ✅ Requirements

- **OS:** Windows (required for some parts, and for stable `pyautogui` usage with these coordinates)
- **Python:** 3.8+ recommended

### Python Packages

Install via:

```bash
pip install pyautogui opencv-python numpy pillow
```

- `pyautogui` – mouse/keyboard control & screenshots
- `opencv-python` – template matching for the “5” image (50% detection)
- `numpy` – image array handling
- `Pillow` – used internally by `pyautogui` for screenshots

> `winsound` (for beeps) is part of the standard library on Windows and used inside `imageRec.py` when run directly as a monitor tool.

---

## 🖥️ Screen Setup

This project assumes:

- Resolution: **1920 × 1200**
- Game window is **not moved or resized** from the layout used when coordinates were recorded.
- UI scale / layout is the same as when the coordinates were captured.

If your resolution or layout is different, you’ll need to **re-capture coordinates** and update the constants in `auto_attack.py` and `imageRec.py`.

---

## 🎯 Key Coordinates

### Troop / Spell / Hero Bar (bottom)

These are used to **select** things before deploying them on the battlefield:

```python
VALKARIE_BUTTON = (520, 1140)
SIEGE_BUTTON    = (617, 1132)
HERO1_BUTTON    = (711, 1136)  # Grand Warden
HERO2_BUTTON    = (783, 1146)  # Royal Champion
EARTHQUAKE_BUTTON = (888, 1142)
```

### Battlefield Deployment Geometry

Used for Valkyries, siege and heroes:

```python
LEFT_LEFT    = (181, 592)
LEFT_BOTTOM  = (823, 1075)
RIGHT_BOTTOM = (1156, 1075)
RIGHT_RIGHT  = (1787, 590)
RIGHT_UP     = (1070, 60)
LEFT_UP      = (878, 70)
```

Lines for Valkyrie deployment (evenly spaced points):

1. `LEFT_BOTTOM  → LEFT_LEFT`
2. `LEFT_LEFT    → LEFT_UP`
3. `RIGHT_UP     → RIGHT_RIGHT`
4. `RIGHT_RIGHT  → RIGHT_BOTTOM`

Earthquake target positions:

```python
LEFT_EARTH   = (635, 567)   # 3 quakes
RIGHT_EARTH  = (1245, 581)  # 4 quakes
BUTTON_EARTH = (951, 783)   # 4 quakes
```

Attack buttons:

```python
ATTACK_BUTTON      = (126, 1092)
FIND_MATCH         = (301, 847)
SURRENDER_BUTTON   = (117, 1021)
CONFIRM_OK_BUTTON  = (1170, 763)
RETURN_HOME_BUTTON = (945, 1025)
```

If *anything* clicks slightly off in your setup, adjust these coordinates.

---

## 📸 Template Images

Two images are required next to `imageRec.py`:

- `next.png` – cropped image of the **NEXT** button.
- `five.png` – cropped grayscale-ish image of the **“5”** from the % destruction text (used to detect **50%+**).

Make sure:

- They are captured at your actual in-game resolution.
- You don’t scale the game window after capturing them.
- File names match exactly: `next.png` and `five.png`.

---

## 🚀 Usage

1. **Clone or download** this repository.

2. (Optional but recommended) create a virtual environment:

   ```bash
   python -m venv myenv
   myenv\Scripts\activate
   pip install pyautogui opencv-python numpy pillow
   ```

3. Place `next.png` and `five.png` in the project folder.

4. Make sure your Clash of Clans window is open and matches the resolution/layout used for capturing the coordinates.

5. Run:

   ```bash
   python auto_attack.py
   ```

6. The script will ask:

   ```text
   How many attacks do you want to run? (default 1):
   ```

   Enter a number (e.g. `5`) and press Enter.

7. Quickly switch to the game window. The script will:

   - Zoom out
   - Start attacks
   - Deploy spells/troops/heroes
   - Trigger hero abilities
   - Surrender at 50%
   - Loop until all requested attacks are done

> 🔴 At any time, move your mouse to a corner of the screen to trigger `pyautogui.FAILSAFE` and **abort** the script.

---

## 🧪 Troubleshooting

**Nothing is being clicked correctly**

- Check your **resolution** (must match what the coordinates were captured on).
- Make sure Windows scaling (DPI) isn’t changing the click positions.
- Adjust problem coordinates in `auto_attack.py` or `imageRec.py`.

**Base never detected (stuck on “Searching for base…”)**

- Re-capture **`next.png`**.
- Confirm that the NEXT button looks identical in color/shape to your template.
- Try lowering `DETECTION_CONFIDENCE_NEXT` slightly in `imageRec.py` (if using OpenCV confidence).

**50% never detected**

- Re-capture **`five.png`** more tightly around the “5”.
- Check the search region in `imageRec.py` matches where `% destruction` appears on your screen.
- Adjust `FIFTY_DETECTION_THRESHOLD` if needed.

**Hero abilities not triggering**

- Make sure `HERO1_BUTTON` and `HERO2_BUTTON` actually point to the hero icons on the bar.
- Abilities are triggered by clicking those same buttons again after a delay.

---

## ⚙️ Customization Ideas

- Change number of Valkyries deployed or spacing logic.
- Add conditions to **skip bad bases** (e.g. based on certain layouts, later if you add more image recognition).
- Modify delays (`time.sleep` values) to match your PC speed and network conditions.
- Add logging to a file instead of just printing to console.

---


## 🙌 Credits

- Built with **Python** and **pyautogui**.
- Image detection powered by **OpenCV** and **NumPy**.
- Coordinates & behavior tuned specifically for one player’s setup and then generalized.

Feel free to fork, tweak, and adapt this for your own layout.


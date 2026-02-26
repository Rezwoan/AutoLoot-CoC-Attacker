<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/OpenCV-4.8+-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" />
  <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" />
  <img src="https://img.shields.io/badge/Status-Active-00C853?style=for-the-badge" />
</p>

<h1 align="center">⚔️ AutoLoot — CoC Attack & Wall Bot</h1>

<p align="center">
  <b>Fully automated Clash of Clans farming bot</b><br/>
  <sub>Auto-attack · Smart troop deployment · Wall upgrades · Zero hardcoded positions</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/dynamic-positions-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/template_matching-cv2-green?style=flat-square" />
  <img src="https://img.shields.io/badge/overlay-live_stats-orange?style=flat-square" />
</p>

---

## 🎯 What It Does

AutoLoot automates the tedious farming loop in Clash of Clans — finding matches, deploying your army, grabbing loot, and upgrading walls — all while you sit back.

> **Everything is dynamic.** No hardcoded coordinates, no resolution lock-in.  
> You click once to set each position, and the bot remembers.

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🗡️ Attack Engine
- **Full attack cycle** — zoom out → find match → deploy → surrender → return home
- **Smart spell deployment** — distributes your spell count across 3 drop zones, with more spells landing near the siege machine
- **4-edge troop spread** — drops troops evenly across all 4 deployment sides with calculated positions
- **Hero deployment + ability activation** — 4 hero slots with auto-ability trigger
- **Siege machine deployment** — separate deploy position
- **50% detection** — template matching with 93% confidence, waits 5–10s before surrendering
- **90s safety timeout** — auto-surrenders if 50% isn't reached

</td>
<td width="50%">

### 🧱 Wall Upgrade
- **Full Gold + Elixir cycle** — opens upgrade list → finds Wall → upgrades with Gold → repeats for Elixir
- **Drag-scroll detection** — click-hold-drag scrolling that works in emulators
- **Template matching** — finds "Wall" text with 90%+ confidence (no OCR)
- **Multi-select** — clicks "Select Multiple" 3× per cycle
- **Auto-trigger** — wall upgrades every N attacks (configurable)

</td>
</tr>
</table>

### 🖥️ Setup Panel

| Tab | Purpose |
|-----|---------|
| **Positions** | Click-to-set all button/deploy positions (scrollable) |
| **Detection** | Capture or paste template images for matching |
| **Control** | Attack count, troop/spell count, wall settings, Start/Stop |
| **Test** | Test detection, click positions, wall template matching |

### 🔲 Live Overlay
- Compact draggable stats bar (upper-left corner)
- Shows: `Attacks: 3/10 | ✓50%: 2 | Left: 7`
- **F6 hotkey** — toggle panel (bot pauses when panel is open)

---

## 📂 Project Structure

```
AutoLoot-CoC-Attacker/
├── setup_panel.py          # 🖥️  Tabbed GUI — positions, detection, control, test
├── attack.py               # ⚔️  Full attack cycle engine
├── wall_upgrade.py         # 🧱  Wall upgrade automation (Gold + Elixir)
├── core/
│   ├── config.py           # ⚙️  Schema + JSON persistence (config.json)
│   ├── detector.py         # 🔍  cv2.matchTemplate detection engine
│   ├── wall_detector.py    # 🧱  Template-based wall finder + drag-scroll
│   ├── clicker.py          # 🖱️  Mouse click/drag/scroll wrappers
│   └── screen.py           # 📐  Screen size utilities
├── img/                    # 🖼️  Captured template images (auto-generated)
├── config.json             # 💾  Your saved positions & settings (auto-generated)
├── requirements.txt        # 📦  Python dependencies
└── tesseract-ocr-w64-setup-5.5.0.20241111.exe  # 📥  Bundled Tesseract installer
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **Clash of Clans** running in an emulator (BlueStacks, LDPlayer, etc.)

### 1️⃣ Clone the Repo

```bash
git clone https://github.com/Rezwoan/AutoLoot-CoC-Attacker.git
cd AutoLoot-CoC-Attacker
```

### 2️⃣ Install Tesseract OCR

Run the bundled installer:
```
tesseract-ocr-w64-setup-5.5.0.20241111.exe
```
> Install to the default path: `C:\Program Files\Tesseract-OCR`

### 3️⃣ Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Launch the Setup Panel

```bash
python setup_panel.py
```

---

## ⚙️ Setup Guide

### Step 1 — Set Positions

Go to the **Positions** tab and click each button to set its location:

| Group | What to Set |
|-------|-------------|
| **Attack UI** | Attack Menu, Find Match, Confirm, Surrender, OK |
| **Army Bar** | Troop slot, Spell slot, Siege slot, Hero 1–4 |
| **Deploy Edges** | 6 points around the base (left/right × top/mid/bottom) |
| **Spell Targets** | 3 drop locations (left, center, right) |
| **Hero & Siege Deploy** | Where each hero and siege machine lands |
| **Wall Upgrade** | All Upgradable button, scroll area, Gold/Elixir/OK |

> 💡 **Tip:** Position the emulator on one side and the panel on the other. Click "Set" → click the spot in-game.

### Step 2 — Capture Templates

Go to the **Detection** tab and capture these images from your game:

| Template | What to Capture |
|----------|----------------|
| **Next Button** | The "Next" button during base scouting |
| **Return Home** | The "Return Home" button after battle |
| **50% Destruction** | The 50% star/text that appears mid-battle |
| **Wall Text** | The word "Wall" in the upgrade list popup |

> 📋 You can also **paste from clipboard** — take a screenshot, crop in Paint, copy, and hit Paste.

### Step 3 — Configure & Run

Go to the **Control** tab:

| Setting | Description | Default |
|---------|-------------|---------|
| **Number of Attacks** | Total attack cycles to run | 10 |
| **Troop Count** | Total troops to deploy (spread across 4 sides) | 40 |
| **Spell Count** | Total spells to deploy (spread across 3 targets) | 11 |
| **Enable Wall Upgrade** | Run wall upgrades between attacks | Off |
| **Check Walls Every** | Upgrade walls every N attacks | 5 |

Hit **▶ Start** and switch to your game. The bot takes over.

---

## 🔄 Attack Cycle — Under the Hood

```
┌─────────────────────────────────────────────────────────────┐
│                    SINGLE ATTACK CYCLE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 🔭 Zoom Out (centre screen + scroll)                    │
│  2. ⚔️  Click Attack Menu                                    │
│  3. 🔍 Find a Match                                         │
│  4. ✅ Confirm Attack                                        │
│  5. 🪄 Deploy Spells (distributed across 3 zones)           │
│  6. 🏰 Deploy Siege Machine                                 │
│  7. 🏹 Deploy Troops (spread across 4 edges)                │
│  8. 🦸 Deploy Heroes → Activate Abilities                   │
│  9. ⏳ Wait for 50% (90s timeout)                           │
│      ├─ ✓ 50% detected → wait 5-10s → surrender             │
│      └─ ✗ 90s elapsed → surrender                           │
│ 10. 🏳️ Surrender → OK → Return Home                         │
│                                                              │
│  ──── if wall upgrade enabled & interval reached ────        │
│  11. 🧱 Wall Upgrade (Gold + Elixir cycle)                  │
│                                                              │
│  → Repeat from step 1                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧱 Wall Upgrade Cycle

```
Open Upgrade List
       │
       ▼
 Scroll & Find "Wall" (template match, drag-scroll)
       │
       ▼
 Click Wall → Select Multiple (×3) → Upgrade with Gold → OK
       │
       ▼
 Re-open List → Find Wall again
       │
       ▼
 Click Wall → Select Multiple (×3) → Upgrade with Elixir → OK
```

---

## ⌨️ Hotkeys

| Key | Action |
|-----|--------|
| **F6** | Toggle Setup Panel while bot is running (bot pauses) |
| **Move mouse to corner** | PyAutoGUI fail-safe — emergency stop |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **UI** | tkinter (tabbed panel + draggable overlay) |
| **Image Detection** | OpenCV `cv2.matchTemplate` (TM_CCOEFF_NORMED) |
| **Mouse Automation** | PyAutoGUI + pynput |
| **Scrolling** | Click-hold-drag (emulator compatible) |
| **Config** | JSON persistence with auto-save |
| **Hotkeys** | pynput keyboard listener |

---

## 📝 Notes

- **Resolution independent** — all positions are set by clicking, never hardcoded
- **Emulator compatible** — drag-scroll works where mouse wheel doesn't
- **Fail-safe** — move mouse to any screen corner to instantly stop PyAutoGUI
- **Configurable confidence** — detection thresholds tuned to avoid false positives
- **Clean architecture** — modular `core/` package, each file has one job

---

## 📄 License

This project is for **educational purposes only**. Use responsibly and at your own risk. The developers are not responsible for any consequences of using this bot.

---

<p align="center">
  <b>Built with ❤️ by <a href="https://github.com/Rezwoan">Rezwoan</a></b><br/>
  <sub>If this helped you, give it a ⭐</sub>
</p>

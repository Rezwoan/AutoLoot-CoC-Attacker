"""
setup_panel.py

Tabbed Setup Panel for CoC Bot with overlay mode.

Tabs
----
1. **Positions**  — click-to-set button positions  (scrollable)
2. **Detection**  — capture / paste / test template images
3. **Control**    — start attacks, wall upgrade settings, live log
4. **Test**       — test image detection, position clicking, wall detection

Overlay
-------
While the bot runs autonomously the panel hides and a compact overlay
shows live stats.  Press **F6** to toggle the full panel (the bot
pauses while the panel is visible so it won't click on it).

Usage
-----
    python setup_panel.py
"""

import os
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Optional

import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageGrab, ImageTk
from pynput import keyboard as pynput_kb
from pynput import mouse as pynput_mouse

from core.config import (
    POSITION_SCHEMA,
    TEMPLATE_SCHEMA,
    default_config,
    load_config,
    save_config,
)
from core.wall_detector import find_wall_on_screen

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_IMG_DIR = os.path.join(_SCRIPT_DIR, "img")
_HOTKEY = pynput_kb.Key.f6


# ===========================================================================
#  ScrollableFrame
# ===========================================================================

class ScrollableFrame(ttk.Frame):
    """A frame containing a Canvas + vertical Scrollbar."""

    def __init__(self, parent: tk.Widget, height: int = 420, **kw) -> None:
        super().__init__(parent, **kw)

        self._canvas = tk.Canvas(self, highlightthickness=0, height=height)
        self._vscroll = ttk.Scrollbar(
            self, orient="vertical", command=self._canvas.yview
        )
        self.inner = ttk.Frame(self._canvas)

        self.inner.bind("<Configure>", self._on_inner_cfg)
        self._win = self._canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        self._canvas.bind("<Configure>", self._on_canvas_cfg)
        self._canvas.configure(yscrollcommand=self._vscroll.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        self._vscroll.pack(side="right", fill="y")

        self._canvas.bind("<Enter>", self._bind_wheel)
        self._canvas.bind("<Leave>", self._unbind_wheel)

    # ------------------------------------------------------------------

    def _on_inner_cfg(self, _e: tk.Event) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_cfg(self, e: tk.Event) -> None:
        self._canvas.itemconfig(self._win, width=e.width)

    def _bind_wheel(self, _e: tk.Event) -> None:
        self._canvas.bind_all("<MouseWheel>", self._on_wheel)

    def _unbind_wheel(self, _e: tk.Event) -> None:
        self._canvas.unbind_all("<MouseWheel>")

    def _on_wheel(self, e: tk.Event) -> None:
        self._canvas.yview_scroll(-(e.delta // 120), "units")


# ===========================================================================
#  RegionSelector  (fullscreen drag-to-crop)
# ===========================================================================

class RegionSelector(tk.Toplevel):
    """Fullscreen overlay — user drags a rectangle to capture a region."""

    def __init__(
        self,
        master: tk.Tk,
        screenshot: Image.Image,
        on_complete: Callable[[Image.Image], None],
        on_cancel: Callable[[], None],
    ) -> None:
        super().__init__(master)

        self._on_complete = on_complete
        self._on_cancel = on_cancel
        self._done = False

        self.overrideredirect(True)
        self.attributes("-topmost", True)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")

        self._photo = ImageTk.PhotoImage(screenshot)
        self._canvas = tk.Canvas(
            self, width=sw, height=sh, cursor="crosshair", highlightthickness=0
        )
        self._canvas.pack()
        self._canvas.create_image(0, 0, image=self._photo, anchor="nw")

        self._canvas.create_text(
            sw // 2, 25,
            text="Drag to select region  |  ESC to cancel",
            fill="yellow",
            font=("Segoe UI", 14, "bold"),
        )

        self._sx = self._sy = 0
        self._rect: Optional[int] = None
        self._screenshot = screenshot

        self._canvas.bind("<ButtonPress-1>", self._press)
        self._canvas.bind("<B1-Motion>", self._drag)
        self._canvas.bind("<ButtonRelease-1>", self._release)
        self.bind("<Escape>", lambda _: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self.focus_force()
        self.grab_set()

    def _press(self, e: tk.Event) -> None:
        self._sx, self._sy = e.x, e.y

    def _drag(self, e: tk.Event) -> None:
        if self._rect:
            self._canvas.delete(self._rect)
        self._rect = self._canvas.create_rectangle(
            self._sx, self._sy, e.x, e.y,
            outline="#ff3333", width=2, dash=(6, 3),
        )

    def _release(self, e: tk.Event) -> None:
        x0, y0 = min(self._sx, e.x), min(self._sy, e.y)
        x1, y1 = max(self._sx, e.x), max(self._sy, e.y)
        if (x1 - x0) > 10 and (y1 - y0) > 10:
            cropped = self._screenshot.crop((x0, y0, x1, y1))
            self._done = True
            self.destroy()
            self._on_complete(cropped)
        elif self._rect:
            self._canvas.delete(self._rect)

    def _cancel(self) -> None:
        if not self._done:
            self._done = True
            self.destroy()
            self._on_cancel()


# ===========================================================================
#  BotOverlay  (compact stats bar during bot operation)
# ===========================================================================

class BotOverlay(tk.Toplevel):
    """Small draggable overlay that shows live bot stats."""

    def __init__(
        self,
        master: tk.Tk,
        on_stop: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.88)
        self.configure(bg="#1a1a2e")

        frm = tk.Frame(self, bg="#1a1a2e", padx=10, pady=5)
        frm.pack()

        self._stats_var = tk.StringVar(
            value="Attacks: 0/0  |  \u271350%: 0  |  Left: 0"
        )
        tk.Label(
            frm,
            textvariable=self._stats_var,
            fg="#00ff88",
            bg="#1a1a2e",
            font=("Consolas", 11, "bold"),
        ).pack(side="left", padx=(0, 14))

        self._pause_var = tk.StringVar(value="")
        tk.Label(
            frm,
            textvariable=self._pause_var,
            fg="#ffcc00",
            bg="#1a1a2e",
            font=("Consolas", 9, "bold"),
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            frm,
            text="\u25a0  Stop",
            fg="white",
            bg="#cc3333",
            activebackground="#ff4444",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            command=on_stop,
            padx=10,
        ).pack(side="left", padx=2)

        tk.Label(
            frm,
            text="F6: Panel",
            fg="#666666",
            bg="#1a1a2e",
            font=("Segoe UI", 8),
        ).pack(side="left", padx=(10, 0))

        # Centre-top of screen
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        w = self.winfo_width()
        self.geometry(f"+{(sw - w) // 2}+{4}")

        # Drag support
        self._dx = self._dy = 0
        frm.bind("<ButtonPress-1>", self._start_drag)
        frm.bind("<B1-Motion>", self._do_drag)

    # ------------------------------------------------------------------

    def _start_drag(self, e: tk.Event) -> None:
        self._dx, self._dy = e.x, e.y

    def _do_drag(self, e: tk.Event) -> None:
        self.geometry(
            f"+{self.winfo_x() + e.x - self._dx}"
            f"+{self.winfo_y() + e.y - self._dy}"
        )

    def update_stats(
        self, done: int, total: int, successful: int, remaining: int
    ) -> None:
        self._stats_var.set(
            f"Attacks: {done}/{total}  |  \u271350%: {successful}"
            f"  |  Left: {remaining}"
        )

    def set_paused(self, paused: bool) -> None:
        self._pause_var.set("\u23f8 PAUSED" if paused else "")


# ===========================================================================
#  SetupPanel  (main application)
# ===========================================================================

class SetupPanel:
    """Tabbed setup / control / test panel with overlay mode."""

    _WINDOW_ALPHA = 0.92
    _CAPTURE_ALPHA = 0.15

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("CoC Bot \u2014 Setup Panel")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self._WINDOW_ALPHA)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Config -------------------------------------------------------
        self.config = load_config()
        os.makedirs(_IMG_DIR, exist_ok=True)

        # UI references ------------------------------------------------
        self._pos_labels: Dict[str, ttk.Label] = {}
        self._tmpl_labels: Dict[str, ttk.Label] = {}
        self._photo_refs: list = []

        # Status -------------------------------------------------------
        self._status_var = tk.StringVar(value="Ready")
        self._capturing = False

        # Bot state ----------------------------------------------------
        self._bot_running = False
        self._bot_thread: Optional[threading.Thread] = None
        self._bot_stop = threading.Event()
        self._bot_pause = threading.Event()
        self._overlay: Optional[BotOverlay] = None
        self._panel_visible = True

        # Bot settings -------------------------------------------------
        self._total_attacks = tk.IntVar(value=10)
        self._wall_enabled = tk.BooleanVar(value=False)
        self._wall_every = tk.IntVar(value=5)
        self._attacks_done = 0
        self._attacks_ok = 0  # 50 %+ destruction

        # Build --------------------------------------------------------
        self._build_ui()
        self._start_hotkey_listener()

        # Position near top-right
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        w = self.root.winfo_width()
        self.root.geometry(f"+{sw - w - 20}+{30}")

    # ==================================================================
    #  UI construction
    # ==================================================================

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=6)
        main.pack(fill="both", expand=True)

        nb = ttk.Notebook(main)
        nb.pack(fill="both", expand=True)

        tab_pos = ttk.Frame(nb)
        tab_det = ttk.Frame(nb)
        tab_ctrl = ttk.Frame(nb)
        tab_test = ttk.Frame(nb)

        nb.add(tab_pos, text="  Positions  ")
        nb.add(tab_det, text="  Detection  ")
        nb.add(tab_ctrl, text="  Control  ")
        nb.add(tab_test, text="  Test  ")

        self._build_positions_tab(tab_pos)
        self._build_detection_tab(tab_det)
        self._build_control_tab(tab_ctrl)
        self._build_test_tab(tab_test)

        # Bottom bar (always visible regardless of tab)
        bottom = ttk.Frame(main)
        bottom.pack(fill="x", pady=(6, 0))

        ttk.Button(bottom, text="Save", command=self._save).pack(
            side="left", padx=2
        )
        ttk.Button(bottom, text="Reload", command=self._reload).pack(
            side="left", padx=2
        )
        ttk.Button(bottom, text="Reset All", command=self._reset).pack(
            side="left", padx=2
        )

        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=(6, 2))
        ttk.Label(
            main, textvariable=self._status_var, foreground="gray"
        ).pack(fill="x")

    # ------------------------------------------------------------------
    #  Tab 1 — Positions  (scrollable)
    # ------------------------------------------------------------------

    def _build_positions_tab(self, parent: ttk.Frame) -> None:
        sf = ScrollableFrame(parent, height=420)
        sf.pack(fill="both", expand=True, padx=2, pady=2)

        for group_name, keys in POSITION_SCHEMA.items():
            grp = ttk.LabelFrame(sf.inner, text=group_name, padding=(8, 4))
            grp.pack(fill="x", padx=4, pady=(0, 6))
            for i, (key, label) in enumerate(keys.items()):
                self._add_position_row(grp, i, key, label)

    def _add_position_row(
        self, parent: ttk.LabelFrame, row: int, key: str, label: str
    ) -> None:
        ttk.Label(parent, text=label, width=24, anchor="w").grid(
            row=row, column=0, padx=(0, 4), sticky="w"
        )

        pos = self.config["positions"].get(key)
        txt, fg = self._pos_display(pos)
        val = ttk.Label(
            parent, text=txt, width=14, anchor="center", foreground=fg
        )
        val.grid(row=row, column=1, padx=4)
        self._pos_labels[key] = val

        ttk.Button(
            parent,
            text="Set",
            width=4,
            command=lambda k=key, lb=label: self._start_position_capture(k, lb),
        ).grid(row=row, column=2, padx=(4, 0))

    # ------------------------------------------------------------------
    #  Tab 2 — Detection  (templates)
    # ------------------------------------------------------------------

    def _build_detection_tab(self, parent: ttk.Frame) -> None:
        for group_name, keys in TEMPLATE_SCHEMA.items():
            grp = ttk.LabelFrame(parent, text=group_name, padding=(8, 4))
            grp.pack(fill="x", padx=4, pady=(4, 6))
            for i, (key, label) in enumerate(keys.items()):
                self._add_template_row(grp, i, key, label)

        ttk.Label(
            parent,
            text="Tip: \U0001f4f7 capture from screen, "
            "\U0001f4cb paste from clipboard, "
            "Test to verify detection.",
            foreground="gray",
            wraplength=380,
        ).pack(padx=8, pady=(0, 4), anchor="w")

    def _add_template_row(
        self, parent: ttk.LabelFrame, row: int, key: str, label: str
    ) -> None:
        ttk.Label(parent, text=label, width=24, anchor="w").grid(
            row=row, column=0, padx=(0, 4), sticky="w"
        )

        tmpl = self.config["templates"].get(key)
        txt, fg = self._tmpl_display(tmpl)
        val = ttk.Label(
            parent, text=txt, width=14, anchor="center", foreground=fg
        )
        val.grid(row=row, column=1, padx=4)
        self._tmpl_labels[key] = val

        bf = ttk.Frame(parent)
        bf.grid(row=row, column=2, padx=(4, 0))

        ttk.Button(
            bf, text="\U0001f4f7", width=3,
            command=lambda k=key: self._start_region_capture(k),
        ).pack(side="left", padx=1)
        ttk.Button(
            bf, text="\U0001f4cb", width=3,
            command=lambda k=key: self._paste_template(k),
        ).pack(side="left", padx=1)
        ttk.Button(
            bf, text="Test", width=4,
            command=lambda k=key: self._test_template(k),
        ).pack(side="left", padx=1)

    # ------------------------------------------------------------------
    #  Tab 3 — Control
    # ------------------------------------------------------------------

    def _build_control_tab(self, parent: ttk.Frame) -> None:
        # ── Attack settings ──
        atk = ttk.LabelFrame(parent, text="Attack Settings", padding=(10, 6))
        atk.pack(fill="x", padx=4, pady=(4, 6))

        r = 0
        ttk.Label(atk, text="Number of Attacks:").grid(
            row=r, column=0, sticky="w"
        )
        ttk.Spinbox(
            atk, from_=1, to=999, width=6, textvariable=self._total_attacks
        ).grid(row=r, column=1, padx=6, sticky="w")

        r += 1
        ttk.Checkbutton(
            atk, text="Enable Wall Upgrade", variable=self._wall_enabled
        ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(4, 0))

        r += 1
        ttk.Label(atk, text="Check Walls Every:").grid(
            row=r, column=0, sticky="w", pady=(2, 0)
        )
        wf = ttk.Frame(atk)
        wf.grid(row=r, column=1, sticky="w", pady=(2, 0))
        ttk.Spinbox(
            wf, from_=1, to=50, width=4, textvariable=self._wall_every
        ).pack(side="left")
        ttk.Label(wf, text=" attacks").pack(side="left")

        # ── Buttons ──
        bf = ttk.Frame(parent)
        bf.pack(fill="x", padx=4, pady=6)

        self._start_btn = ttk.Button(
            bf, text="\u25b6  Start", command=self._start_bot
        )
        self._start_btn.pack(side="left", padx=4, ipadx=12, ipady=4)

        self._stop_btn = ttk.Button(
            bf, text="\u25a0  Stop", command=self._stop_bot, state="disabled"
        )
        self._stop_btn.pack(side="left", padx=4, ipadx=12, ipady=4)

        ttk.Label(
            bf, text="F6 toggles panel while running", foreground="gray"
        ).pack(side="right", padx=4)

        # ── Log ──
        lf = ttk.LabelFrame(parent, text="Log", padding=(4, 4))
        lf.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        log_frame = ttk.Frame(lf)
        log_frame.pack(fill="both", expand=True)

        self._log_text = tk.Text(
            log_frame,
            height=12,
            wrap="word",
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#cccccc",
            insertbackground="#cccccc",
            state="disabled",
        )
        log_scroll = ttk.Scrollbar(log_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=log_scroll.set)

        log_scroll.pack(side="right", fill="y")
        self._log_text.pack(side="left", fill="both", expand=True)

    # ------------------------------------------------------------------
    #  Tab 4 — Test
    # ------------------------------------------------------------------

    def _build_test_tab(self, parent: ttk.Frame) -> None:
        # ── Template detection test ──
        det = ttk.LabelFrame(
            parent, text="Test Image Detection", padding=(10, 6)
        )
        det.pack(fill="x", padx=4, pady=(4, 6))

        tmpl_keys: list = []
        for grp in TEMPLATE_SCHEMA.values():
            tmpl_keys.extend(grp.keys())

        ttk.Label(det, text="Template:").grid(row=0, column=0, sticky="w")
        self._test_tmpl_var = tk.StringVar(
            value=tmpl_keys[0] if tmpl_keys else ""
        )
        ttk.Combobox(
            det,
            textvariable=self._test_tmpl_var,
            values=tmpl_keys,
            state="readonly",
            width=18,
        ).grid(row=0, column=1, padx=6, sticky="w")

        ttk.Button(
            det, text="Run Test", command=self._run_detection_test
        ).grid(row=0, column=2, padx=6)

        self._test_det_result = tk.StringVar(value="\u2014")
        ttk.Label(
            det, textvariable=self._test_det_result, wraplength=340
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

        # ── Position click test ──
        pos = ttk.LabelFrame(
            parent, text="Test Position Click", padding=(10, 6)
        )
        pos.pack(fill="x", padx=4, pady=(0, 6))

        pos_keys: list = []
        for grp in POSITION_SCHEMA.values():
            pos_keys.extend(grp.keys())

        ttk.Label(pos, text="Position:").grid(row=0, column=0, sticky="w")
        self._test_pos_var = tk.StringVar(
            value=pos_keys[0] if pos_keys else ""
        )
        combo = ttk.Combobox(
            pos,
            textvariable=self._test_pos_var,
            values=pos_keys,
            state="readonly",
            width=18,
        )
        combo.grid(row=0, column=1, padx=6, sticky="w")
        combo.bind("<<ComboboxSelected>>", self._on_test_pos_selected)

        self._test_pos_coords = tk.StringVar(value="")
        ttk.Label(
            pos, textvariable=self._test_pos_coords, foreground="gray"
        ).grid(row=0, column=2, padx=4)

        ttk.Button(
            pos, text="Click Position", command=self._run_click_test
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

        self._test_click_result = tk.StringVar(value="\u2014")
        ttk.Label(pos, textvariable=self._test_click_result).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(4, 0)
        )

        # ── Wall detection (Template Matching) ──
        wall = ttk.LabelFrame(
            parent, text="Test Wall Detection (Template Match)", padding=(10, 6)
        )
        wall.pack(fill="x", padx=4, pady=(0, 6))

        ttk.Label(
            wall,
            text='Matches the captured "Wall Text" template on screen.',
            foreground="gray",
        ).grid(row=0, column=0, columnspan=3, sticky="w")

        ttk.Button(
            wall, text="Find \"Wall\" on Screen",
            command=self._run_wall_template_test,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        self._test_wall_result = tk.StringVar(value="\u2014")
        ttk.Label(
            wall, textvariable=self._test_wall_result, wraplength=360,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))

    def _on_test_pos_selected(self, _e: tk.Event = None) -> None:
        key = self._test_pos_var.get()
        pos = self.config["positions"].get(key)
        if pos and isinstance(pos, (list, tuple)) and len(pos) == 2:
            self._test_pos_coords.set(f"({pos[0]}, {pos[1]})")
        else:
            self._test_pos_coords.set("not set")

    # ------------------------------------------------------------------
    #  Display helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pos_display(pos) -> tuple:
        if pos and isinstance(pos, (list, tuple)) and len(pos) == 2:
            return f"({pos[0]}, {pos[1]})", "#006600"
        return "\u2717 not set", "#cc0000"

    @staticmethod
    def _tmpl_display(tmpl) -> tuple:
        if tmpl and os.path.isfile(os.path.join(_IMG_DIR, tmpl)):
            return f"\u2713 {tmpl}", "#006600"
        return "\u2717 not set", "#cc0000"

    # ==================================================================
    #  Position capture  (click-to-set)
    # ==================================================================

    def _start_position_capture(self, key: str, label: str) -> None:
        if self._capturing:
            return
        self._capturing = True
        self._status_var.set(f'Click on "{label}" in the game...')
        self.root.attributes("-alpha", self._CAPTURE_ALPHA)
        self.root.after(400, self._listen_click, key)

    def _listen_click(self, key: str) -> None:
        def on_click(x, y, button, pressed):
            if pressed and button == pynput_mouse.Button.left:
                self.root.after(0, self._finish_capture, key, x, y)
                return False

        pynput_mouse.Listener(on_click=on_click).start()

    def _finish_capture(self, key: str, x: int, y: int) -> None:
        self.config["positions"][key] = [x, y]
        self._capturing = False
        self.root.attributes("-alpha", self._WINDOW_ALPHA)

        lbl = self._pos_labels.get(key)
        if lbl:
            lbl.config(text=f"({x}, {y})", foreground="#006600")
        self._status_var.set(f"\u2713  {key} = ({x}, {y})")
        self._auto_save()

    # ==================================================================
    #  Region capture  (template screenshot)
    # ==================================================================

    def _start_region_capture(self, key: str) -> None:
        if self._capturing:
            return
        self._capturing = True
        self._status_var.set("Taking screenshot...")
        self.root.withdraw()
        self.root.update()
        self.root.after(400, self._do_region_capture, key)

    def _do_region_capture(self, key: str) -> None:
        screenshot = pyautogui.screenshot()

        def on_complete(cropped: Image.Image) -> None:
            filename = f"{key}.png"
            cropped.save(os.path.join(_IMG_DIR, filename))
            self.config["templates"][key] = filename
            lbl = self._tmpl_labels.get(key)
            if lbl:
                lbl.config(text=f"\u2713 {filename}", foreground="#006600")
            self._status_var.set(f"\u2713  Captured template: {filename}")
            self._auto_save()
            self._capturing = False
            self.root.deiconify()

        def on_cancel() -> None:
            self._capturing = False
            self.root.deiconify()
            self._status_var.set("Capture cancelled")

        RegionSelector(self.root, screenshot, on_complete, on_cancel)

    # ==================================================================
    #  Paste template
    # ==================================================================

    def _paste_template(self, key: str) -> None:
        try:
            img = ImageGrab.grabclipboard()
        except Exception:
            img = None

        if not isinstance(img, Image.Image):
            messagebox.showwarning(
                "No Image",
                "No image on clipboard.\nCopy a screenshot first.",
            )
            return

        filename = f"{key}.png"
        img.save(os.path.join(_IMG_DIR, filename))
        self.config["templates"][key] = filename

        lbl = self._tmpl_labels.get(key)
        if lbl:
            lbl.config(text=f"\u2713 {filename}", foreground="#006600")
        self._status_var.set(f"\u2713  Pasted template: {filename}")
        self._auto_save()

    # ==================================================================
    #  Template detection test  (inline Test button on Detection tab)
    # ==================================================================

    def _test_template(self, key: str) -> None:
        tmpl_file = self.config["templates"].get(key)
        if not tmpl_file:
            self._status_var.set(f"\u2717  No template set for {key}")
            return

        fpath = os.path.join(_IMG_DIR, tmpl_file)
        if not os.path.isfile(fpath):
            self._status_var.set(f"\u2717  File missing: {tmpl_file}")
            return

        self._status_var.set(f"Testing {key}...")
        self.root.attributes("-alpha", self._CAPTURE_ALPHA)
        self.root.update()
        self.root.after(400, self._do_match_test, key, fpath, "status")

    # ==================================================================
    #  Test-tab detection test
    # ==================================================================

    def _run_detection_test(self) -> None:
        key = self._test_tmpl_var.get()
        if not key:
            self._test_det_result.set("Select a template first")
            return

        tmpl_file = self.config["templates"].get(key)
        if not tmpl_file:
            self._test_det_result.set(
                f"\u2717 No template captured for '{key}'"
            )
            return

        fpath = os.path.join(_IMG_DIR, tmpl_file)
        if not os.path.isfile(fpath):
            self._test_det_result.set(f"\u2717 File missing: {tmpl_file}")
            return

        self._test_det_result.set("Scanning...")
        self.root.attributes("-alpha", self._CAPTURE_ALPHA)
        self.root.update()
        self.root.after(400, self._do_match_test, key, fpath, "test_tab")

    # ------------------------------------------------------------------

    def _do_match_test(self, key: str, fpath: str, target: str) -> None:
        """
        Run cv2.matchTemplate and report result.

        *target*: ``"status"`` writes to status bar,
                  ``"test_tab"`` writes to the Test tab result label.
        """
        try:
            ss = pyautogui.screenshot()
            gray = cv2.cvtColor(np.array(ss), cv2.COLOR_RGB2GRAY)
            tmpl = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)

            if tmpl is None:
                msg = f"\u2717  Cannot load template: {key}"
            else:
                res = cv2.matchTemplate(
                    gray, tmpl, cv2.TM_CCOEFF_NORMED
                )
                _, mx, _, loc = cv2.minMaxLoc(res)
                conf = round(mx * 100, 1)

                if mx >= 0.8:
                    cx = loc[0] + tmpl.shape[1] // 2
                    cy = loc[1] + tmpl.shape[0] // 2
                    msg = (
                        f"\u2713  {key}: FOUND at ({cx}, {cy}) "
                        f"\u2014 {conf}% confidence"
                    )
                else:
                    msg = (
                        f"\u2717  {key}: NOT FOUND "
                        f"\u2014 best match {conf}%"
                    )
        except Exception as exc:
            msg = f"\u2717  Test error: {exc}"

        self.root.attributes("-alpha", self._WINDOW_ALPHA)

        if target == "status":
            self._status_var.set(msg)
        else:
            self._test_det_result.set(msg)

    # ==================================================================
    #  Test-tab click test
    # ==================================================================

    def _run_click_test(self) -> None:
        key = self._test_pos_var.get()
        if not key:
            self._test_click_result.set("Select a position first")
            return

        pos = self.config["positions"].get(key)
        if not pos or not isinstance(pos, (list, tuple)) or len(pos) != 2:
            self._test_click_result.set(
                f"\u2717 Position '{key}' is not set"
            )
            return

        x, y = pos
        self._test_click_result.set(f"Clicking ({x}, {y}) in 2 seconds...")
        self.root.attributes("-alpha", self._CAPTURE_ALPHA)
        self.root.update()
        self.root.after(2000, self._do_click_test, key, x, y)

    def _do_click_test(self, key: str, x: int, y: int) -> None:
        try:
            pyautogui.click(x, y)
            self.root.attributes("-alpha", self._WINDOW_ALPHA)
            self._test_click_result.set(
                f"\u2713 Clicked {key} at ({x}, {y})"
            )
        except Exception as exc:
            self.root.attributes("-alpha", self._WINDOW_ALPHA)
            self._test_click_result.set(f"\u2717 Error: {exc}")

    # ==================================================================
    #  Test-tab wall template matching
    # ==================================================================

    def _run_wall_template_test(self) -> None:
        """Search the screen for the 'Wall' template image."""
        tpl = self.config["templates"].get("wall_text")
        if not tpl or not os.path.isfile(tpl):
            self._test_wall_result.set(
                "\u2717  No wall template captured. "
                "Go to Detection tab \u2192 capture 'Wall Text' first."
            )
            return

        self._test_wall_result.set("Matching wall template...")
        self.root.attributes("-alpha", self._CAPTURE_ALPHA)
        self.root.update()
        self.root.after(400, lambda: self._do_wall_template_test(tpl))

    def _do_wall_template_test(self, tpl: str) -> None:
        try:
            pos = find_wall_on_screen(tpl)
            self.root.attributes("-alpha", self._WINDOW_ALPHA)
            if pos:
                self._test_wall_result.set(
                    f"\u2713  'Wall' FOUND at ({pos[0]}, {pos[1]})"
                )
            else:
                self._test_wall_result.set(
                    "\u2717  'Wall' NOT FOUND on screen"
                )
        except Exception as exc:
            self.root.attributes("-alpha", self._WINDOW_ALPHA)
            self._test_wall_result.set(f"\u2717  Detection error: {exc}")

    # ==================================================================
    #  Bot control
    # ==================================================================

    def _start_bot(self) -> None:
        if self._bot_running:
            return

        # Validate critical positions
        required = ("attack_menu", "find_match", "confirm_attack")
        missing = [
            k for k in required if not self.config["positions"].get(k)
        ]
        if missing:
            messagebox.showwarning(
                "Missing Positions",
                f"Set these positions first:\n{', '.join(missing)}",
            )
            return

        self._bot_running = True
        self._bot_stop.clear()
        self._bot_pause.clear()
        self._attacks_done = 0
        self._attacks_ok = 0

        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")

        self._log_msg("Bot started")
        self._log_msg(f"Target: {self._total_attacks.get()} attacks")
        if self._wall_enabled.get():
            self._log_msg(
                f"Wall upgrade every {self._wall_every.get()} attacks"
            )

        # Switch to overlay
        self._show_overlay()
        self._panel_visible = False
        self.root.withdraw()

        # Launch bot thread
        self._bot_thread = threading.Thread(
            target=self._bot_loop, daemon=True
        )
        self._bot_thread.start()

        # Periodic overlay refresh
        self._tick_overlay()

    def _bot_loop(self) -> None:
        """
        Bot main loop.

        **Replace the placeholder block below** with real attack logic
        once ``attack.py`` is implemented.
        """
        total = self._total_attacks.get()

        try:
            # ── PLACEHOLDER — demo mode ──────────────────────────────
            # When the attack engine is ready, import and call it here:
            #
            #   from attack import run_attacks
            #   run_attacks(
            #       config=self.config,
            #       total=total,
            #       stop_event=self._bot_stop,
            #       pause_event=self._bot_pause,
            #       wall_enabled=self._wall_enabled.get(),
            #       wall_every=self._wall_every.get(),
            #       on_attack_done=self._on_attack_done,
            #   )
            #
            # For now, simulate attacks so the overlay can be tested.

            self._log_msg(
                "\u26a0 Attack engine not built yet \u2014 demo mode"
            )

            for _ in range(total):
                if self._bot_stop.is_set():
                    break

                # Honour pause
                while (
                    self._bot_pause.is_set()
                    and not self._bot_stop.is_set()
                ):
                    time.sleep(0.2)

                if self._bot_stop.is_set():
                    break

                time.sleep(3)  # simulate attack duration

                self._attacks_done += 1
                ok = random.random() > 0.3
                if ok:
                    self._attacks_ok += 1

                self._log_msg(
                    f"Attack {self._attacks_done}/{total} \u2014 "
                    f"{'\u2713 50%+' if ok else '\u2717 below 50%'}"
                )

        except Exception as exc:
            self._log_msg(f"Bot error: {exc}")

        finally:
            self.root.after(0, self._bot_finished)

    def _stop_bot(self) -> None:
        if not self._bot_running:
            return
        self._bot_stop.set()
        self._bot_pause.clear()
        self._log_msg("Stopping bot...")

    def _bot_finished(self) -> None:
        self._bot_running = False
        self._start_btn.config(state="normal")
        self._stop_btn.config(state="disabled")

        done, ok = self._attacks_done, self._attacks_ok
        self._log_msg(
            f"Bot finished \u2014 {done} attacks, {ok} successful (50%+)"
        )

        # Restore panel
        self._hide_overlay()
        self.root.deiconify()
        self._panel_visible = True

    # ==================================================================
    #  Overlay management
    # ==================================================================

    def _show_overlay(self) -> None:
        if self._overlay:
            self._overlay.destroy()
        self._overlay = BotOverlay(self.root, on_stop=self._stop_bot)
        total = self._total_attacks.get()
        self._overlay.update_stats(0, total, 0, total)

    def _hide_overlay(self) -> None:
        if self._overlay:
            self._overlay.destroy()
            self._overlay = None

    def _tick_overlay(self) -> None:
        """Periodically refresh overlay stats from main thread."""
        if not self._bot_running:
            return
        total = self._total_attacks.get()
        remaining = max(0, total - self._attacks_done)
        if self._overlay:
            self._overlay.update_stats(
                self._attacks_done, total, self._attacks_ok, remaining
            )
        self.root.after(500, self._tick_overlay)

    # ==================================================================
    #  F6 hotkey  (toggle panel / overlay while bot is running)
    # ==================================================================

    def _start_hotkey_listener(self) -> None:
        def on_press(key):
            if key == _HOTKEY:
                self.root.after(0, self._toggle_panel)

        listener = pynput_kb.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()

    def _toggle_panel(self) -> None:
        """
        F6 behaviour while the bot is running:

        - Panel visible  -> hide panel, show overlay, **resume** bot
        - Panel hidden    -> show panel, hide overlay, **pause** bot
        """
        if not self._bot_running:
            return

        if self._panel_visible:
            # Hide panel -> resume
            self.root.withdraw()
            self._panel_visible = False
            if self._overlay:
                self._overlay.deiconify()
                self._overlay.set_paused(False)
            self._bot_pause.clear()
            self._log_msg("Resumed \u2014 panel hidden")
        else:
            # Show panel -> pause
            self._bot_pause.set()
            if self._overlay:
                self._overlay.set_paused(True)
                self._overlay.withdraw()
            self.root.deiconify()
            self._panel_visible = True
            self._log_msg("Paused \u2014 press F6 to resume")
            self._status_var.set(
                "Bot PAUSED \u2014 press F6 to hide panel & resume"
            )

    # ==================================================================
    #  Thread-safe logging
    # ==================================================================

    def _log_msg(self, msg: str) -> None:
        """Schedule a log append on the tkinter main thread."""
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self._log_text.config(state="normal")
        self._log_text.insert("end", f"[{ts}] {msg}\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    # ==================================================================
    #  Save / Load / Reset
    # ==================================================================

    def _auto_save(self) -> None:
        save_config(self.config)

    def _save(self) -> None:
        save_config(self.config)
        self._status_var.set("\u2713  Config saved")

    def _reload(self) -> None:
        self.config = load_config()
        self._refresh_all()
        self._status_var.set("\u2713  Config reloaded")

    def _reset(self) -> None:
        if messagebox.askyesno("Reset", "Clear ALL positions and templates?"):
            self.config = default_config()
            save_config(self.config)
            self._refresh_all()
            self._status_var.set("\u2713  Config reset")

    def _refresh_all(self) -> None:
        for group in POSITION_SCHEMA.values():
            for key in group:
                lbl = self._pos_labels.get(key)
                if lbl:
                    pos = self.config["positions"].get(key)
                    txt, fg = self._pos_display(pos)
                    lbl.config(text=txt, foreground=fg)

        for group in TEMPLATE_SCHEMA.values():
            for key in group:
                lbl = self._tmpl_labels.get(key)
                if lbl:
                    tmpl = self.config["templates"].get(key)
                    txt, fg = self._tmpl_display(tmpl)
                    lbl.config(text=txt, foreground=fg)

    # ==================================================================
    #  Shutdown
    # ==================================================================

    def _on_close(self) -> None:
        if self._bot_running:
            self._bot_stop.set()
            self._bot_pause.clear()
        self._hide_overlay()
        self.root.destroy()

    # ==================================================================
    #  Run
    # ==================================================================

    def run(self) -> None:
        self.root.mainloop()


# ===========================================================================
#  Entry point
# ===========================================================================

def main() -> None:
    panel = SetupPanel()
    panel.run()


if __name__ == "__main__":
    main()

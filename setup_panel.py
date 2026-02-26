"""
setup_panel.py

Always-on-top Setup Panel for configuring CoC Bot.

Features
--------
- Click-to-set button positions  (panel fades, you click the game, done)
- Screen region capture for detection templates  (drag a rectangle)
- Paste from clipboard for templates
- Auto-saves to ``config.json`` on every change

Usage
-----
    python setup_panel.py
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Optional

import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageGrab, ImageTk
from pynput import mouse as pynput_mouse

from core.config import (
    POSITION_SCHEMA,
    TEMPLATE_SCHEMA,
    default_config,
    load_config,
    save_config,
)

# ---------------------------------------------------------------------------
#  Paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_IMG_DIR = os.path.join(_SCRIPT_DIR, "img")


# ===========================================================================
#  RegionSelector — fullscreen overlay for dragging a capture rectangle
# ===========================================================================

class RegionSelector(tk.Toplevel):
    """
    Fullscreen overlay that shows a frozen screenshot.

    The user drags a rectangle to select a region.  On release the cropped
    image is passed to *on_complete*.  Press **Escape** to cancel.
    """

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

        # Fullscreen, no borders, on top
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        self.geometry(f"{screen_w}x{screen_h}+0+0")

        # Display screenshot as background
        self._photo = ImageTk.PhotoImage(screenshot)
        self._canvas = tk.Canvas(
            self,
            width=screen_w,
            height=screen_h,
            cursor="crosshair",
            highlightthickness=0,
        )
        self._canvas.pack()
        self._canvas.create_image(0, 0, image=self._photo, anchor="nw")

        # Instruction banner
        self._canvas.create_text(
            screen_w // 2,
            25,
            text="Drag to select region  |  ESC to cancel",
            fill="yellow",
            font=("Segoe UI", 14, "bold"),
        )

        # State
        self._start_x = 0
        self._start_y = 0
        self._rect_id: Optional[int] = None
        self._screenshot = screenshot

        # Bindings
        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Escape>", lambda _: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self.focus_force()
        self.grab_set()

    # ------------------------------------------------------------------

    def _on_press(self, event: tk.Event) -> None:
        self._start_x = event.x
        self._start_y = event.y

    def _on_drag(self, event: tk.Event) -> None:
        if self._rect_id:
            self._canvas.delete(self._rect_id)
        self._rect_id = self._canvas.create_rectangle(
            self._start_x,
            self._start_y,
            event.x,
            event.y,
            outline="#ff3333",
            width=2,
            dash=(6, 3),
        )

    def _on_release(self, event: tk.Event) -> None:
        x0 = min(self._start_x, event.x)
        y0 = min(self._start_y, event.y)
        x1 = max(self._start_x, event.x)
        y1 = max(self._start_y, event.y)

        if (x1 - x0) > 10 and (y1 - y0) > 10:
            cropped = self._screenshot.crop((x0, y0, x1, y1))
            self._done = True
            self.destroy()
            self._on_complete(cropped)
        else:
            # Selection too small — ignore, let user retry
            if self._rect_id:
                self._canvas.delete(self._rect_id)

    def _cancel(self) -> None:
        if not self._done:
            self._done = True
            self.destroy()
            self._on_cancel()


# ===========================================================================
#  SetupPanel — the main GUI
# ===========================================================================

class SetupPanel:
    """
    Always-on-top configuration panel.

    Position items:  user clicks [Set], then clicks on the game.
    Template items:  user clicks [📷 Capture] or [📋 Paste].
    """

    _WINDOW_ALPHA = 0.92
    _CAPTURE_ALPHA = 0.15

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("CoC Bot — Setup Panel")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self._WINDOW_ALPHA)
        self.root.resizable(False, False)

        # Config
        self.config = load_config()
        os.makedirs(_IMG_DIR, exist_ok=True)

        # UI element references
        self._pos_labels: Dict[str, ttk.Label] = {}
        self._tmpl_labels: Dict[str, ttk.Label] = {}
        self._photo_refs: list = []  # prevent GC of PhotoImage objects

        # Status bar
        self._status_var = tk.StringVar(value="Ready")

        # Capture state
        self._capturing = False

        self._build_ui()

        # Position near top-right of screen
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        w = self.root.winfo_width()
        self.root.geometry(f"+{sw - w - 20}+{40}")

    # ==================================================================
    #  UI construction
    # ==================================================================

    def _build_ui(self) -> None:
        """Assemble all widgets."""
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # ── Position sections ──
        for group_name, keys in POSITION_SCHEMA.items():
            frame = ttk.LabelFrame(main, text=group_name, padding=(8, 4))
            frame.pack(fill="x", pady=(0, 6))
            for i, (key, label) in enumerate(keys.items()):
                self._add_position_row(frame, i, key, label)

        # ── Template sections ──
        for group_name, keys in TEMPLATE_SCHEMA.items():
            frame = ttk.LabelFrame(main, text=group_name, padding=(8, 4))
            frame.pack(fill="x", pady=(0, 6))
            for i, (key, label) in enumerate(keys.items()):
                self._add_template_row(frame, i, key, label)

        # ── Bottom buttons ──
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(btn_frame, text="Save", command=self._save).pack(
            side="left", padx=2
        )
        ttk.Button(btn_frame, text="Reload", command=self._reload).pack(
            side="left", padx=2
        )
        ttk.Button(btn_frame, text="Reset All", command=self._reset).pack(
            side="left", padx=2
        )

        # ── Status bar ──
        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=(10, 4))
        ttk.Label(main, textvariable=self._status_var, foreground="gray").pack(
            fill="x"
        )

    # ------------------------------------------------------------------

    def _add_position_row(
        self, parent: ttk.LabelFrame, row: int, key: str, label: str
    ) -> None:
        ttk.Label(parent, text=label, width=26, anchor="w").grid(
            row=row, column=0, padx=(0, 4), sticky="w"
        )

        pos = self.config["positions"].get(key)
        val_text, val_fg = self._pos_display(pos)

        val_label = ttk.Label(
            parent, text=val_text, width=14, anchor="center", foreground=val_fg
        )
        val_label.grid(row=row, column=1, padx=4)
        self._pos_labels[key] = val_label

        ttk.Button(
            parent,
            text="Set",
            width=4,
            command=lambda k=key, l=label: self._start_position_capture(k, l),
        ).grid(row=row, column=2, padx=(4, 0))

    def _add_template_row(
        self, parent: ttk.LabelFrame, row: int, key: str, label: str
    ) -> None:
        ttk.Label(parent, text=label, width=26, anchor="w").grid(
            row=row, column=0, padx=(0, 4), sticky="w"
        )

        tmpl = self.config["templates"].get(key)
        val_text, val_fg = self._tmpl_display(tmpl)

        val_label = ttk.Label(
            parent, text=val_text, width=14, anchor="center", foreground=val_fg
        )
        val_label.grid(row=row, column=1, padx=4)
        self._tmpl_labels[key] = val_label

        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=row, column=2, padx=(4, 0))

        ttk.Button(
            btn_frame,
            text="\U0001f4f7",  # 📷
            width=3,
            command=lambda k=key: self._start_region_capture(k),
        ).pack(side="left", padx=1)

        ttk.Button(
            btn_frame,
            text="\U0001f4cb",  # 📋
            width=3,
            command=lambda k=key: self._paste_template(k),
        ).pack(side="left", padx=1)

        ttk.Button(
            btn_frame,
            text="Test",
            width=4,
            command=lambda k=key: self._test_template(k),
        ).pack(side="left", padx=1)

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

        self._status_var.set(f"Click on \"{label}\" in the game...")
        self.root.attributes("-alpha", self._CAPTURE_ALPHA)

        # Delay so the [Set] button click itself isn't captured
        self.root.after(400, self._listen_for_click, key)

    def _listen_for_click(self, key: str) -> None:
        def on_click(x, y, button, pressed):
            if pressed and button == pynput_mouse.Button.left:
                # Schedule UI update on the tkinter main thread
                self.root.after(0, self._finish_position_capture, key, x, y)
                return False  # stop listener

        listener = pynput_mouse.Listener(on_click=on_click)
        listener.start()

    def _finish_position_capture(self, key: str, x: int, y: int) -> None:
        self.config["positions"][key] = [x, y]
        self._capturing = False
        self.root.attributes("-alpha", self._WINDOW_ALPHA)

        lbl = self._pos_labels.get(key)
        if lbl:
            lbl.config(text=f"({x}, {y})", foreground="#006600")

        self._status_var.set(f"\u2713  {key} = ({x}, {y})")
        self._auto_save()

    # ==================================================================
    #  Region capture  (for detection templates)
    # ==================================================================

    def _start_region_capture(self, key: str) -> None:
        if self._capturing:
            return
        self._capturing = True

        self._status_var.set("Taking screenshot...")
        self.root.withdraw()  # hide panel completely
        self.root.update()

        # Small delay so the panel disappears before the screenshot
        self.root.after(400, self._do_region_capture, key)

    def _do_region_capture(self, key: str) -> None:
        screenshot = pyautogui.screenshot()

        def on_complete(cropped: Image.Image) -> None:
            filename = f"{key}.png"
            filepath = os.path.join(_IMG_DIR, filename)
            cropped.save(filepath)

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
    #  Paste from clipboard
    # ==================================================================

    def _paste_template(self, key: str) -> None:
        try:
            img = ImageGrab.grabclipboard()
        except Exception:
            img = None

        if img is None or not isinstance(img, Image.Image):
            messagebox.showwarning(
                "No Image",
                "No image found on the clipboard.\n\n"
                "Copy a screenshot first, then click Paste.",
            )
            return

        filename = f"{key}.png"
        filepath = os.path.join(_IMG_DIR, filename)
        img.save(filepath)

        self.config["templates"][key] = filename

        lbl = self._tmpl_labels.get(key)
        if lbl:
            lbl.config(text=f"\u2713 {filename}", foreground="#006600")

        self._status_var.set(f"\u2713  Pasted template: {filename}")
        self._auto_save()

    # ==================================================================
    #  Test template detection
    # ==================================================================

    def _test_template(self, key: str) -> None:
        """Take a screenshot and try to find the template on screen."""
        tmpl_file = self.config["templates"].get(key)
        if not tmpl_file:
            self._status_var.set(f"\u2717  No template set for {key}")
            return

        filepath = os.path.join(_IMG_DIR, tmpl_file)
        if not os.path.isfile(filepath):
            self._status_var.set(f"\u2717  Template file missing: {tmpl_file}")
            return

        self._status_var.set(f"Testing {key}...")
        self.root.attributes("-alpha", self._CAPTURE_ALPHA)
        self.root.update()

        # Small delay so panel fades before screenshot
        self.root.after(400, self._do_test_template, key, filepath)

    def _do_test_template(self, key: str, filepath: str) -> None:
        """Perform the actual template match test."""
        try:
            screenshot = pyautogui.screenshot()
            screen_arr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            template = cv2.imread(filepath, cv2.IMREAD_GRAYSCALE)

            if template is None:
                self.root.attributes("-alpha", self._WINDOW_ALPHA)
                self._status_var.set(f"\u2717  Could not load template: {key}")
                return

            result = cv2.matchTemplate(screen_arr, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            confidence = round(max_val * 100, 1)

            self.root.attributes("-alpha", self._WINDOW_ALPHA)

            if max_val >= 0.8:
                cx = max_loc[0] + template.shape[1] // 2
                cy = max_loc[1] + template.shape[0] // 2
                self._status_var.set(
                    f"\u2713  {key}: FOUND at ({cx}, {cy}) — {confidence}%"
                )
            else:
                self._status_var.set(
                    f"\u2717  {key}: NOT FOUND — best match {confidence}%"
                )
        except Exception as exc:
            self.root.attributes("-alpha", self._WINDOW_ALPHA)
            self._status_var.set(f"\u2717  Test error: {exc}")

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
        self._status_var.set("\u2713  Config reloaded from file")

    def _reset(self) -> None:
        if messagebox.askyesno("Reset", "Clear ALL positions and templates?"):
            self.config = default_config()
            save_config(self.config)
            self._refresh_all()
            self._status_var.set("\u2713  Config reset to defaults")

    def _refresh_all(self) -> None:
        """Re-render every label from the current config dict."""
        for group in POSITION_SCHEMA.values():
            for key in group:
                lbl = self._pos_labels.get(key)
                if lbl:
                    pos = self.config["positions"].get(key)
                    text, fg = self._pos_display(pos)
                    lbl.config(text=text, foreground=fg)

        for group in TEMPLATE_SCHEMA.values():
            for key in group:
                lbl = self._tmpl_labels.get(key)
                if lbl:
                    tmpl = self.config["templates"].get(key)
                    text, fg = self._tmpl_display(tmpl)
                    lbl.config(text=text, foreground=fg)

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

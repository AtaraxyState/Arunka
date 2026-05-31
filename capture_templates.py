"""
Template capture tool — run this whenever the game UI changes.

Usage:
    python capture_templates.py

Controls:
    - Drag to select a region
    - Type a name and press Enter to save
    - Press Escape or close to quit
"""

import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk
import numpy as np
from pathlib import Path
from loguru import logger

from config import cfg
from bot.window import find_window, capture_window

TEMPLATES_DIR = Path("assets/templates")
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


class TemplateCapturer:
    def __init__(self, hwnd: int):
        self.hwnd = hwnd
        self.screen_np = capture_window(hwnd)

        # Convert BGR (OpenCV) → RGB for PIL
        rgb = self.screen_np[:, :, ::-1]
        self.pil_image = Image.fromarray(rgb)

        self.root = tk.Tk()
        self.root.title("Template Capture — drag to select, Enter to save, Esc to quit")
        self.root.resizable(False, False)

        self.tk_image = ImageTk.PhotoImage(self.pil_image)
        self.canvas = tk.Canvas(
            self.root,
            width=self.pil_image.width,
            height=self.pil_image.height,
            cursor="crosshair"
        )
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

        # Status bar
        self.status = tk.StringVar(value="Drag to select a UI element")
        tk.Label(self.root, textvariable=self.status, anchor="w", bg="#222", fg="white").pack(fill=tk.X)

        # Draw existing templates as overlays
        self._draw_existing_templates()

        # Selection state
        self.start_x = self.start_y = 0
        self.rect_id = None
        self.selection = None

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<F5>", lambda e: self._refresh())

        self.root.mainloop()

    def _draw_existing_templates(self):
        """Show already-saved templates as green overlays so user knows what exists."""
        import cv2
        for png in sorted(TEMPLATES_DIR.glob("*.png")):
            tmpl = cv2.imread(str(png))
            if tmpl is None:
                continue
            import cv2 as _cv
            result = _cv.matchTemplate(self.screen_np, tmpl, _cv.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = _cv.minMaxLoc(result)
            if max_val >= 0.85:
                h, w = tmpl.shape[:2]
                x, y = max_loc
                self.canvas.create_rectangle(x, y, x + w, y + h, outline="#00ff00", width=2)
                self.canvas.create_text(x + 2, y - 6, anchor=tk.NW, text=png.stem, fill="#00ff00", font=("Helvetica", 8))

    def _on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#ff0000", width=2, dash=(4, 2)
        )

    def _on_drag(self, event):
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def _on_release(self, event):
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)

        if x2 - x1 < 5 or y2 - y1 < 5:
            self.status.set("Selection too small — try again")
            return

        self.selection = (x1, y1, x2, y2)
        self.status.set(f"Selected {x2-x1}×{y2-y1}px — type a name and press Enter, or drag a new selection")

        # Ask for name inline (simple dialog)
        name = simpledialog.askstring(
            "Name this template",
            "Template name (e.g. shop_refresh_btn):",
            parent=self.root
        )

        if not name or not name.strip():
            self.status.set("Cancelled — drag to try again")
            return

        name = name.strip().replace(" ", "_").lower()
        self._save(name, x1, y1, x2, y2)

    def _save(self, name: str, x1, y1, x2, y2):
        dest = TEMPLATES_DIR / f"{name}.png"

        if dest.exists():
            overwrite = messagebox.askyesno("Overwrite?", f"'{name}.png' already exists. Overwrite?")
            if not overwrite:
                self.status.set("Skipped — drag to select another element")
                return

        crop = self.pil_image.crop((x1, y1, x2, y2))
        crop.save(dest)
        logger.info(f"Saved template: {dest}")
        self.status.set(f"✓ Saved '{name}.png' ({x2-x1}×{y2-y1}px) — drag to capture another")

        # Draw saved region in green
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#00ff00", width=2)
        self.canvas.create_text(x1 + 2, y1 - 6, anchor=tk.NW, text=name, fill="#00ff00", font=("Helvetica", 8))

        if self.rect_id:
            self.canvas.delete(self.rect_id)

    def _refresh(self):
        """Re-capture the window (F5) in case the screen changed."""
        self.screen_np = capture_window(self.hwnd)
        rgb = self.screen_np[:, :, ::-1]
        self.pil_image = Image.fromarray(rgb)
        self.tk_image = ImageTk.PhotoImage(self.pil_image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self._draw_existing_templates()
        self.status.set("Refreshed — drag to select a UI element")


def main():
    title = cfg["window"]["title"]
    try:
        hwnd = find_window(title)
    except RuntimeError as e:
        print(f"Error: {e}")
        return

    print(f"Found '{title}' — opening capture tool...")
    print("  Drag to select a UI element, type a name, press Enter to save")
    print("  F5 to refresh the screenshot, Esc to quit")
    print(f"  Templates saved to: {TEMPLATES_DIR.resolve()}")

    TemplateCapturer(hwnd)


if __name__ == "__main__":
    main()

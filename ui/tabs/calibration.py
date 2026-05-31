"""
Calibration tab — two modes:
  Template mode  : drag a region → saves a PNG for image recognition
  Nav click mode : single click  → saves an (x, y) point for menu navigation
"""

import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
from pathlib import Path
from tkinter import simpledialog, messagebox

from ui.widgets import SectionLabel, DimLabel
from config import cfg
from bot.window import find_window, capture_window
from bot import navigator

ACCENT  = "#e94560"
SUCCESS = "#4ecca3"

TEMPLATES_DIR = Path("assets/templates")
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_TEMPLATES = {
    "Secret Shop": [
        ("shop_refresh_btn",         "Refresh button (bottom-left)"),
        ("shop_confirm_refresh_btn", "Confirm refresh dialog"),
        ("shop_buy_btn",             "Buy button (item row, right side)"),
        ("shop_confirm_buy_btn",     "Buy button inside confirm dialog"),
        ("item_covenant_bookmark",   "Covenant bookmark icon"),
        ("item_mystic_medal",        "Mystic medal icon"),
    ],
    "Dailies": [
        ("daily_missions_tab",    "Daily missions tab"),
        ("daily_claim_all_btn",   "Claim all (dailies)"),
        ("mailbox_tab",           "Mailbox tab"),
        ("mailbox_claim_all_btn", "Claim all (mailbox)"),
        ("reputation_tab",        "Reputation tab"),
        ("reputation_claim_btn",  "Claim (reputation)"),
    ],
}

REQUIRED_NAV = {
    "Secret Shop": [
        ("nav_lobby",          "Lobby / main screen"),
        ("nav_shop_tab",       "Shop icon in nav bar"),
        ("nav_secret_shop",    "Secret Shop entry"),
    ],
    "Dailies": [
        ("nav_daily_tab",      "Daily missions icon"),
        ("nav_mailbox",        "Mailbox icon"),
        ("nav_reputation",     "Reputation icon"),
    ],
}

MODE_TEMPLATE = "template"
MODE_NAV      = "nav"


class CalibrationTab:
    def __init__(self, parent, logs):
        self.parent = parent
        self.logs   = logs
        self.hwnd   = None
        self._mode  = MODE_TEMPLATE
        self._pending_template = None
        self._pending_nav      = None
        self._sel_start = None
        self._sel_rect  = None
        self._scale     = 1.0
        self._screen_np = None
        self._pil_image = None
        self._canvas    = None
        self._tk_image  = None
        self._guided_queue = []
        self._dot_labels = {}   # name → ctk label showing ● color
        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        # Root split: left panel | right preview
        self.parent.grid_columnconfigure(1, weight=1)
        self.parent.grid_rowconfigure(0, weight=1)

        # ── Left panel ────────────────────────────────────────────────────────
        left = ctk.CTkFrame(self.parent, fg_color="#13131f", width=280, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_propagate(False)
        left.grid_rowconfigure(2, weight=1)

        # Mode selector
        mode_frame = ctk.CTkFrame(left, fg_color="#1a1a2e", corner_radius=8)
        mode_frame.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(mode_frame, text="Mode",
                     font=ctk.CTkFont("Helvetica", 11, "bold"),
                     text_color="#aaa").pack(anchor="w", padx=10, pady=(8, 4))

        self._mode_var = ctk.StringVar(value=MODE_TEMPLATE)
        ctk.CTkRadioButton(mode_frame, text="Template  (drag region)",
                           variable=self._mode_var, value=MODE_TEMPLATE,
                           command=self._on_mode_change,
                           radiobutton_width=16, radiobutton_height=16,
                           fg_color=ACCENT).pack(anchor="w", padx=10, pady=2)
        ctk.CTkRadioButton(mode_frame, text="Nav click  (single click)",
                           variable=self._mode_var, value=MODE_NAV,
                           command=self._on_mode_change,
                           radiobutton_width=16, radiobutton_height=16,
                           fg_color=ACCENT).pack(anchor="w", padx=10, pady=(2, 4))

        self._hint_label = ctk.CTkLabel(mode_frame,
                                        text="Drag a box around a UI element",
                                        font=ctk.CTkFont("Helvetica", 10),
                                        text_color="#555", wraplength=240)
        self._hint_label.pack(anchor="w", padx=10, pady=(0, 8))

        # Scrollable checklist
        scroll = ctk.CTkScrollableFrame(left, fg_color="transparent", label_text="")
        scroll.pack(fill="both", expand=True, padx=8, pady=4)
        self._list_container = scroll
        self._build_checklist()

        # Guided button
        ctk.CTkButton(left, text="Capture All Missing  (guided)",
                      fg_color=ACCENT, hover_color="#c73652",
                      font=ctk.CTkFont("Helvetica", 12, "bold"),
                      corner_radius=8, height=38,
                      command=self._capture_all_guided).pack(
                          fill="x", padx=12, pady=(6, 12))

        # ── Right panel ───────────────────────────────────────────────────────
        right = ctk.CTkFrame(self.parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        top_bar = ctk.CTkFrame(right, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkLabel(top_bar, text="Game Preview",
                     font=ctk.CTkFont("Helvetica", 13, "bold")).pack(side="left")
        ctk.CTkButton(top_bar, text="↺  Refresh screenshot",
                      width=160, height=30, corner_radius=6,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      command=self._refresh_screenshot).pack(side="right")

        self._preview_frame = ctk.CTkFrame(right, fg_color="#0d0d1a", corner_radius=8)
        self._preview_frame.grid(row=1, column=0, sticky="nsew")
        self._preview_frame.bind("<Configure>", self._on_preview_resize)

        self._placeholder = ctk.CTkLabel(
            self._preview_frame,
            text="Click  'Refresh screenshot'  to capture the game window.\n\n"
                 "Template mode → drag a box to mark a UI element\n"
                 "Nav click mode → single click to mark a navigation point",
            font=ctk.CTkFont("Helvetica", 11),
            text_color="#444")
        self._placeholder.place(relx=0.5, rely=0.5, anchor="center")

    def _build_checklist(self):
        for w in self._list_container.winfo_children():
            w.destroy()
        self._dot_labels.clear()

        def _section(title):
            ctk.CTkLabel(self._list_container, text=title,
                         font=ctk.CTkFont("Helvetica", 11, "bold"),
                         text_color=ACCENT).pack(anchor="w", pady=(10, 2))

        def _group_header(title):
            ctk.CTkLabel(self._list_container, text=title,
                         font=ctk.CTkFont("Helvetica", 10, "bold"),
                         text_color="#888").pack(anchor="w", pady=(6, 1))

        def _row(name, label, kind):
            row = ctk.CTkFrame(self._list_container, fg_color="transparent")
            row.pack(fill="x", pady=1)
            dot = ctk.CTkLabel(row, text="●", width=18,
                               font=ctk.CTkFont("Helvetica", 12),
                               text_color=ACCENT)
            dot.pack(side="left")
            ctk.CTkLabel(row, text=label,
                         font=ctk.CTkFont("Helvetica", 10),
                         text_color="#ccc", anchor="w",
                         wraplength=140).pack(side="left", fill="x", expand=True)
            cmd = (lambda n=name: self._start_template_capture(n)) if kind == "t" \
                  else (lambda n=name: self._start_nav_record(n))
            btn_text = "Capture" if kind == "t" else "Record"
            ctk.CTkButton(row, text=btn_text, width=60, height=24, corner_radius=6,
                          fg_color="#1e1e3a", hover_color="#2a2a50",
                          font=ctk.CTkFont("Helvetica", 10),
                          command=cmd).pack(side="right")
            self._dot_labels[name] = dot

        _section("Templates")
        for group, items in REQUIRED_TEMPLATES.items():
            _group_header(group)
            for name, label in items:
                _row(name, label, "t")

        _section("Nav Click Points")
        for group, items in REQUIRED_NAV.items():
            _group_header(group)
            for name, label in items:
                _row(name, label, "n")

        self._refresh_dots()

    # ── Mode ──────────────────────────────────────────────────────────────────

    def _on_mode_change(self):
        self._mode = self._mode_var.get()
        self._pending_template = None
        self._pending_nav = None
        if self._canvas:
            cur = "crosshair" if self._mode == MODE_TEMPLATE else "tcross"
            self._canvas.configure(cursor=cur)
        hints = {
            MODE_TEMPLATE: "Drag a box around a UI element",
            MODE_NAV:      "Single click on a button to record its position",
        }
        self._hint_label.configure(text=hints[self._mode])

    # ── Screenshot ────────────────────────────────────────────────────────────

    def _on_preview_resize(self, event):
        """Re-render the preview when the window is resized."""
        if self._pil_image is not None:
            self._show_image(self._pil_image)

    def _refresh_screenshot(self):
        try:
            # ADB-based: find_window just verifies connection, title unused
            self.hwnd = find_window("")
        except Exception as e:
            messagebox.showerror("ADB not connected",
                                 f"Could not connect to emulator:\n{e}\n\n"
                                 "Go to Settings and click Connect ADB.")
            return
        self.logs.log("Capturing screenshot from emulator…", "info")
        try:
            self._screen_np = capture_window(self.hwnd)
        except Exception as e:
            messagebox.showerror("Screenshot failed", str(e))
            return
        rgb = self._screen_np[:, :, ::-1]
        self._pil_image = Image.fromarray(rgb)
        self._show_image(self._pil_image)
        self.logs.log("Screenshot captured", "success")

    def _show_image(self, img: Image.Image):
        # Scale to fit whatever space the preview frame currently has
        self._preview_frame.update_idletasks()
        max_w = max(self._preview_frame.winfo_width()  - 4, 400)
        max_h = max(self._preview_frame.winfo_height() - 4, 300)
        self._scale = min(max_w / img.width, max_h / img.height, 1.0)
        dw = int(img.width  * self._scale)
        dh = int(img.height * self._scale)
        disp = img.resize((dw, dh), Image.LANCZOS)

        if self._canvas:
            self._canvas.destroy()
        self._placeholder.place_forget()

        cur = "crosshair" if self._mode == MODE_TEMPLATE else "tcross"
        self._canvas = tk.Canvas(self._preview_frame, width=dw, height=dh,
                                  bg="#0d0d1a", cursor=cur, highlightthickness=0)
        self._canvas.place(x=0, y=0)
        self._tk_image = ImageTk.PhotoImage(disp)
        self._canvas.create_image(0, 0, anchor="nw", image=self._tk_image)
        self._canvas.bind("<ButtonPress-1>",   self._on_press)
        self._canvas.bind("<B1-Motion>",       self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._draw_overlays()

    def _draw_overlays(self):
        import cv2
        if self._screen_np is None or self._canvas is None:
            return
        for name, _ in sum(REQUIRED_TEMPLATES.values(), []):
            path = TEMPLATES_DIR / f"{name}.png"
            if not path.exists():
                continue
            tmpl = cv2.imread(str(path))
            if tmpl is None:
                continue
            res = cv2.matchTemplate(self._screen_np, tmpl, cv2.TM_CCOEFF_NORMED)
            _, val, _, loc = cv2.minMaxLoc(res)
            if val >= 0.85:
                h, w = tmpl.shape[:2]
                x1, y1 = int(loc[0]*self._scale), int(loc[1]*self._scale)
                x2, y2 = int((loc[0]+w)*self._scale), int((loc[1]+h)*self._scale)
                self._canvas.create_rectangle(x1, y1, x2, y2, outline=SUCCESS, width=2)
                self._canvas.create_text(x1+2, y1-8, anchor="nw",
                                          text=name, fill=SUCCESS, font=("Helvetica", 7))
        for name, pt in navigator._load_points().items():
            cx = int(pt["x"] * self._scale)
            cy = int(pt["y"] * self._scale)
            r = 6
            self._canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                      fill="#00ccff", outline="white", width=1)
            self._canvas.create_text(cx+10, cy, anchor="w",
                                      text=name, fill="#00ccff", font=("Helvetica", 7))

    # ── Input events ──────────────────────────────────────────────────────────

    def _on_press(self, event):
        if self._mode == MODE_TEMPLATE:
            self._sel_start = (event.x, event.y)
            if self._sel_rect:
                self._canvas.delete(self._sel_rect)

    def _on_drag(self, event):
        if self._mode == MODE_TEMPLATE and self._sel_start:
            if self._sel_rect:
                self._canvas.delete(self._sel_rect)
            x0, y0 = self._sel_start
            self._sel_rect = self._canvas.create_rectangle(
                x0, y0, event.x, event.y, outline=ACCENT, width=2, dash=(4, 2))

    def _on_release(self, event):
        if self._mode == MODE_TEMPLATE:
            self._finish_template_selection(event.x, event.y)
        else:
            self._finish_nav_click(event.x, event.y)

    # ── Template capture ──────────────────────────────────────────────────────

    def _start_template_capture(self, name: str):
        if self._canvas is None:
            messagebox.showinfo("Screenshot needed", "Click 'Refresh screenshot' first.")
            return
        self._mode_var.set(MODE_TEMPLATE)
        self._on_mode_change()
        self._pending_template = name
        label = next((l for g in REQUIRED_TEMPLATES.values() for n, l in g if n == name), name)
        self.logs.log(f"Drag a box around: {label}", "info")

    def _finish_template_selection(self, ex, ey):
        if not self._sel_start:
            return
        x0, y0 = self._sel_start
        sx0, sy0 = min(x0, ex), min(y0, ey)
        sx1, sy1 = max(x0, ex), max(y0, ey)
        self._sel_start = None
        if sx1-sx0 < 5 or sy1-sy0 < 5:
            return

        s = self._scale
        rx0, ry0, rx1, ry1 = int(sx0/s), int(sy0/s), int(sx1/s), int(sy1/s)

        name = self._pending_template or simpledialog.askstring(
            "Name this template", "Template name:", parent=self.parent)
        if not name:
            return
        name = name.strip().replace(" ", "_").lower()
        self._pending_template = None

        dest = TEMPLATES_DIR / f"{name}.png"
        if dest.exists() and not messagebox.askyesno("Overwrite?", f"'{name}.png' exists. Overwrite?"):
            # Skipped — still advance guided queue
            if self._guided_queue is not None:
                self.parent.after(300, self._next_guided)
            return

        self._pil_image.crop((rx0, ry0, rx1, ry1)).save(dest)
        from bot.vision import invalidate_cache
        invalidate_cache(name)
        self.logs.log(f"Saved template: {name}.png  ({rx1-rx0}×{ry1-ry0}px)", "success")

        if self._sel_rect:
            self._canvas.delete(self._sel_rect)
        self._canvas.create_rectangle(sx0, sy0, sx1, sy1, outline=SUCCESS, width=2)
        self._canvas.create_text(sx0+2, sy0-8, anchor="nw",
                                  text=name, fill=SUCCESS, font=("Helvetica", 7))
        self._refresh_dots()
        # Always advance guided queue after a save (even if queue is now empty)
        if self._guided_queue is not None:
            self.parent.after(300, self._next_guided)

    # ── Nav click ─────────────────────────────────────────────────────────────

    def _start_nav_record(self, name: str):
        if self._canvas is None:
            messagebox.showinfo("Screenshot needed", "Click 'Refresh screenshot' first.")
            return
        self._mode_var.set(MODE_NAV)
        self._on_mode_change()
        self._pending_nav = name
        label = next((l for g in REQUIRED_NAV.values() for n, l in g if n == name), name)
        self.logs.log(f"Click on: {label}", "info")

    def _finish_nav_click(self, sx, sy):
        rx, ry = int(sx/self._scale), int(sy/self._scale)
        name = self._pending_nav or simpledialog.askstring(
            "Name this nav point", "Nav point name:", parent=self.parent)
        if not name:
            return
        name = name.strip().replace(" ", "_").lower()
        self._pending_nav = None

        navigator.save_point(name, rx, ry)
        self.logs.log(f"Saved nav point: {name}  →  ({rx}, {ry})", "success")

        r = 6
        self._canvas.create_oval(sx-r, sy-r, sx+r, sy+r,
                                  fill="#00ccff", outline="white", width=1)
        self._canvas.create_text(sx+10, sy, anchor="w",
                                  text=name, fill="#00ccff", font=("Helvetica", 7))
        self._refresh_dots()
        if self._guided_queue is not None:
            self.parent.after(300, self._next_guided)

    # ── Guided capture ────────────────────────────────────────────────────────

    def _capture_all_guided(self):
        # Auto-take screenshot if not done yet
        if self._canvas is None:
            self.logs.log("No screenshot yet — capturing automatically…", "info")
            self._refresh_screenshot()
            if self._canvas is None:
                return  # refresh failed (error already shown)

        missing_t = [(n, "t", l) for g in REQUIRED_TEMPLATES.values()
                     for n, l in g if not (TEMPLATES_DIR / f"{n}.png").exists()]
        existing  = navigator._load_points()
        missing_n = [(n, "n", l) for g in REQUIRED_NAV.values()
                     for n, l in g if n not in existing]
        self._guided_queue = missing_t + missing_n

        if not self._guided_queue:
            messagebox.showinfo("All done!", "Everything is already captured.")
            return

        self.logs.log(f"Guided capture started — {len(self._guided_queue)} items to go", "info")
        self._next_guided()

    def _next_guided(self):
        if not self._guided_queue:
            self.logs.log("Guided capture complete!", "success")
            self._hint_label.configure(
                text="All done! Drag a box to capture more manually.")
            return

        name, kind, label = self._guided_queue.pop(0)
        remaining = len(self._guided_queue)

        # Set mode directly without calling _on_mode_change (which clears pending)
        if kind == "t":
            self._mode = MODE_TEMPLATE
            self._mode_var.set(MODE_TEMPLATE)
            self._pending_template = name
            self._pending_nav      = None
        else:
            self._mode = MODE_NAV
            self._mode_var.set(MODE_NAV)
            self._pending_nav      = name
            self._pending_template = None

        # Update canvas cursor
        if self._canvas:
            self._canvas.configure(
                cursor="crosshair" if kind == "t" else "tcross")

        # Show clear instruction in hint label (visible without switching tabs)
        action = "Drag box around" if kind == "t" else "Click on"
        hint = f"[{remaining + 1} of {remaining + 1 + len(self._guided_queue)}]  {action}: {label}"
        self._hint_label.configure(text=hint)
        self.logs.log(f"[{remaining} left]  {action}: {label}", "info")

    # ── Dots ──────────────────────────────────────────────────────────────────

    def _refresh_dots(self):
        pts = navigator._load_points()
        for name, dot in self._dot_labels.items():
            is_template = any(name == n for g in REQUIRED_TEMPLATES.values() for n, _ in g)
            done = (TEMPLATES_DIR / f"{name}.png").exists() if is_template else name in pts
            dot.configure(text_color=SUCCESS if done else ACCENT)

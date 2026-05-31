"""
History tab - browse the rolling history of past secret-shop runs.

Two levels of navigation:
  * Left sidebar : list of runs. Pick one to analyse.
  * Right panel  : roll browser for the selected run. Left/Right arrow keys
                   (or the on-screen arrows) move between refreshes; Up/Down
                   toggle the Top/Bottom screenshot. An overlay marks what the
                   bot found (green = bought, amber = found but not bought).

Nothing is ever deleted automatically - use Delete roll / Delete run / Clear all.
"""

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk

from bot import history

ACCENT  = "#e94560"
SUCCESS = "#4ecca3"
WARNING = "#f0a500"
INFO    = "#00ccff"

STATUS_COLOR = {
    "done": SUCCESS,
    "running": WARNING,
    "stopped": WARNING,
    "error": ACCENT,
}


class HistoryTab:
    def __init__(self, parent, logs):
        self.parent = parent
        self.logs   = logs
        self.runs        = []
        self.run_id      = None
        self.run_data    = None
        self.rolls       = []
        self.roll_idx    = 0
        self.which       = "top"
        self.show_overlay = True
        self._scale      = 1.0
        self._pil_image  = None
        self._canvas     = None
        self._tk_image   = None
        self._build()
        self._refresh_runs()

    # -- Layout --------------------------------------------------------------

    def _build(self):
        self.parent.grid_columnconfigure(1, weight=1)
        self.parent.grid_rowconfigure(0, weight=1)

        # ---- Left: run list ----
        left = ctk.CTkFrame(self.parent, fg_color="#13131f", width=270, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_propagate(False)
        left.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(left, text="Runs",
                     font=ctk.CTkFont("Helvetica", 13, "bold")).pack(
                         anchor="w", padx=14, pady=(14, 2))
        self._size_lbl = ctk.CTkLabel(left, text="",
                                      font=ctk.CTkFont("Helvetica", 10),
                                      text_color="#555")
        self._size_lbl.pack(anchor="w", padx=14, pady=(0, 6))

        list_frame = ctk.CTkFrame(left, fg_color="#0d0d1a", corner_radius=8)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self._runlist = tk.Listbox(list_frame, bg="#0d0d1a", fg="#ccc",
                                   selectbackground=ACCENT, selectforeground="white",
                                   relief="flat", highlightthickness=0, borderwidth=0,
                                   font=("Helvetica", 10), activestyle="none")
        self._runlist.pack(fill="both", expand=True, padx=4, pady=4)
        self._runlist.bind("<<ListboxSelect>>", self._on_run_select)

        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 12))
        ctk.CTkButton(btn_row, text="Refresh", height=30, corner_radius=6,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      command=self._refresh_runs).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(btn_row, text="Clear all", height=30, corner_radius=6,
                      fg_color="#2a0a12", hover_color="#3d0f1a", text_color=ACCENT,
                      command=self._clear_all).pack(side="left", fill="x", expand=True)

        # ---- Right: roll browser ----
        right = ctk.CTkFrame(self.parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(right, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self._prev_btn = ctk.CTkButton(bar, text="◀", width=42, height=32, corner_radius=6,
                                       fg_color="#1e1e3a", hover_color="#2a2a50",
                                       command=self._prev_roll)
        self._prev_btn.pack(side="left")
        self._roll_lbl = ctk.CTkLabel(bar, text="No run selected",
                                      font=ctk.CTkFont("Helvetica", 12, "bold"), width=140)
        self._roll_lbl.pack(side="left", padx=8)
        self._next_btn = ctk.CTkButton(bar, text="▶", width=42, height=32, corner_radius=6,
                                       fg_color="#1e1e3a", hover_color="#2a2a50",
                                       command=self._next_roll)
        self._next_btn.pack(side="left")

        self._which_seg = ctk.CTkSegmentedButton(
            bar, values=["Top", "Bottom"], command=self._on_which,
            selected_color=ACCENT, selected_hover_color="#c73652")
        self._which_seg.set("Top")
        self._which_seg.pack(side="left", padx=14)

        self._overlay_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(bar, text="Overlay", variable=self._overlay_var,
                        fg_color=ACCENT, hover_color="#c73652", checkmark_color="white",
                        command=self._on_overlay).pack(side="left", padx=4)

        ctk.CTkButton(bar, text="Export CSV", height=32, corner_radius=6,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      command=self._export_csv).pack(side="right")
        ctk.CTkButton(bar, text="Delete run", height=32, corner_radius=6,
                      fg_color="#2a0a12", hover_color="#3d0f1a", text_color=ACCENT,
                      command=self._delete_run).pack(side="right", padx=(0, 6))
        ctk.CTkButton(bar, text="Delete roll", height=32, corner_radius=6,
                      fg_color="#2a0a12", hover_color="#3d0f1a", text_color=ACCENT,
                      command=self._delete_roll).pack(side="right", padx=(0, 6))

        self._preview = ctk.CTkFrame(right, fg_color="#0d0d1a", corner_radius=8)
        self._preview.grid(row=1, column=0, sticky="nsew")
        self._preview.bind("<Configure>", lambda e: self._render())
        self._preview.bind("<Enter>", lambda e: self._focus_canvas())

        self._placeholder = ctk.CTkLabel(
            self._preview,
            text="Select a run on the left.\n\n"
                 "Left / Right arrows  -  move between refreshes\n"
                 "Up / Down arrows  -  switch Top / Bottom screenshot",
            font=ctk.CTkFont("Helvetica", 11), text_color="#444")
        self._placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # Summary panel
        self._summary = ctk.CTkTextbox(right, height=120, fg_color="#13131f",
                                       text_color="#ccc", corner_radius=8,
                                       font=ctk.CTkFont("Courier New", 11),
                                       state="disabled", wrap="word")
        self._summary.grid(row=2, column=0, sticky="ew", pady=(8, 0))

    # -- Keyboard ------------------------------------------------------------

    def _focus_canvas(self):
        if self._canvas is not None:
            self._canvas.focus_set()

    def _bind_keys(self):
        if self._canvas is None:
            return
        self._canvas.bind("<Left>",  lambda e: self._prev_roll())
        self._canvas.bind("<Right>", lambda e: self._next_roll())
        self._canvas.bind("<Up>",    lambda e: self._set_which("top"))
        self._canvas.bind("<Down>",  lambda e: self._set_which("bottom"))

    # -- Run list ------------------------------------------------------------

    def _refresh_runs(self):
        self.runs = history.list_runs()
        self._runlist.delete(0, tk.END)
        for i, r in enumerate(self.runs):
            label = (f"  {r.get('id','?')}   "
                     f"{r.get('rolls',0)} rolls, {r.get('bought',0)} bought")
            self._runlist.insert(tk.END, label)
            self._runlist.itemconfig(i, foreground=STATUS_COLOR.get(r.get("status"), "#ccc"))
        self._size_lbl.configure(
            text=f"{len(self.runs)} run(s)  -  {history.human_size(history.history_size_bytes())}")
        if not self.runs:
            self._roll_lbl.configure(text="No runs yet")

    def _on_run_select(self, _=None):
        sel = self._runlist.curselection()
        if not sel:
            return
        run_id = self.runs[sel[0]].get("id")
        self._load_run(run_id)

    def _load_run(self, run_id):
        data = history.load_run(run_id)
        if data is None:
            messagebox.showerror("History", f"Could not load run {run_id}")
            return
        self.run_id   = run_id
        self.run_data = data
        self.rolls    = data.get("rolls", [])
        self.roll_idx = 0
        self.which    = "top"
        self._which_seg.set("Top")
        self._render()

    # -- Navigation ----------------------------------------------------------

    def _prev_roll(self):
        if self.rolls and self.roll_idx > 0:
            self.roll_idx -= 1
            self._render()

    def _next_roll(self):
        if self.rolls and self.roll_idx < len(self.rolls) - 1:
            self.roll_idx += 1
            self._render()

    def _on_which(self, value):
        self._set_which(value.lower())

    def _set_which(self, which):
        self.which = which
        self._which_seg.set("Top" if which == "top" else "Bottom")
        self._render()

    def _on_overlay(self):
        self.show_overlay = self._overlay_var.get()
        self._render()

    # -- Rendering -----------------------------------------------------------

    def _current_roll(self):
        if self.rolls and 0 <= self.roll_idx < len(self.rolls):
            return self.rolls[self.roll_idx]
        return None

    def _render(self):
        roll = self._current_roll()
        if roll is None:
            self._roll_lbl.configure(text="No run selected" if not self.run_id else "Empty run")
            self._clear_canvas()
            self._update_summary(None)
            return

        self._roll_lbl.configure(text=f"Roll {roll.get('n','?')}  /  {len(self.rolls)}")

        img_name = roll.get(f"{self.which}_img")
        path = history.roll_image_path(self.run_id, img_name) if img_name else None
        if path is None:
            self._pil_image = None
            self._clear_canvas(message=f"No {self.which} screenshot for this roll.")
        else:
            try:
                self._pil_image = Image.open(path).convert("RGB")
                self._show_image(self._pil_image, roll)
            except Exception as e:
                self._clear_canvas(message=f"Could not open image:\n{e}")

        self._update_summary(roll)

    def _clear_canvas(self, message=None):
        if self._canvas is not None:
            self._canvas.destroy()
            self._canvas = None
        self._placeholder.configure(
            text=message or "Select a run on the left.")
        self._placeholder.place(relx=0.5, rely=0.5, anchor="center")

    def _show_image(self, img, roll):
        self._preview.update_idletasks()
        max_w = max(self._preview.winfo_width() - 4, 400)
        max_h = max(self._preview.winfo_height() - 4, 300)
        self._scale = min(max_w / img.width, max_h / img.height, 1.0)
        dw, dh = int(img.width * self._scale), int(img.height * self._scale)
        disp = img.resize((dw, dh), Image.LANCZOS)

        if self._canvas is not None:
            self._canvas.destroy()
        self._placeholder.place_forget()
        self._canvas = tk.Canvas(self._preview, width=dw, height=dh,
                                 bg="#0d0d1a", highlightthickness=0, takefocus=True)
        self._canvas.place(relx=0.5, rely=0.5, anchor="center")
        self._tk_image = ImageTk.PhotoImage(disp)
        self._canvas.create_image(0, 0, anchor="nw", image=self._tk_image)
        self._bind_keys()
        self._focus_canvas()

        if self.show_overlay:
            self._draw_overlay(roll)

    def _draw_overlay(self, roll):
        dets = roll.get("detections", {}).get(self.which, [])
        s = self._scale
        for d in dets:
            cx, cy = int(d["x"] * s), int(d["y"] * s)
            color = SUCCESS if d.get("status") == "bought" else WARNING
            r = int(34 * s)
            self._canvas.create_rectangle(cx - r, cy - r, cx + r, cy + r,
                                          outline=color, width=2)
            tag = f"{d.get('score', 0):.2f}"
            self._canvas.create_text(cx - r, cy - r - 8, anchor="nw",
                                     text=tag, fill=color, font=("Helvetica", 8, "bold"))

    def _update_summary(self, roll):
        self._summary.configure(state="normal")
        self._summary.delete("1.0", tk.END)
        if roll is None:
            self._summary.configure(state="disabled")
            return
        lines = []
        lines.append(f"Outcome : {roll.get('outcome', 'n/a')}")
        lines.append(f"Found   : {roll.get('found', 0)}    Bought: {roll.get('bought', 0)}")
        warn = roll.get("warnings", [])
        if warn:
            lines.append("Warnings: " + "; ".join(warn))
        for side in ("top", "bottom"):
            dets = roll.get("detections", {}).get(side, [])
            if dets:
                lines.append(f"[{side}]")
                for d in dets:
                    lines.append(f"   {d['template']:<24} score={d.get('score',0):.2f}  {d.get('status')}")
        self._summary.insert("1.0", "\n".join(lines))
        self._summary.configure(state="disabled")

    # -- Admin ---------------------------------------------------------------

    def _delete_roll(self):
        roll = self._current_roll()
        if roll is None or not self.run_id:
            return
        if not messagebox.askyesno("Delete roll", f"Delete roll {roll.get('n')} from this run?"):
            return
        if history.delete_roll(self.run_id, roll.get("n")):
            self.logs.log(f"Deleted roll {roll.get('n')} from {self.run_id}", "warn")
            self._load_run(self.run_id)
            self._refresh_runs()

    def _delete_run(self):
        if not self.run_id:
            return
        if not messagebox.askyesno("Delete run", f"Delete the entire run {self.run_id}?"):
            return
        if history.delete_run(self.run_id):
            self.logs.log(f"Deleted run {self.run_id}", "warn")
            self.run_id = None
            self.run_data = None
            self.rolls = []
            self._clear_canvas()
            self._update_summary(None)
            self._roll_lbl.configure(text="No run selected")
            self._refresh_runs()

    def _clear_all(self):
        if not messagebox.askyesno("Clear all history",
                                   "Delete ALL recorded runs? This cannot be undone."):
            return
        if history.clear_all():
            self.logs.log("Cleared all history", "warn")
            self.run_id = None
            self.rolls = []
            self._clear_canvas()
            self._update_summary(None)
            self._roll_lbl.configure(text="No run selected")
            self._refresh_runs()

    def _export_csv(self):
        if not self.run_id:
            return
        path = history.export_csv(self.run_id)
        if path:
            self.logs.log(f"Exported CSV: {path}", "success")
            messagebox.showinfo("Export CSV", f"Saved:\n{path}")
        else:
            messagebox.showerror("Export CSV", "Export failed - see logs.")

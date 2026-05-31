"""Routes tab — build and manage named navigation routes."""

import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from ui.widgets import SectionLabel, DimLabel
from bot import navigator

ACCENT  = "#e94560"
SUCCESS = "#4ecca3"


class RoutesTab:
    def __init__(self, parent, logs):
        self.parent = parent
        self.logs   = logs
        self._selected_route = None
        self._build()
        self._refresh_route_list()

    def _build(self):
        self.parent.grid_columnconfigure(1, weight=1)
        self.parent.grid_rowconfigure(0, weight=1)

        # ── Left: route list ──────────────────────────────────────────────────
        left = ctk.CTkFrame(self.parent, fg_color="#13131f", width=240, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_propagate(False)
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left, text="Saved Routes",
                     font=ctk.CTkFont("Helvetica", 13, "bold")).pack(anchor="w", padx=14, pady=(14, 2))
        ctk.CTkLabel(left, text="Click a route to edit it",
                     font=ctk.CTkFont("Helvetica", 10), text_color="#555").pack(anchor="w", padx=14, pady=(0, 8))

        # Route listbox (tk.Listbox styled dark)
        list_frame = ctk.CTkFrame(left, fg_color="#0d0d1a", corner_radius=8)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self._listbox = tk.Listbox(list_frame, bg="#0d0d1a", fg="#ccc",
                                    selectbackground=ACCENT, selectforeground="white",
                                    relief="flat", highlightthickness=0, borderwidth=0,
                                    font=("Helvetica", 10), activestyle="none")
        self._listbox.pack(fill="both", expand=True, padx=4, pady=4)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 12))
        ctk.CTkButton(btn_row, text="+ New", height=30, corner_radius=6,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      command=self._new_route).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(btn_row, text="Delete", height=30, corner_radius=6,
                      fg_color="#2a0a12", hover_color="#3d0f1a", text_color=ACCENT,
                      command=self._delete_route).pack(side="left", fill="x", expand=True)

        # ── Right: editor ─────────────────────────────────────────────────────
        right = ctk.CTkFrame(self.parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        # Meta
        meta = ctk.CTkFrame(right, fg_color="#1a1a2e", corner_radius=8)
        meta.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        meta.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(meta, text="Route info",
                     font=ctk.CTkFont("Helvetica", 12, "bold")).grid(
                         row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 6))

        ctk.CTkLabel(meta, text="Name", text_color="#888").grid(row=1, column=0, sticky="w", padx=14, pady=4)
        self._name_var = ctk.StringVar()
        ctk.CTkEntry(meta, textvariable=self._name_var, placeholder_text="e.g. to_secret_shop",
                     height=32, corner_radius=6).grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=4)

        ctk.CTkLabel(meta, text="Description", text_color="#888").grid(row=2, column=0, sticky="w", padx=14, pady=4)
        self._desc_var = ctk.StringVar()
        ctk.CTkEntry(meta, textvariable=self._desc_var, placeholder_text="Optional description",
                     height=32, corner_radius=6).grid(row=2, column=1, sticky="ew", padx=(0, 14), pady=(4, 12))

        # Step builder
        steps = ctk.CTkFrame(right, fg_color="#1a1a2e", corner_radius=8)
        steps.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        steps.grid_columnconfigure(0, weight=1)
        steps.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(steps, text="Steps  —  top = first click",
                     font=ctk.CTkFont("Helvetica", 12, "bold")).grid(
                         row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 6))

        # Steps listbox
        steps_list_frame = ctk.CTkFrame(steps, fg_color="#0d0d1a", corner_radius=6)
        steps_list_frame.grid(row=1, column=0, sticky="nsew", padx=(14, 4), pady=(0, 8))

        self._steps_lb = tk.Listbox(steps_list_frame, bg="#0d0d1a", fg="#ccc",
                                     selectbackground=ACCENT, selectforeground="white",
                                     relief="flat", highlightthickness=0, borderwidth=0,
                                     font=("Courier New", 11), activestyle="none")
        self._steps_lb.pack(fill="both", expand=True, padx=4, pady=4)

        # Reorder / remove buttons
        order = ctk.CTkFrame(steps, fg_color="transparent")
        order.grid(row=1, column=1, sticky="ns", padx=(0, 14), pady=(0, 8))
        for text, cmd in [("▲", self._step_up), ("▼", self._step_down), ("✕", self._remove_step)]:
            ctk.CTkButton(order, text=text, width=34, height=34, corner_radius=6,
                          fg_color="#1e1e3a", hover_color="#2a2a50",
                          command=cmd).pack(pady=3)

        # Add step row
        add_row = ctk.CTkFrame(steps, fg_color="transparent")
        add_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))
        add_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(add_row, text="Add step:", text_color="#888").grid(row=0, column=0, padx=(0, 8))
        self._point_var = ctk.StringVar()
        self._combo = ctk.CTkComboBox(add_row, variable=self._point_var, state="readonly",
                                       height=32, corner_radius=6)
        self._combo.grid(row=0, column=1, sticky="ew")
        ctk.CTkButton(add_row, text="Add →", width=72, height=32, corner_radius=6,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      command=self._add_step).grid(row=0, column=2, padx=(6, 0))
        ctk.CTkButton(add_row, text="↺", width=36, height=32, corner_radius=6,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      command=self._refresh_points).grid(row=0, column=3, padx=(4, 0))

        # Path preview
        self._preview_var = ctk.StringVar()
        ctk.CTkLabel(right, textvariable=self._preview_var,
                     font=ctk.CTkFont("Helvetica", 10), text_color="#555",
                     wraplength=600, anchor="w").grid(row=3, column=0, sticky="w")

        # Save button
        ctk.CTkButton(right, text="💾  Save Route", height=40,
                      fg_color=ACCENT, hover_color="#c73652",
                      font=ctk.CTkFont("Helvetica", 12, "bold"),
                      corner_radius=8, command=self._save_route).grid(
                          row=4, column=0, sticky="ew", pady=(10, 0))

        self._refresh_points()

    # ── Route list ────────────────────────────────────────────────────────────

    def _refresh_route_list(self):
        self._listbox.delete(0, tk.END)
        for name, data in navigator._load_routes().items():
            n = len(data.get("steps", []))
            self._listbox.insert(tk.END, f"  {name}  ({n} steps)")

    def _on_select(self, _=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        routes = navigator._load_routes()
        name = list(routes.keys())[sel[0]]
        self._selected_route = name
        data = routes[name]
        self._name_var.set(name)
        self._desc_var.set(data.get("description", ""))
        self._set_steps(data.get("steps", []))
        self._update_preview(data.get("steps", []))

    def _new_route(self):
        self._selected_route = None
        self._name_var.set("")
        self._desc_var.set("")
        self._steps_lb.delete(0, tk.END)
        self._preview_var.set("")

    def _delete_route(self):
        if not self._selected_route:
            return
        if messagebox.askyesno("Delete route", f"Delete  '{self._selected_route}' ?"):
            navigator.delete_route(self._selected_route)
            self.logs.log(f"Deleted route: {self._selected_route}", "warn")
            self._new_route()
            self._refresh_route_list()

    # ── Steps ─────────────────────────────────────────────────────────────────

    def _refresh_points(self):
        pts = list(navigator._load_points().keys())
        self._combo.configure(values=pts)
        if pts:
            self._point_var.set(pts[0])

    def _add_step(self):
        p = self._point_var.get()
        if not p:
            return
        i = self._steps_lb.size() + 1
        self._steps_lb.insert(tk.END, f"  {i}.  {p}")
        self._update_preview(self._get_steps())

    def _remove_step(self):
        sel = self._steps_lb.curselection()
        if sel:
            self._steps_lb.delete(sel[0])
            self._renumber()
            self._update_preview(self._get_steps())

    def _step_up(self):
        sel = self._steps_lb.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        s = self._get_steps()
        s[i-1], s[i] = s[i], s[i-1]
        self._set_steps(s)
        self._steps_lb.selection_set(i-1)

    def _step_down(self):
        sel = self._steps_lb.curselection()
        if not sel or sel[0] == self._steps_lb.size()-1:
            return
        i = sel[0]
        s = self._get_steps()
        s[i], s[i+1] = s[i+1], s[i]
        self._set_steps(s)
        self._steps_lb.selection_set(i+1)

    def _get_steps(self) -> list[str]:
        return [self._steps_lb.get(i).strip().split(". ", 1)[-1].strip()
                for i in range(self._steps_lb.size())]

    def _set_steps(self, steps: list[str]):
        self._steps_lb.delete(0, tk.END)
        for i, s in enumerate(steps, 1):
            self._steps_lb.insert(tk.END, f"  {i}.  {s}")

    def _renumber(self):
        self._set_steps(self._get_steps())

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save_route(self):
        name = self._name_var.get().strip().replace(" ", "_").lower()
        if not name:
            messagebox.showwarning("Missing name", "Give the route a name first.")
            return
        steps = self._get_steps()
        if not steps:
            messagebox.showwarning("No steps", "Add at least one step.")
            return
        navigator.save_route(name, steps, self._desc_var.get().strip())
        self._refresh_route_list()
        self.logs.log(f"Saved route: {name}  →  {' → '.join(steps)}", "success")

    def _update_preview(self, steps: list[str]):
        self._preview_var.set("Path:  " + "  →  ".join(steps) if steps else "")

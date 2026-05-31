"""Secret Shop tab."""

import customtkinter as ctk
import threading
from ui.widgets import CTkSpinbox
from config import cfg, save_cfg

ACCENT  = "#e94560"
SUCCESS = "#4ecca3"


class ShopTab:
    def __init__(self, parent, logs, status_var):
        self.parent     = parent
        self.logs       = logs
        self.status_var = status_var
        self._running   = False
        self._build()

    def _build(self):
        self.parent.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(self.parent, text="Secret Shop",
                     font=ctk.CTkFont("Helvetica", 16, "bold")).grid(
                         row=0, column=0, sticky="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(self.parent, text="Configure what to buy, then hit Run.",
                     font=ctk.CTkFont("Helvetica", 11), text_color="#555").grid(
                         row=1, column=0, sticky="w", padx=20, pady=(0, 14))

        # Settings card
        card = ctk.CTkFrame(self.parent, fg_color="#1a1a2e", corner_radius=10)
        card.grid(row=2, column=0, sticky="ew", padx=20)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(card, text="Settings",
                     font=ctk.CTkFont("Helvetica", 12, "bold")).grid(
                         row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 8))

        # Max refreshes
        ctk.CTkLabel(card, text="Max refreshes", text_color="#aaa").grid(
            row=1, column=0, sticky="w", padx=16, pady=6)
        self._refresh_limit = ctk.IntVar(value=cfg["secret_shop"]["refresh_limit"])
        CTkSpinbox(card, from_=1, to=999, variable=self._refresh_limit).grid(
            row=1, column=1, sticky="e", padx=16, pady=6)

        # Max cost
        ctk.CTkLabel(card, text="Max item cost  (skystones)", text_color="#aaa").grid(
            row=2, column=0, sticky="w", padx=16, pady=6)
        self._max_cost = ctk.IntVar(value=cfg["secret_shop"]["max_item_cost"])
        CTkSpinbox(card, from_=1, to=500, variable=self._max_cost).grid(
            row=2, column=1, sticky="e", padx=16, pady=6)

        # Toggles
        self._buy_bookmarks = ctk.BooleanVar(value=cfg["secret_shop"]["buy_bookmarks"])
        self._buy_mystic    = ctk.BooleanVar(value=cfg["secret_shop"]["buy_mystic_medals"])

        for i, (text, var) in enumerate([
            ("Buy Covenant Bookmarks", self._buy_bookmarks),
            ("Buy Mystic Medals",      self._buy_mystic),
        ], start=3):
            ctk.CTkCheckBox(card, text=text, variable=var,
                            fg_color=ACCENT, hover_color="#c73652",
                            checkmark_color="white").grid(
                                row=i, column=0, columnspan=2, sticky="w", padx=16, pady=4)

        # History recording toggle
        self._record_history = ctk.BooleanVar(
            value=cfg.get("history", {}).get("enabled", True))
        ctk.CTkCheckBox(card, text="Record roll history (screenshots)",
                        variable=self._record_history,
                        fg_color=ACCENT, hover_color="#c73652",
                        checkmark_color="white").grid(
                            row=5, column=0, columnspan=2, sticky="w", padx=16, pady=4)

        # Timing card
        tcard = ctk.CTkFrame(self.parent, fg_color="#1a1a2e", corner_radius=10)
        tcard.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 0))
        tcard.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(tcard, text="Timing",
                     font=ctk.CTkFont("Helvetica", 12, "bold")).grid(
                         row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 8))

        t = cfg.get("timing", {})

        def _row(r, label, attr, default, mn, mx, fmt=None):
            ctk.CTkLabel(tcard, text=label, text_color="#aaa").grid(
                row=r, column=0, sticky="w", padx=16, pady=4)
            var = ctk.DoubleVar(value=float(t.get(attr, default)))
            setattr(self, f"_{attr}", var)
            entry = ctk.CTkEntry(tcard, textvariable=var, width=80,
                                 height=28, corner_radius=6, justify="center")
            entry.grid(row=r, column=1, sticky="w", padx=16, pady=4)

        _row(1, "Click delay (s)",    "click_delay",    0.15, 0.05, 2.0)
        _row(2, "Nav delay (s)",      "navigation_delay", 0.6, 0.1, 5.0)
        _row(3, "Scroll amount",      "scroll_amount",  0.35, 0.1, 0.9)
        _row(4, "Scroll duration (s)","scroll_duration", 0.3, 0.1, 2.0)

        ctk.CTkButton(tcard, text="Save settings", width=120, height=28,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      corner_radius=6, command=self._save_settings).grid(
                          row=5, column=1, sticky="e", padx=16, pady=(8, 14))

        ctk.CTkButton(card, text="Save settings", width=120, height=28,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      corner_radius=6, command=self._save_settings).grid(
                          row=6, column=1, sticky="e", padx=16, pady=(8, 14))

        # Run button
        self._run_btn = ctk.CTkButton(self.parent,
                                       text="▶   Run Shop Rolling",
                                       height=48, corner_radius=10,
                                       fg_color=ACCENT, hover_color="#c73652",
                                       font=ctk.CTkFont("Helvetica", 14, "bold"),
                                       command=self._toggle)
        self._run_btn.grid(row=4, column=0, sticky="ew", padx=20, pady=20)

    def _save_settings(self):
        cfg["secret_shop"]["refresh_limit"]     = self._refresh_limit.get()
        cfg["secret_shop"]["max_item_cost"]     = self._max_cost.get()
        cfg["secret_shop"]["buy_bookmarks"]     = self._buy_bookmarks.get()
        cfg["secret_shop"]["buy_mystic_medals"] = self._buy_mystic.get()
        if "timing" not in cfg:
            cfg["timing"] = {}
        for attr in ("click_delay", "navigation_delay", "scroll_amount", "scroll_duration"):
            var = getattr(self, f"_{attr}", None)
            if var:
                cfg["timing"][attr] = round(var.get(), 3)
        cfg.setdefault("history", {})["enabled"] = self._record_history.get()
        save_cfg()
        self.logs.log("Settings saved", "success")

    def _toggle(self):
        if self._running:
            self._running = False
            self._run_btn.configure(text="▶   Run Shop Rolling", fg_color=ACCENT)
            self.status_var.set("Idle")
            self.logs.log("Shop rolling stopped", "warn")
        else:
            self._running = True
            self._run_btn.configure(text="■   Stop", fg_color="#333")
            self.status_var.set("Running: Secret Shop")
            threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        recorder = None
        try:
            from config import cfg
            from bot.window import find_window, capture_window
            from bot.tasks import secret_shop
            from bot.history import HistoryRecorder

            hist_cfg = cfg.get("history", {})
            recorder = HistoryRecorder(
                enabled=hist_cfg.get("enabled", True),
                jpeg_quality=hist_cfg.get("jpeg_quality", 85))

            hwnd = find_window("")
            self.logs.log("Starting shop rolling...", "info")
            secret_shop.run(hwnd, lambda: capture_window(hwnd),
                            should_run=lambda: self._running,
                            recorder=recorder)
            recorder.close("done" if self._running else "stopped")
            recorder = None
            self.logs.log("Shop rolling complete", "success")
        except Exception as e:
            self.logs.log(f"Error: {e}", "error")
            if recorder is not None:
                recorder.close("error")
        finally:
            self._running = False
            self.parent.after(0, lambda: self._run_btn.configure(
                text="▶   Run Shop Rolling", fg_color=ACCENT))
            self.parent.after(0, lambda: self.status_var.set("Idle"))

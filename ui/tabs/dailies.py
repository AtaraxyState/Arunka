"""Dailies tab."""

import customtkinter as ctk
import threading

ACCENT  = "#e94560"
SUCCESS = "#4ecca3"


class DailiesTab:
    def __init__(self, parent, logs, status_var):
        self.parent     = parent
        self.logs       = logs
        self.status_var = status_var
        self._running   = False
        self._build()

    def _build(self):
        self.parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.parent, text="Dailies",
                     font=ctk.CTkFont("Helvetica", 16, "bold")).grid(
                         row=0, column=0, sticky="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(self.parent, text="Select which daily tasks to automate.",
                     font=ctk.CTkFont("Helvetica", 11), text_color="#555").grid(
                         row=1, column=0, sticky="w", padx=20, pady=(0, 14))

        card = ctk.CTkFrame(self.parent, fg_color="#1a1a2e", corner_radius=10)
        card.grid(row=2, column=0, sticky="ew", padx=20)

        ctk.CTkLabel(card, text="Tasks",
                     font=ctk.CTkFont("Helvetica", 12, "bold")).pack(
                         anchor="w", padx=16, pady=(12, 8))

        self._do_missions  = ctk.BooleanVar(value=True)
        self._do_mailbox   = ctk.BooleanVar(value=True)
        self._do_rep       = ctk.BooleanVar(value=True)

        for text, var in [
            ("Claim daily mission rewards", self._do_missions),
            ("Claim mailbox",               self._do_mailbox),
            ("Claim reputation rewards",    self._do_rep),
        ]:
            ctk.CTkCheckBox(card, text=text, variable=var,
                            fg_color=ACCENT, hover_color="#c73652",
                            checkmark_color="white").pack(
                                anchor="w", padx=16, pady=4)

        ctk.CTkFrame(card, fg_color="transparent", height=12).pack()

        self._run_btn = ctk.CTkButton(self.parent,
                                       text="▶   Run Dailies",
                                       height=48, corner_radius=10,
                                       fg_color=ACCENT, hover_color="#c73652",
                                       font=ctk.CTkFont("Helvetica", 14, "bold"),
                                       command=self._toggle)
        self._run_btn.grid(row=3, column=0, sticky="ew", padx=20, pady=20)

    def _toggle(self):
        if self._running:
            self._running = False
            self._run_btn.configure(text="▶   Run Dailies", fg_color=ACCENT)
            self.status_var.set("Idle")
            self.logs.log("Dailies stopped", "warn")
        else:
            self._running = True
            self._run_btn.configure(text="■   Stop", fg_color="#333")
            self.status_var.set("Running: Dailies")
            threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            from config import cfg
            from bot.window import find_window, capture_window
            from bot.tasks import dailies
            hwnd = find_window("")
            selections = {
                "missions":   self._do_missions.get(),
                "mailbox":    self._do_mailbox.get(),
                "reputation": self._do_rep.get(),
            }
            self.logs.log("Starting dailies...", "info")
            dailies.run(hwnd, lambda: capture_window(hwnd),
                        selections=selections,
                        should_run=lambda: self._running)
            self.logs.log("Dailies complete", "success")
        except Exception as e:
            self.logs.log(f"Error: {e}", "error")
        finally:
            self._running = False
            self.parent.after(0, lambda: self._run_btn.configure(
                text="▶   Run Dailies", fg_color=ACCENT))
            self.parent.after(0, lambda: self.status_var.set("Idle"))

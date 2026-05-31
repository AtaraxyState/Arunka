"""
Arunka - Main UI entry point
Run: python run.py
"""

import customtkinter as ctk
from ui.tabs.settings import SettingsTab
from ui.tabs.calibration import CalibrationTab
from ui.tabs.routes import RoutesTab
from ui.tabs.shop import ShopTab
from ui.tabs.dailies import DailiesTab
from ui.tabs.history import HistoryTab
from ui.tabs.logs import LogsTab

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT  = "#e94560"
SUCCESS = "#4ecca3"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Arunka - Epic Seven Bot")
        self.geometry("1100x700")
        self.minsize(900, 580)
        self.resizable(True, True)
        self.configure(fg_color="#0f0f1a")

        self._build_header()
        self._build_tabs()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=0, height=52)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="⚔  ARUNKA",
                     font=ctk.CTkFont("Helvetica", 18, "bold"),
                     text_color=ACCENT).pack(side="left", padx=20)

        self._status_var = ctk.StringVar(value="Idle")
        ctk.CTkLabel(header, textvariable=self._status_var,
                     font=ctk.CTkFont("Helvetica", 11),
                     text_color="#666").pack(side="right", padx=20)

    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(self, fg_color="#13131f",
                                      segmented_button_fg_color="#1a1a2e",
                                      segmented_button_selected_color=ACCENT,
                                      segmented_button_selected_hover_color="#c73652",
                                      segmented_button_unselected_color="#1a1a2e",
                                      segmented_button_unselected_hover_color="#252540",
                                      text_color="#aaa",
                                      text_color_disabled="#555")
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        for name in ("Settings", "Calibration", "Routes", "Secret Shop",
                     "Dailies", "History", "Logs"):
            self.tabview.add(name)

        self.logs_tab = LogsTab(self.tabview.tab("Logs"))

        # These manage their own layout - pass the tab frame directly
        CalibrationTab(self.tabview.tab("Calibration"), self.logs_tab)
        RoutesTab(self.tabview.tab("Routes"), self.logs_tab)
        HistoryTab(self.tabview.tab("History"), self.logs_tab)

        # Settings / Shop / Dailies get a scrollable wrapper so they work on small screens
        for tab_name, cls, extra in [
            ("Settings",    SettingsTab, (self._status_var,)),
            ("Secret Shop", ShopTab,     (self._status_var,)),
            ("Dailies",     DailiesTab,  (self._status_var,)),
        ]:
            scroll = ctk.CTkScrollableFrame(
                self.tabview.tab(tab_name),
                fg_color="transparent",
                scrollbar_button_color="#2a2a50",
                scrollbar_button_hover_color="#3a3a70",
            )
            scroll.pack(fill="both", expand=True)
            scroll.grid_columnconfigure(0, weight=1)
            cls(scroll, self.logs_tab, *extra)


def main():
    app = App()
    app.mainloop()

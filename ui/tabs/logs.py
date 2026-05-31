import customtkinter as ctk
import datetime

ACCENT  = "#e94560"
SUCCESS = "#4ecca3"
WARNING = "#f0a500"


class LogsTab:
    def __init__(self, parent):
        self.frame = parent
        self._build()

    def _build(self):
        self.textbox = ctk.CTkTextbox(
            self.frame,
            font=ctk.CTkFont("Courier New", 11),
            fg_color="#0d0d1a",
            text_color="#ccc",
            wrap="word",
            state="disabled",
            corner_radius=8,
        )
        self.textbox.pack(fill="both", expand=True, padx=8, pady=8)

        # Color tags via underlying tk Text widget
        t = self.textbox._textbox
        t.tag_configure("dim",     foreground="#555")
        t.tag_configure("info",    foreground="#ccc")
        t.tag_configure("success", foreground=SUCCESS)
        t.tag_configure("warn",    foreground=WARNING)
        t.tag_configure("error",   foreground=ACCENT)

    def log(self, message: str, level: str = "info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.textbox.configure(state="normal")
        t = self.textbox._textbox
        t.insert("end", f"[{ts}] ", "dim")
        t.insert("end", f"{message}\n", level)
        self.textbox.configure(state="disabled")
        self.textbox._textbox.see("end")

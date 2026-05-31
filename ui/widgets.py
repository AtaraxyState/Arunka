"""Reusable custom widgets."""

import customtkinter as ctk

ACCENT  = "#e94560"
SUCCESS = "#4ecca3"


class CTkSpinbox(ctk.CTkFrame):
    """Minimal integer spinbox: [−] [value] [+]"""

    def __init__(self, master, from_=0, to=999, variable: ctk.IntVar = None, width=110, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._from = from_
        self._to   = to
        self._var  = variable or ctk.IntVar(value=from_)

        ctk.CTkButton(self, text="−", width=28, height=28, corner_radius=6,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      command=self._decrement).pack(side="left")

        self._entry = ctk.CTkEntry(self, width=width - 56, height=28,
                                   textvariable=self._var,
                                   justify="center", corner_radius=6,
                                   fg_color="#1e1e3a", border_width=0)
        self._entry.pack(side="left", padx=2)

        ctk.CTkButton(self, text="+", width=28, height=28, corner_radius=6,
                      fg_color="#1e1e3a", hover_color="#2a2a50",
                      command=self._increment).pack(side="left")

    def _increment(self):
        v = min(self._var.get() + 1, self._to)
        self._var.set(v)

    def _decrement(self):
        v = max(self._var.get() - 1, self._from)
        self._var.set(v)

    def get(self) -> int:
        return self._var.get()


class SectionLabel(ctk.CTkLabel):
    def __init__(self, master, text, **kwargs):
        super().__init__(master, text=text,
                         font=ctk.CTkFont("Helvetica", 13, "bold"),
                         text_color="#eee", **kwargs)


class DimLabel(ctk.CTkLabel):
    def __init__(self, master, text, **kwargs):
        super().__init__(master, text=text,
                         font=ctk.CTkFont("Helvetica", 10),
                         text_color="#666", **kwargs)

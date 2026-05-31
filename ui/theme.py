import tkinter as tk
from tkinter import ttk

BG       = "#16213e"
BG_LIGHT = "#1a1a2e"
ACCENT   = "#e94560"
FG       = "#eaeaea"
FG_DIM   = "#888888"
SUCCESS  = "#4ecca3"
BTN_BG   = "#0f3460"


def apply_theme(root: tk.Tk):
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("TNotebook",        background=BG,       borderwidth=0)
    style.configure("TNotebook.Tab",    background=BG_LIGHT, foreground=FG_DIM,
                    padding=[12, 6],    font=("Helvetica", 10))
    style.map("TNotebook.Tab",
              background=[("selected", BG)],
              foreground=[("selected", ACCENT)])

    style.configure("TFrame",           background=BG)
    style.configure("TLabel",           background=BG,       foreground=FG,
                    font=("Helvetica", 10))
    style.configure("Dim.TLabel",       background=BG,       foreground=FG_DIM,
                    font=("Helvetica", 9))
    style.configure("TCheckbutton",     background=BG,       foreground=FG,
                    font=("Helvetica", 10))
    style.configure("TSpinbox",         fieldbackground=BG_LIGHT, foreground=FG)
    style.configure("TScrollbar",       background=BG_LIGHT, troughcolor=BG)

    style.configure("Action.TButton",
                    background=ACCENT,  foreground="white",
                    font=("Helvetica", 11, "bold"),
                    padding=[16, 8],    relief="flat")
    style.map("Action.TButton",
              background=[("active", "#c73652"), ("disabled", "#555")])

    style.configure("Small.TButton",
                    background=BTN_BG,  foreground=FG,
                    font=("Helvetica", 9), padding=[8, 4], relief="flat")
    style.map("Small.TButton",
              background=[("active", "#1a4a8a")])

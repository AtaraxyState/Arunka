"""
Arunka — Entry point.

Creates two pywebview windows:
  1. Main window  — full app UI (index.html)
  2. HUD window   — always-on-top Seal HUD (hud.html), frameless, draggable

Run:   python run.py
Debug: python run.py --debug
Build: pyinstaller arunka.spec
"""

import sys
import os
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE = Path(sys._MEIPASS)
else:
    BASE = Path(__file__).parent

UI_DIR   = BASE / "ui"
HTML     = UI_DIR / "index.html"
HUD_HTML = UI_DIR / "hud.html"

# ── API ───────────────────────────────────────────────────────────────────────
from api import ArunkaAPI
api = ArunkaAPI()

# ── Windows ───────────────────────────────────────────────────────────────────
import webview

# Main app window
window = webview.create_window(
    title     = "Arunka — Epic Seven Bot",
    url       = str(HTML),
    js_api    = api,
    width     = 1280,
    height    = 800,
    min_size  = (960, 640),
    resizable = True,
)

# HUD window — always on top, frameless, small
HUD_X, HUD_Y = 40, 40   # initial position (top-left corner)
hud = webview.create_window(
    title       = "Arunka HUD",
    url         = str(HUD_HTML),
    js_api      = api,
    width       = 278,
    height      = 220,
    x           = HUD_X,
    y           = HUD_Y,
    resizable   = False,
    on_top      = True,
    frameless   = True,
    transparent = False,        # True can be unstable on some Windows setups
    background_color = "#0a0e14",
)

def on_main_loaded():
    api.set_window(window)

def on_hud_loaded():
    api.set_hud_window(hud, HUD_X, HUD_Y)
    # Default mode is Status Bar — hide HUD until user switches
    from config import cfg
    if cfg.get("ui", {}).get("hud_mode", "bar") != "seal":
        hud.hide()

window.events.loaded += on_main_loaded
hud.events.loaded    += on_hud_loaded

# ── Start ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    debug = "--debug" in sys.argv or os.environ.get("ARUNKA_DEBUG") == "1"
    webview.start(debug=debug)

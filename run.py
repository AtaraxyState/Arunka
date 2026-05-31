"""
Arunka — Entry point.

Launches a native pywebview window that loads the HTML/CSS/JS UI.
The Python API (api.ArunkaAPI) is bound as window.pywebview.api in JS.

Run:
    python run.py

Build:
    pyinstaller arunka.spec
"""

import sys
import os
from pathlib import Path

# ── Resolve paths ─────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    # PyInstaller: files extracted to sys._MEIPASS
    BASE = Path(sys._MEIPASS)
else:
    BASE = Path(__file__).parent

UI_DIR  = BASE / "ui"
HTML    = UI_DIR / "index.html"

# ── API ───────────────────────────────────────────────────────────────────────
from api import ArunkaAPI
api = ArunkaAPI()

# ── Window ────────────────────────────────────────────────────────────────────
import webview

window = webview.create_window(
    title     = "Arunka — Epic Seven Bot",
    url       = str(HTML),
    js_api    = api,
    width     = 1280,
    height    = 800,
    min_size  = (960, 640),
    resizable = True,
    # Keep native frame; pywebview handles the chrome
)

def on_loaded():
    """Called after the DOM is ready — give the API a reference to the window."""
    api.set_window(window)

window.events.loaded += on_loaded

# ── Start (blocks until window is closed) ────────────────────────────────────
if __name__ == "__main__":
    # debug=True enables DevTools on right-click → Inspect (remove for release)
    debug = "--debug" in sys.argv or os.environ.get("ARUNKA_DEBUG") == "1"
    webview.start(debug=debug)

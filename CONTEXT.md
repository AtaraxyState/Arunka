# Arunka — Project Context

> Read this file at the start of any new conversation to restore full context.
> Project folder: `C:\Users\timot\Documents\Claude\Projects\Arunka`
> GitHub: https://github.com/AtaraxyState/Arunka

---

## What this is

Arunka is a desktop bot for **Epic Seven** (mobile RPG by Smilegate).
It automates Secret Shop rolling and Daily missions.
It runs as a Python desktop app using **pywebview** (native WebView2 window) that renders
a custom HTML/CSS/JS UI and controls a **BlueStacks Android emulator** via ADB.

---

## Architecture

```
run.py                      ← entry point (python run.py)
api/
  __init__.py               ← ArunkaAPI class — all JS→Python methods (pywebview bridge)
ui/
  index.html                ← full app UI (HTML/CSS/JS, moto-tech / sakura theme)
  arunka-tech.css           ← instrument-cluster design system
  arunka-app.css            ← Windshield-C shell (ambient art, glass panels, nav)
  assets/
    arunka.png              ← character art (transparent bg preferred)
bot/
  adb.py                    ← ADB connection (adbutils, localhost:5555)
  window.py                 ← screencap via ADB (3 fallback methods)
  input.py                  ← adb shell input tap / swipe (fully headless)
  vision.py                 ← multi-scale OpenCV template matching
  navigator.py              ← nav points + named routes, follow_route()
  launcher.py               ← start BlueStacks, wait for ADB
  tasks/
    secret_shop.py          ← scroll list, buy items, refresh loop
    dailies.py              ← claim missions/mailbox/reputation
  history.py                ← run/roll recording, image storage, index
config/
  __init__.py               ← loads settings.yaml, exposes cfg + save_cfg()
  settings.yaml             ← all user config (ADB, task settings, timing)
assets/
  templates/                ← PNG template images for vision matching
  nav_points.json           ← recorded (x,y) click positions
  nav_routes.json           ← named sequences of nav point keys
```

### Old UI (obsolete, not used)
`ui/app.py`, `ui/tabs/`, `ui/widgets.py`, `ui/theme.py` — replaced by pywebview.
Kept harmless; can be deleted.

---

## Key technical decisions

| Decision | Why |
|---|---|
| pywebview instead of CustomTkinter | Full HTML/CSS/JS UI — no visual compromises, native WebView2 (Edge) on Windows |
| ADB + BlueStacks instead of PC client | PostMessage/Win32 input ignored by E7; ADB `input tap` is fully headless |
| Multi-scale template matching | Templates captured once, work at any window/emulator resolution |
| JS→Python via `window.pywebview.api.*` | Each public method on ArunkaAPI becomes a Promise-returning JS call |
| Python→JS via `window.evaluate_js()` | Log lines, progress updates, and state changes pushed from bot threads |
| Routes system | Named sequences of nav points so tasks navigate menus without hard-coded clicks |
| `save_cfg()` helper | Config persisted to `%APPDATA%\Arunka\settings.yaml` when frozen as .exe |

---

## UI → Python bridge

### JS calls Python (returns Promise):
```js
window.pywebview.api.connect_adb()
window.pywebview.api.start_shop(config)
window.pywebview.api.pause_shop()
window.pywebview.api.stop_shop()
window.pywebview.api.get_runs()
window.pywebview.api.get_run_detail(run_id)
window.pywebview.api.get_roll_image(run_id, filename)   // filename = "roll_0001_top.jpg"
window.pywebview.api.get_routes()
window.pywebview.api.save_route(name, description, steps)
window.pywebview.api.start_dailies(config)
// ... see api/__init__.py for full list
```

### Python pushes to JS:
```js
window.arunka.log(ts, level, tag, msg)          // log line → terminal tab
window.arunka.shopProgress(data)                // {refresh, found, elapsed, max, sky}
window.arunka.shopState(state)                  // "running"|"paused"|"done"|"error"
window.arunka.dailiesState(state)
window.arunka.adbStatus(connected, serial)
window.arunka.templateStatus(statusDict)
```

---

## Current state

### Working
- pywebview window launches, loads the full moto-tech/sakura HTML UI
- ADB connection (BlueStacks emulator-5554)
- Live log forwarding: loguru → terminal tab in real time
- Secret shop: run/pause/stop, tachometer updates every second, found counter
- Elapsed timer pushes to Seal HUD + Status Bar + cluster every second
- Skystone reading: optional pytesseract OCR on game screenshot (10s interval)
- Dailies: run/stop
- History: run list + roll image viewer (base64 JPEG via pywebview API)
- Routes: build/save/delete named nav sequences
- Calibration: template status dots, screenshot refresh
- Theme (dark / warm sakura white) + HUD mode (Seal HUD / Status Bar) in Settings
- Git repo: https://github.com/AtaraxyState/Arunka

### Buy flow fix (secret_shop.py)
`_buy_items` re-captures a fresh screen before each buy attempt.
If the purchased item's Buy button is grayed and the next scan doesn't find it,
the loop ends cleanly. Missing confirm dialog = immediate return (no wrong purchases).

### Skystone OCR (optional)
Install Tesseract for Windows + `pip install pytesseract` to enable live skystone
count in the HUD. Without it, skystones shows `—`.

### Config (settings.yaml)
```yaml
adb:
  adb_path: C:\Program Files\BlueStacks_nxt\HD-Adb.exe
  emulator_exe: C:/Program Files/BlueStacks_nxt/HD-Player.exe
  host: localhost
  port: 5555
secret_shop:
  refresh_limit: 100
  buy_bookmarks: true
  buy_mystic_medals: true
  item_threshold: 0.88
timing:
  click_delay: 0.15
  navigation_delay: 0.6
  scroll_amount: 0.35
  scroll_duration: 0.3
```

### Templates needed (assets/templates/)
**Secret Shop:** `shop_refresh_btn`, `shop_confirm_refresh_btn`, `shop_buy_btn`,
`shop_confirm_buy_btn`, `item_covenant_bookmark`, `item_mystic_medal`

**Dailies:** `daily_missions_tab`, `daily_claim_all_btn`, `mailbox_tab`,
`mailbox_claim_all_btn`, `reputation_tab`, `reputation_claim_btn`

### Known issues / pending work
- Calibration drag-to-capture overlay not yet implemented in the web UI
  (clicking Capture logs a message but doesn't open a region selector)
- Skystone reading requires Tesseract install; fallback shows `—`
- White/sakura mode with black-background Arunka art uses `mix-blend-mode: multiply`
  (slightly different look than dark mode `screen` blend)

---

## How to run

```bash
# Install deps (first time)
setup.bat

# Run from source
python run.py

# Debug (DevTools on right-click → Inspect)
python run.py --debug

# Build .exe
pyinstaller arunka.spec
```

## How to start a new conversation

Tell the new agent:
> "Read CONTEXT.md in C:\Users\timot\Documents\Claude\Projects\Arunka and continue working on Arunka."

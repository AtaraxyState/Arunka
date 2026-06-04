"""
Arunka — Python API exposed to the pywebview frontend.

Every public method on ArunkaAPI becomes callable from JS as:
    window.pywebview.api.method_name(args)   → returns a Promise

Python → JS push is done via:
    self._js('window.arunka.callback(data)')

Threading model:
    - pywebview calls API methods on background threads (one per call)
    - task loops (_run_shop, _run_dailies) run on dedicated daemon threads
    - _js() is thread-safe (pywebview buffers evaluate_js internally)
"""

import threading
import json
import base64
import time
from pathlib import Path
from loguru import logger
from config import cfg, save_cfg


class ArunkaAPI:
    def __init__(self):
        self._window      = None
        self._hud_window  = None   # separate always-on-top HUD window
        self._hud_x       = 40     # tracked position for move_hud_by
        self._hud_y       = 40
        self._log_sink_id = None

        # shop state
        self._shop_thread  = None
        self._shop_stop    = threading.Event()
        self._shop_pause   = threading.Event()
        self._shop_resume  = threading.Event()  # set for one tick when unpaused
        self._shop_refresh  = 0
        self._shop_found    = 0
        self._shop_mystic   = 0
        self._shop_covenant = 0
        self._shop_t0          = 0.0
        self._shop_paused_at   = 0.0  # time.time() when last paused, 0 = not paused
        self._shop_pause_total = 0.0  # cumulative seconds spent paused
        self._shop_running = False   # True while task thread is active
        self._shop_sky     = None    # last known skystone count

        # dailies state
        self._dailies_thread = None
        self._dailies_stop   = threading.Event()

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    def set_window(self, window):
        """Called after pywebview creates the main window."""
        self._window = window
        self._log_sink_id = logger.add(
            self._loguru_sink,
            format="{time:HH:mm:ss} {level} {name} {message}",
            level="DEBUG",
        )

    def set_hud_window(self, window, x: int = 40, y: int = 40):
        """Called after the HUD window loads."""
        self._hud_window = window
        self._hud_x = x
        self._hud_y = y

    def _js(self, code: str):
        """Push JS to both the main window and the HUD window."""
        for w in (self._window, self._hud_window):
            if w:
                try:
                    w.evaluate_js(code)
                except Exception:
                    pass

    # ── HUD window controls ───────────────────────────────────────────────────

    def move_hud_by(self, dx: int, dy: int):
        """Called from HUD drag handler — moves the OS window by a delta."""
        if self._hud_window:
            self._hud_x += int(dx)
            self._hud_y += int(dy)
            self._hud_window.move(self._hud_x, self._hud_y)

    def resize_hud(self, width: int, height: int):
        """Resize HUD window (used by collapse/expand)."""
        if self._hud_window:
            self._hud_window.resize(int(width), int(height))

    def set_hud_visible(self, visible: bool):
        """Show or hide the floating HUD window (toggled from Settings)."""
        if self._hud_window:
            if visible:
                self._hud_window.show()
            else:
                self._hud_window.hide()

    def _loguru_sink(self, message):
        # loguru passes a Message object (string subclass); the dict lives at .record
        record = message.record
        ts    = record["time"].strftime("%H:%M:%S")
        level = record["level"].name.lower()
        lv_map = {"success": "ok", "warning": "warn", "error": "err",
                  "critical": "err", "debug": "info"}
        lv = lv_map.get(level, level)
        name = record["name"].split(".")[-1] if record["name"] else "bot"
        tag_map = {"secret_shop": "shop", "dailies": "dailies",
                   "navigator": "nav", "vision": "vision",
                   "adb": "adb", "window": "window", "input": "input"}
        tag = tag_map.get(name, name)
        msg  = record["message"]

        # Detect successful purchases and update per-item counters
        if msg.startswith("Bought:") and self._shop_running:
            self._shop_found += 1
            if "mystic" in msg:
                self._shop_mystic += 1
            elif "covenant" in msg:
                self._shop_covenant += 1
            self._push_shop_progress()

        code = (
            f"window.arunka&&window.arunka.log("
            f"{json.dumps(ts)},{json.dumps(lv)},"
            f"{json.dumps(tag)},{json.dumps(msg)})"
        )
        self._js(code)

    # ─────────────────────────────────────────────────────────────────────────
    # Settings
    # ─────────────────────────────────────────────────────────────────────────

    def get_settings(self):
        return dict(cfg)

    def save_settings(self, data: dict):
        for section, values in data.items():
            if isinstance(values, dict):
                cfg.setdefault(section, {}).update(values)
            else:
                cfg[section] = values
        save_cfg()
        logger.success("Settings saved")
        return {"ok": True}

    def connect_adb(self):
        from bot import adb
        try:
            device = adb.connect()
            serial = device.serial
            logger.success(f"ADB connected · {serial}")
            return {"ok": True, "serial": serial}
        except Exception as e:
            logger.error(f"ADB connect failed: {e}")
            return {"ok": False, "error": str(e)}

    def launch_bluestacks(self):
        from bot import launcher
        try:
            launcher.start_bluestacks()
            return {"ok": True}
        except Exception as e:
            logger.error(f"Launch BlueStacks failed: {e}")
            return {"ok": False, "error": str(e)}

    def get_adb_status(self):
        from bot import adb
        try:
            device = adb.get_device()
            if device:
                return {"connected": True, "serial": device.serial}
        except Exception:
            pass
        return {"connected": False, "serial": None}

    # ─────────────────────────────────────────────────────────────────────────
    # Calibration
    # ─────────────────────────────────────────────────────────────────────────

    def get_template_status(self):
        """Return dict of template_name → bool (file exists)."""
        tdir = Path("assets/templates")
        templates = [
            "shop_refresh_btn", "shop_confirm_refresh_btn",
            "shop_buy_btn", "shop_confirm_buy_btn",
            "item_covenant_bookmark", "item_mystic_medal",
            "daily_missions_tab", "daily_claim_all_btn",
            "mailbox_tab", "mailbox_claim_all_btn",
            "reputation_tab", "reputation_claim_btn",
        ]
        nav_keys = [
            "nav_lobby", "nav_shop_tab", "nav_secret_shop",
            "nav_daily_tab", "nav_mailbox", "nav_reputation",
        ]

        nav_path = Path("assets/nav_points.json")
        nav_data = {}
        if nav_path.exists():
            with open(nav_path) as f:
                nav_data = json.load(f)

        status = {t: (tdir / f"{t}.png").exists() for t in templates}
        status.update({k: k in nav_data for k in nav_keys})
        return status

    def get_screenshot(self):
        """Capture a live screenshot from the device, return base64 JPEG."""
        import cv2
        try:
            from bot.window import find_window, capture_window
            hwnd = find_window("")
            img  = capture_window(hwnd)
            _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return {"ok": True, "image": base64.b64encode(buf).decode()}
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"ok": False, "error": str(e)}

    # ─────────────────────────────────────────────────────────────────────────
    # Routes
    # ─────────────────────────────────────────────────────────────────────────

    def get_routes(self):
        from bot import navigator
        routes = navigator._load_routes()
        points = navigator._load_points()
        return {"routes": routes, "nav_points": list(points.keys())}

    def save_route(self, name: str, description: str, steps: list):
        from bot import navigator
        navigator.save_route(name, steps, description)
        logger.success(f"Route '{name}' saved ({len(steps)} steps)")
        return {"ok": True}

    def delete_route(self, name: str):
        from bot import navigator
        navigator.delete_route(name)
        logger.info(f"Route '{name}' deleted")
        return {"ok": True}

    # ─────────────────────────────────────────────────────────────────────────
    # Secret Shop
    # ─────────────────────────────────────────────────────────────────────────

    def start_shop(self, config: dict = None):
        if self._shop_thread and self._shop_thread.is_alive():
            # Already running → toggle pause
            return self.pause_shop()

        # Apply any config overrides from the UI
        if config:
            ss = cfg.setdefault("secret_shop", {})
            for k, v in config.items():
                if k in ss:
                    ss[k] = v
            t = cfg.setdefault("timing", {})
            for k in ("click_delay", "navigation_delay", "scroll_amount", "scroll_duration"):
                if k in config:
                    t[k] = config[k]

        self._shop_stop.clear()
        self._shop_pause.clear()
        self._shop_refresh     = 0
        self._shop_found       = 0
        self._shop_mystic      = 0
        self._shop_covenant    = 0
        self._shop_t0          = time.time()
        self._shop_paused_at   = 0.0
        self._shop_pause_total = 0.0

        self._shop_thread = threading.Thread(target=self._run_shop, daemon=True)
        self._shop_thread.start()
        return {"ok": True, "state": "running"}

    def pause_shop(self):
        if self._shop_pause.is_set():
            # Resuming — accumulate the time spent paused
            if self._shop_paused_at > 0:
                self._shop_pause_total += time.time() - self._shop_paused_at
                self._shop_paused_at = 0.0
            self._shop_resume.set()
            self._shop_pause.clear()
            self._js('window.arunka&&window.arunka.shopState("running")')
            return {"state": "running"}
        else:
            self._shop_paused_at = time.time()
            self._shop_resume.clear()
            self._shop_pause.set()
            self._js('window.arunka&&window.arunka.shopState("paused")')
            return {"state": "paused"}

    def stop_shop(self):
        self._shop_stop.set()
        self._shop_pause.clear()
        return {"ok": True}

    def get_shop_state(self):
        running = self._shop_thread and self._shop_thread.is_alive()
        return {
            "running":  running,
            "paused":   self._shop_pause.is_set(),
            "refresh":  self._shop_refresh,
            "found":    self._shop_found,
            "elapsed":  int(time.time() - self._shop_t0) if running else 0,
        }

    def _run_shop(self):
        from bot.window import find_window, capture_window
        from bot.tasks  import secret_shop
        from bot.history import HistoryRecorder
        import time as _time

        recorder  = None
        self._shop_running = True

        def should_run():
            while self._shop_pause.is_set() and not self._shop_stop.is_set():
                _time.sleep(0.2)
            return not self._shop_stop.is_set()

        # Background timer: push elapsed every second (sky is now event-based)
        def _timer():
            while self._shop_running and not self._shop_stop.is_set():
                self._push_shop_progress()
                _time.sleep(1.0)

        timer = threading.Thread(target=_timer, daemon=True)
        timer.start()

        try:
            hist_cfg = cfg.get("history", {})
            recorder = HistoryRecorder(
                enabled=hist_cfg.get("enabled", True),
                jpeg_quality=hist_cfg.get("jpeg_quality", 85),
            )

            # Patch start_roll to track refresh counter
            _orig_start_roll = recorder.start_roll
            api_ref = self
            def _counted_start_roll(roll_n):
                api_ref._shop_refresh = roll_n
                return _orig_start_roll(roll_n)
            recorder.start_roll = _counted_start_roll

            def sky_fn():
                """Full OCR read — used at start and on resume from pause."""
                try:
                    sky = self._read_skystone(capture_window(find_window("")))
                    if sky is not None:
                        self._shop_sky = sky
                        self._push_shop_progress()
                except Exception:
                    pass

            def sky_decrement_fn():
                """Fast path — subtract 3 per refresh without OCR."""
                if self._shop_sky is not None:
                    self._shop_sky -= 3
                    self._push_shop_progress()

            def restart_fn():
                """Return True (once) when the user just resumed from pause."""
                if self._shop_resume.is_set():
                    self._shop_resume.clear()
                    sky_fn()   # re-read after pause in case skystones changed
                    return True
                return False

            self._js('window.arunka&&window.arunka.shopState("running")')
            hwnd = find_window("")
            secret_shop.run(
                hwnd,
                lambda: capture_window(hwnd),
                should_run=should_run,
                recorder=recorder,
                step_fn=self._push_shop_step,
                restart_fn=restart_fn,
                sky_fn=sky_fn,
                sky_decrement_fn=sky_decrement_fn,
            )

            recorder.close(
                "done" if not self._shop_stop.is_set() else "stopped",
                elapsed_seconds=self._active_elapsed(),
            )
            recorder = None
            self._js('window.arunka&&window.arunka.shopState("done")')

        except Exception as e:
            logger.error(f"Shop task error: {e}")
            if recorder:
                try:
                    recorder.close("error", elapsed_seconds=self._active_elapsed())
                except Exception:
                    pass
            self._js('window.arunka&&window.arunka.shopState("error")')
        finally:
            self._shop_running = False

    def _read_skystone(self, screen) -> "int | None":
        """OCR the skystone count from the game top bar."""
        try:
            import pytesseract
            import cv2
            import re
            # Point to default Tesseract install location on Windows
            pytesseract.pytesseract.tesseract_cmd = (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )
            h, w = screen.shape[:2]

            # Skystone number: ~67–80 % of width, top ~7 % of height
            roi = screen[0:int(h * 0.07), int(w * 0.67):int(w * 0.80)]

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            # Scale up 3× — improves Tesseract accuracy on small game text
            large = cv2.resize(gray, None, fx=3, fy=3,
                               interpolation=cv2.INTER_CUBIC)

            # White text on dark background → invert so text is black on white
            inv = cv2.bitwise_not(large)
            _, thresh = cv2.threshold(inv, 50, 255, cv2.THRESH_BINARY)

            # PSM 6 = uniform block; digits + comma only
            text = pytesseract.image_to_string(
                thresh, config="--psm 6 -c tessedit_char_whitelist=0123456789,"
            )

            nums = [int(n.replace(",", ""))
                    for n in re.findall(r"\d[\d,]+", text)]
            # Skystones are 3–6 digits; gold is 7–10
            candidates = [n for n in nums if 100 <= n <= 999_999]
            return candidates[0] if candidates else None
        except Exception:
            return None

    def _push_shop_step(self, step: str):
        """Push the current roll phase to the UI gauge."""
        self._js(f'window.arunka&&window.arunka.shopStep({json.dumps(step)})')

    @staticmethod
    def _fmt_duration(seconds: int) -> str:
        """0:SS  /  M:SS  /  H:MM:SS depending on magnitude."""
        s = max(0, int(seconds))
        if s < 3600:
            m, s = divmod(s, 60)
            return f"{m}:{s:02d}"
        h, rem = divmod(s, 3600)
        m, s   = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}"

    def _active_elapsed(self) -> int:
        """Seconds elapsed since shop start, excluding time spent paused."""
        paused = self._shop_pause_total
        if self._shop_paused_at > 0:
            paused += time.time() - self._shop_paused_at
        return max(0, int(time.time() - self._shop_t0 - paused))

    def _push_shop_progress(self):
        elapsed_sec = self._active_elapsed()
        elapsed_str = self._fmt_duration(elapsed_sec)

        # ETA: extrapolate from time-per-refresh × refreshes remaining
        refresh = self._shop_refresh
        max_ref = cfg.get("secret_shop", {}).get("refresh_limit", 100)
        if refresh > 0 and elapsed_sec > 0:
            eta_sec = int(elapsed_sec / refresh * max(0, max_ref - refresh))
            eta_str = self._fmt_duration(eta_sec)
        else:
            eta_str = None

        data = json.dumps({
            "refresh":  refresh,
            "found":    self._shop_found,
            "mystic":   self._shop_mystic,
            "covenant": self._shop_covenant,
            "elapsed":  elapsed_str,
            "eta":      eta_str,
            "max":      max_ref,
            "sky":      self._shop_sky,
        })
        self._js(f'window.arunka&&window.arunka.shopProgress({data})')

    # ─────────────────────────────────────────────────────────────────────────
    # Dailies
    # ─────────────────────────────────────────────────────────────────────────

    def start_dailies(self, config: dict = None):
        if self._dailies_thread and self._dailies_thread.is_alive():
            return {"ok": False, "error": "Already running"}
        self._dailies_stop.clear()
        self._dailies_thread = threading.Thread(
            target=self._run_dailies, args=(config or {},), daemon=True
        )
        self._dailies_thread.start()
        return {"ok": True}

    def stop_dailies(self):
        self._dailies_stop.set()
        return {"ok": True}

    def _run_dailies(self, selections: dict):
        from bot.window import find_window, capture_window
        from bot.tasks  import dailies
        try:
            self._js('window.arunka&&window.arunka.dailiesState("running")')
            hwnd = find_window("")
            dailies.run(
                hwnd,
                lambda: capture_window(hwnd),
                selections=selections,
                should_run=lambda: not self._dailies_stop.is_set(),
            )
            self._js('window.arunka&&window.arunka.dailiesState("done")')
        except Exception as e:
            logger.error(f"Dailies task error: {e}")
            self._js('window.arunka&&window.arunka.dailiesState("error")')

    # ─────────────────────────────────────────────────────────────────────────
    # History
    # ─────────────────────────────────────────────────────────────────────────
    # History
    # ─────────────────────────────────────────────────────────────────────────

    def get_runs(self):
        from bot.history import list_runs, history_size_bytes, human_size
        try:
            runs  = list_runs()
            total = human_size(history_size_bytes())
            return {"runs": runs, "total_size": total}
        except Exception as e:
            return {"runs": [], "total_size": "0 B", "error": str(e)}

    def get_run_detail(self, run_id: str):
        from bot.history import load_run
        run = load_run(run_id)
        return run or {}

    def get_roll_image(self, run_id: str, filename: str):
        """Return base64-encoded JPEG. filename = e.g. \'roll_0001_top.jpg\'."""
        from bot.history import roll_image_path
        if not filename:
            return None
        p = roll_image_path(run_id, filename)
        if not p or not p.exists():
            return None
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def delete_run(self, run_id: str):
        from bot.history import delete_run
        ok = delete_run(run_id)
        return {"ok": ok}

    def clear_history(self):
        from bot.history import clear_all
        ok = clear_all()
        return {"ok": ok}

    def export_run_csv(self, run_id: str):
        from bot.history import export_csv
        p = export_csv(run_id)
        if p and p.exists():
            return {"ok": True, "path": str(p)}
        return {"ok": False}

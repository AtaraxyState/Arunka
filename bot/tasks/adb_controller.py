"""
ADBController adapter — wraps Arunka's existing bot.input / bot.window so
that secret_shop_bot.SecretShopBot can call self.adb.tap / swipe / screenshot
without knowing anything about our internals.
"""

import cv2
import time
from pathlib import Path
from loguru import logger as _logger


class ADBController:
    def __init__(self, hwnd: int, screen_fn):
        self._hwnd = hwnd
        self._screen_fn = screen_fn

    # ── screen size ───────────────────────────────────────────────────────────
    def get_screen_size(self) -> tuple[int, int]:
        screen = self._screen_fn()
        h, w = screen.shape[:2]
        return w, h

    # ── screenshot ────────────────────────────────────────────────────────────
    def screenshot(self, path: str) -> bool:
        try:
            screen = self._screen_fn()
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(path, screen)
            return True
        except Exception as e:
            _logger.error(f"screenshot failed: {e}")
            return False

    # ── tap ───────────────────────────────────────────────────────────────────
    def tap(self, x: int, y: int, delay: float = 0.3):
        from bot import input as inp
        from config import cfg
        inp.click(self._hwnd, int(x), int(y),
                  delay=cfg["timing"].get("click_delay", 0.1))
        if delay > 0:
            time.sleep(delay)

    # ── swipe ─────────────────────────────────────────────────────────────────
    def swipe(self, x1: int, y1: int, x2: int, y2: int,
              duration: int = 200, delay: float = 0.5) -> bool:
        from bot import input as inp
        inp.drag(self._hwnd, int(x1), int(y1), int(x2), int(y2),
                 duration=duration / 1000.0)
        if delay > 0:
            time.sleep(delay)
        return True

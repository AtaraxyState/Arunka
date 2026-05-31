"""
Input injection via ADB — completely headless, no cursor movement.

ADB tap/swipe commands are sent directly to the emulator process.
The user's mouse is never touched.
"""

import time
from loguru import logger
from bot.adb import get_device


def _scale(x: int, y: int) -> tuple[int, int]:
    """Scale matched coordinates back to original emulator resolution."""
    from bot.window import capture_scale
    return int(x * capture_scale), int(y * capture_scale)


def click(device_serial: str, x: int, y: int, delay: float = 0.3) -> None:
    """Tap at (x, y) in downscaled coordinates."""
    sx, sy = _scale(x, y)
    get_device().shell(f"input tap {sx} {sy}")
    logger.debug(f"Tap ({sx},{sy})  [matched ({x},{y})]")
    time.sleep(delay)


def double_click(device_serial: str, x: int, y: int, delay: float = 0.3) -> None:
    click(device_serial, x, y, delay=0.08)
    click(device_serial, x, y, delay=delay)


def drag(device_serial: str, x1: int, y1: int, x2: int, y2: int,
         duration: float = 0.4) -> None:
    """Swipe from (x1,y1) to (x2,y2). Duration in seconds."""
    sx1, sy1 = _scale(x1, y1)
    sx2, sy2 = _scale(x2, y2)
    ms = int(duration * 1000)
    get_device().shell(f"input swipe {sx1} {sy1} {sx2} {sy2} {ms}")
    logger.debug(f"Swipe ({sx1},{sy1})→({sx2},{sy2}) {ms}ms")


def scroll_list(device_serial: str, screen_w: int, screen_h: int,
                direction: str = "down", amount: float = 0.35,
                duration: float = 0.4) -> None:
    """
    Swipe the item list.
    direction="down" → swipe up (bottom→top) to reveal items below
    direction="up"   → swipe down (top→bottom) to return to top
    """
    cx = int(screen_w * 0.55)
    swipe_px = int(screen_h * amount)

    if direction == "down":
        y1 = int(screen_h * 0.75)
        y2 = y1 - swipe_px
    else:
        y1 = int(screen_h * 0.25)
        y2 = y1 + swipe_px

    drag(device_serial, cx, y1, cx, y2, duration=duration)
    time.sleep(0.3)
    logger.debug(f"Scroll {direction}")

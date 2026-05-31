"""
Window / screen capture — ADB-based.

capture_window() grabs a screenshot from the emulator via ADB screencap,
returning a BGR numpy array exactly like the old Win32 version so the
vision and task layers are unchanged.
"""

import cv2
import numpy as np
from loguru import logger
from bot.adb import get_device

# Maximum width used for template matching.
# Coordinates returned by vision are in this space;
# click() scales them back up before sending to ADB.
_MATCH_MAX_WIDTH = 1920
capture_scale: float = 1.0


def find_window(title: str) -> str:
    """
    'Find' the game — just verifies ADB is connected and returns the device serial.
    `title` is ignored (kept for API compatibility with the rest of the bot).
    """
    device = get_device()
    logger.debug(f"ADB device ready: {device.serial}")
    return device.serial   # acts as the "hwnd" throughout the codebase


def capture_window(device_serial: str) -> np.ndarray:
    """
    Screencap the emulator and return a BGR numpy array.
    Downscales to _MATCH_MAX_WIDTH for fast template matching.
    """
    global capture_scale

    device = get_device()

    # adbutils API varies by version — try each method in order
    frame = None

    # Method 1: adbutils >= 0.15  device.screenshot() → PIL Image
    if hasattr(device, "screenshot"):
        try:
            pil_img = device.screenshot()
            frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.debug(f"screenshot() failed: {e}")

    # Method 2: device.screencap() → PNG bytes
    if frame is None and hasattr(device, "screencap"):
        try:
            raw   = device.screencap()
            arr   = np.frombuffer(raw, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.debug(f"screencap() failed: {e}")

    # Method 3: adb exec-out screencap -p via subprocess (always works)
    if frame is None:
        from bot.adb import _adb_path
        import subprocess
        result = subprocess.run(
            [_adb_path(), "-s", device.serial, "exec-out", "screencap", "-p"],
            capture_output=True, timeout=15
        )
        if result.returncode == 0 and result.stdout:
            arr   = np.frombuffer(result.stdout, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if frame is None or frame.size == 0:
        raise RuntimeError("All screencap methods failed — is BlueStacks fully loaded?")

    h, w = frame.shape[:2]
    logger.debug(f"Screencap: {w}x{h}")

    if w > _MATCH_MAX_WIDTH:
        capture_scale = w / _MATCH_MAX_WIDTH
        new_w = _MATCH_MAX_WIDTH
        new_h = int(h / capture_scale)
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.debug(f"Downscaled {w}x{h} → {new_w}x{new_h} (scale={capture_scale:.2f})")
    else:
        capture_scale = 1.0

    return frame

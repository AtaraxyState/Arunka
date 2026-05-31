"""
Launcher — start BlueStacks and connect ADB.
"""

import subprocess
import time
import os
from pathlib import Path
from loguru import logger
from config import cfg
from bot.adb import connect, get_device, _adb_path


def launch() -> str:
    """
    Start BlueStacks if not already running, connect ADB, return device serial.
    """
    # Try connecting first — emulator may already be running
    try:
        device = connect()
        logger.info(f"Emulator already running: {device.serial}")
        return device.serial
    except Exception:
        pass

    exe = cfg.get("adb", {}).get("emulator_exe", "")
    if not exe:
        raise RuntimeError(
            "Emulator path not set — go to Settings and point to BlueStacks HD-Player.exe"
        )

    logger.info(f"Starting BlueStacks: {exe}")
    subprocess.Popen([exe])

    # Wait for ADB to become available
    logger.info("Waiting for emulator ADB (up to 90s)…")
    for _ in range(90):
        time.sleep(1)
        try:
            device = connect()
            logger.info(f"Emulator ready: {device.serial}")
            return device.serial
        except Exception:
            pass

    raise RuntimeError("BlueStacks did not become available within 90 seconds.")


def close() -> None:
    """Kill the BlueStacks process."""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "HD-Player.exe"],
                       capture_output=True)
        logger.info("BlueStacks closed")
    except Exception as e:
        logger.warning(f"Could not close BlueStacks: {e}")

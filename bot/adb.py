"""
ADB device management.

Connects to the BlueStacks (or any) Android emulator via ADB.
All other bot modules use get_device() to obtain the active device.
"""

import subprocess
from pathlib import Path
from loguru import logger
from config import cfg

try:
    from adbutils import AdbClient, AdbDevice
    _HAS_ADBUTILS = True
except ImportError:
    _HAS_ADBUTILS = False

_device: "AdbDevice | None" = None


def _adb_path() -> str:
    """Find adb executable — bundled with BlueStacks or on PATH."""
    candidates = [
        cfg.get("adb", {}).get("adb_path", ""),
        r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
        r"C:\Program Files (x86)\BlueStacks\HD-Adb.exe",
        r"C:\ProgramData\BlueStacks\Client\HD-Adb.exe",
        "adb",  # system PATH
    ]
    for p in candidates:
        if not p:
            continue
        path = Path(p)
        if path.exists():
            return str(path)
        # Try on PATH
        try:
            subprocess.run([p, "version"], capture_output=True, timeout=3)
            return p
        except Exception:
            pass
    raise RuntimeError(
        "adb not found. Install Android Platform Tools or point adb_path "
        "to BlueStacks' HD-Adb.exe in config/settings.yaml."
    )


def connect() -> "AdbDevice":
    """Connect to the configured ADB device. Returns the device."""
    global _device

    if not _HAS_ADBUTILS:
        raise RuntimeError("adbutils not installed. Run setup.bat.")

    host = cfg.get("adb", {}).get("host", "localhost")
    port = cfg.get("adb", {}).get("port", 5555)
    address = f"{host}:{port}"

    adb_bin = _adb_path()
    client = AdbClient(host="localhost", port=5037)

    # Start the ADB server
    subprocess.run([adb_bin, "start-server"], capture_output=True)

    # Connect to emulator — log failures at DEBUG so they don't spam the UI
    result = subprocess.run(
        [adb_bin, "connect", address],
        capture_output=True, text=True
    )
    msg = result.stdout.strip()
    if "unable to connect" in msg.lower() or "failed" in msg.lower():
        logger.debug(f"ADB connect {address}: {msg}")
    else:
        logger.info(f"ADB connect {address}: {msg}")

    devices = client.device_list()
    if not devices:
        raise RuntimeError(
            f"No ADB devices found at {address}.\n"
            f"Make sure BlueStacks is running and ADB is enabled."
        )

    # Prefer the emulator at the configured address
    for d in devices:
        if address in d.serial:
            _device = d
            break
    else:
        _device = devices[0]

    logger.info(f"Connected to ADB device: {_device.serial}")
    return _device


def get_device() -> "AdbDevice":
    """Return current device, connecting if needed."""
    global _device
    if _device is None:
        return connect()
    return _device


def disconnect() -> None:
    global _device
    _device = None
    logger.info("ADB device disconnected")

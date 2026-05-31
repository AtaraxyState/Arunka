import yaml
import sys
from pathlib import Path


def _resolve_config_path() -> Path:
    """
    When running from source: config/settings.yaml next to this file.
    When frozen by PyInstaller: %APPDATA%/Arunka/settings.yaml
    This ensures settings persist across .exe runs and survive updates.
    """
    if getattr(sys, "frozen", False):
        base = Path.home() / "AppData" / "Roaming" / "Arunka"
        base.mkdir(parents=True, exist_ok=True)
        dest = base / "settings.yaml"
        # Seed from bundled defaults if not yet present
        if not dest.exists():
            bundled = Path(sys._MEIPASS) / "config" / "settings.yaml"
            if bundled.exists():
                import shutil
                shutil.copy(bundled, dest)
        return dest
    else:
        return Path(__file__).parent / "settings.yaml"


config_path = _resolve_config_path()

with open(config_path) as f:
    cfg = yaml.safe_load(f)


def save_cfg():
    """Write cfg back to disk."""
    with open(config_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)

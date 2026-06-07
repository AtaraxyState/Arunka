"""
Rolling history - persists a visual + structured record of every secret-shop roll.

A "run" is one bot session (one click of Run Shop Rolling). Each run gets its
own folder under the history root. A "roll" is one shop refresh cycle; we store
two screenshots per roll (top + bottom of the item list, captured before buying)
plus the detections found, what was bought, and the refresh outcome.

The HistoryRecorder is the ONLY thing that writes history. Every public method
is crash-safe: a disk/encoding error is logged and swallowed so recording can
never stall or break a running bot. Read/admin helpers at the bottom are used
by the History tab.

Layout:
  <history_root>/
    index.json                      # list of runs + quick summaries
    2026-05-30_14-22-03/            # one folder per run
      run.json                      # run metadata + all roll details
      roll_0001_top.jpg
      roll_0001_bottom.jpg
      ...
"""

import os
import sys
import json
import csv
import shutil
import datetime
from pathlib import Path

import cv2
from loguru import logger


# -- Paths -------------------------------------------------------------------

def history_root() -> Path:
    """
    history/ next to the project when running from source;
    %APPDATA%/Arunka/history when frozen as a .exe (matches config storage).
    """
    if getattr(sys, "frozen", False):
        base = Path.home() / "AppData" / "Roaming" / "Arunka" / "history"
    else:
        base = Path(__file__).resolve().parent.parent / "history"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _index_path() -> Path:
    return history_root() / "index.json"


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON to a temp file then rename, so readers never see a partial file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _read_json(path: Path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


# -- Recorder ----------------------------------------------------------------

class HistoryRecorder:
    """Records one run. Create at run start, call close() at the end."""

    def __init__(self, enabled: bool = True, jpeg_quality: int = 85):
        self.enabled = enabled
        self.jpeg_quality = int(jpeg_quality)
        self.run_id = None
        self.run_dir = None
        self._run = None           # in-memory run.json dict
        self._roll = None          # in-memory current roll dict
        if not enabled:
            return
        try:
            now = datetime.datetime.now()
            self.run_id = now.strftime("%Y-%m-%d_%H-%M-%S")
            self.run_dir = history_root() / self.run_id
            self.run_dir.mkdir(parents=True, exist_ok=True)
            self._run = {
                "id": self.run_id,
                "started": now.isoformat(timespec="seconds"),
                "ended": None,
                "status": "running",
                "rolls": [],
            }
            self._flush_run()
            self._update_index()
            logger.info(f"History recording to {self.run_dir}")
        except Exception as e:
            logger.error(f"History init failed, recording disabled: {e}")
            self.enabled = False

    # -- roll lifecycle ------------------------------------------------------

    def start_roll(self, n: int) -> None:
        if not self.enabled:
            return
        try:
            self._roll = {
                "n": int(n),
                "started": datetime.datetime.now().isoformat(timespec="seconds"),
                "top_img": None,
                "bottom_img": None,
                "detections": {"top": [], "bottom": []},
                "found": 0,
                "bought": 0,
                "mystic_bought": 0,
                "covenant_bought": 0,
                "outcome": None,
                "warnings": [],
            }
        except Exception as e:
            logger.error(f"start_roll failed: {e}")

    def add_screenshot(self, which: str, frame) -> None:
        """which is 'top' or 'bottom'; frame is a BGR numpy array."""
        if not self.enabled or self._roll is None or frame is None:
            return
        try:
            fname = f"roll_{self._roll['n']:04d}_{which}.jpg"
            cv2.imwrite(str(self.run_dir / fname), frame,
                        [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality])
            self._roll[f"{which}_img"] = fname
        except Exception as e:
            logger.error(f"add_screenshot({which}) failed: {e}")

    def record_detection(self, which: str, template: str,
                          x: int, y: int, score: float, status: str) -> None:
        """status: 'bought' or 'found_not_bought'."""
        if not self.enabled or self._roll is None:
            return
        try:
            self._roll["detections"].setdefault(which, []).append({
                "template": template,
                "x": int(x), "y": int(y),
                "score": round(float(score), 3),
                "status": status,
            })
            self._roll["found"] += 1
            if status == "bought":
                self._roll["bought"] += 1
                if "mystic" in template:
                    self._roll["mystic_bought"] += 1
                elif "covenant" in template:
                    self._roll["covenant_bought"] += 1
        except Exception as e:
            logger.error(f"record_detection failed: {e}")

    def record_outcome(self, outcome: str, warnings=None) -> None:
        if not self.enabled or self._roll is None:
            return
        try:
            self._roll["outcome"] = outcome
            if warnings:
                self._roll["warnings"].extend(warnings)
        except Exception as e:
            logger.error(f"record_outcome failed: {e}")

    def finish_roll(self) -> None:
        if not self.enabled or self._roll is None:
            return
        try:
            self._run["rolls"].append(self._roll)
            self._roll = None
            self._flush_run()
            self._update_index()
        except Exception as e:
            logger.error(f"finish_roll failed: {e}")

    def close(self, status: str = "done", elapsed_seconds: int = None) -> None:
        if not self.enabled:
            return
        try:
            # If a roll was started but never finished, persist what we have.
            if self._roll is not None:
                self._run["rolls"].append(self._roll)
                self._roll = None
            now = datetime.datetime.now()
            self._run["ended"] = now.isoformat(timespec="seconds")
            self._run["status"] = status
            # Duration: use the caller-supplied active elapsed (excludes pauses)
            # or fall back to wall-clock diff from started/ended.
            if elapsed_seconds is not None:
                self._run["duration_seconds"] = int(elapsed_seconds)
            else:
                try:
                    started = datetime.datetime.fromisoformat(self._run["started"])
                    self._run["duration_seconds"] = int((now - started).total_seconds())
                except Exception:
                    self._run["duration_seconds"] = None
            self._flush_run()
            self._update_index()
            logger.info(f"History run {self.run_id} closed ({status})")
        except Exception as e:
            logger.error(f"History close failed: {e}")

    # -- persistence ---------------------------------------------------------

    def _flush_run(self) -> None:
        _atomic_write_json(self.run_dir / "run.json", self._run)

    def _update_index(self) -> None:
        index = _read_json(_index_path(), {"runs": []})
        runs = index.get("runs", [])
        summary = _summarize_run(self._run)
        for i, r in enumerate(runs):
            if r.get("id") == self.run_id:
                runs[i] = summary
                break
        else:
            runs.append(summary)
        index["runs"] = runs
        _atomic_write_json(_index_path(), index)


def _summarize_run(run: dict) -> dict:
    rolls = run.get("rolls", [])
    return {
        "id": run.get("id"),
        "started": run.get("started"),
        "ended": run.get("ended"),
        "status": run.get("status"),
        "duration_seconds": run.get("duration_seconds"),
        "rolls": len(rolls),
        "found": sum(r.get("found", 0) for r in rolls),
        "bought": sum(r.get("bought", 0) for r in rolls),
        "mystic_bought": sum(r.get("mystic_bought", 0) for r in rolls),
        "covenant_bought": sum(r.get("covenant_bought", 0) for r in rolls),
    }


# -- Read / admin helpers (used by the History tab) --------------------------

def list_runs() -> list:
    """Return run summaries, newest first."""
    index = _read_json(_index_path(), {"runs": []})
    runs = index.get("runs", [])
    return sorted(runs, key=lambda r: r.get("started", ""), reverse=True)


def load_run(run_id: str) -> dict | None:
    """Return the full run.json (with all roll details) or None."""
    path = history_root() / run_id / "run.json"
    if not path.exists():
        return None
    return _read_json(path, None)


def roll_image_path(run_id: str, filename: str) -> Path | None:
    if not filename:
        return None
    p = history_root() / run_id / filename
    return p if p.exists() else None


def delete_run(run_id: str) -> bool:
    try:
        d = history_root() / run_id
        if d.exists():
            shutil.rmtree(d)
        index = _read_json(_index_path(), {"runs": []})
        index["runs"] = [r for r in index.get("runs", []) if r.get("id") != run_id]
        _atomic_write_json(_index_path(), index)
        logger.info(f"Deleted history run {run_id}")
        return True
    except Exception as e:
        logger.error(f"delete_run failed: {e}")
        return False


def delete_roll(run_id: str, n: int) -> bool:
    """Remove a single roll (its images + entry) from a run."""
    try:
        run = load_run(run_id)
        if run is None:
            return False
        kept = []
        for r in run.get("rolls", []):
            if r.get("n") == n:
                for key in ("top_img", "bottom_img"):
                    img = r.get(key)
                    if img:
                        p = history_root() / run_id / img
                        if p.exists():
                            p.unlink()
            else:
                kept.append(r)
        run["rolls"] = kept
        _atomic_write_json(history_root() / run_id / "run.json", run)
        # refresh index summary
        index = _read_json(_index_path(), {"runs": []})
        summ = _summarize_run(run)
        index["runs"] = [summ if x.get("id") == run_id else x
                         for x in index.get("runs", [])]
        _atomic_write_json(_index_path(), index)
        return True
    except Exception as e:
        logger.error(f"delete_roll failed: {e}")
        return False


def clear_all() -> bool:
    try:
        root = history_root()
        for child in root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            elif child.name == "index.json":
                child.unlink()
        _atomic_write_json(_index_path(), {"runs": []})
        logger.info("Cleared all history")
        return True
    except Exception as e:
        logger.error(f"clear_all failed: {e}")
        return False


def history_size_bytes() -> int:
    total = 0
    try:
        for dirpath, _, files in os.walk(history_root()):
            for f in files:
                try:
                    total += (Path(dirpath) / f).stat().st_size
                except OSError:
                    pass
    except Exception:
        pass
    return total


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def export_csv(run_id: str) -> Path | None:
    """Write one-row-per-roll summary CSV into the run folder; return its path."""
    run = load_run(run_id)
    if run is None:
        return None
    try:
        out = history_root() / run_id / f"{run_id}_summary.csv"
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["roll", "started", "found", "bought", "mystic_bought", "covenant_bought", "outcome", "warnings"])
            for r in run.get("rolls", []):
                w.writerow([
                    r.get("n"),
                    r.get("started", ""),
                    r.get("found", 0),
                    r.get("bought", 0),
                    r.get("mystic_bought", 0),
                    r.get("covenant_bought", 0),
                    r.get("outcome", ""),
                    "; ".join(r.get("warnings", [])),
                ])
        logger.info(f"Exported CSV: {out}")
        return out
    except Exception as e:
        logger.error(f"export_csv failed: {e}")
        return None

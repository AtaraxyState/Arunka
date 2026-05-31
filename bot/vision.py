"""
Vision - resolution-independent template matching.

Performance / accuracy notes:
  * Matching can run in GRAYSCALE (fast) or COLOUR. UI buttons match fine in
    gray, but ITEM ICONS are distinguished mainly by colour (a blue/gold compass
    vs a red medal vs a green equipment icon look near-identical in gray), so
    callers should pass gray=False for item icons. Default comes from config
    vision.grayscale.
  * The emulator resolution is fixed during a session, so templates captured via
    calibration match at ~1:1. We try scale 1.0 FIRST and accept it if it clears
    the threshold - skipping the expensive multi-scale sweep. Toggle with
    config vision.fast_scale_first.
  * Loaded templates are cached (colour + gray) keyed by file mtime.
  * find() / find_all() accept an optional pixel region (x0, y0, x1, y1).
"""

import cv2
import numpy as np
from pathlib import Path
from loguru import logger

try:
    from config import cfg as _CFG
except Exception:
    _CFG = {}

ASSETS_DIR = Path("assets/templates")

_SEARCH_SCALES = [0.50, 0.60, 0.70, 0.80, 0.90, 1.00,
                  1.10, 1.20, 1.35, 1.50, 1.75, 2.00]

_scale_cache: dict[str, float] = {}
_tmpl_cache: dict = {}   # name -> {"mtime", "color", "gray"}


# -- Options -----------------------------------------------------------------

def _vopt(key, default):
    try:
        return _CFG.get("vision", {}).get(key, default)
    except Exception:
        return default


def _resolve_gray(gray):
    """gray=None -> config default; otherwise honour the explicit choice."""
    if gray is None:
        return bool(_vopt("grayscale", True))
    return bool(gray)


def _fast_first() -> bool:
    return bool(_vopt("fast_scale_first", True))


# -- Template loading (cached) -----------------------------------------------

def _load_entry(name: str) -> dict:
    path = ASSETS_DIR / f"{name}.png"
    try:
        mtime = path.stat().st_mtime
    except OSError:
        raise FileNotFoundError(f"Template not found: {path}")

    ent = _tmpl_cache.get(name)
    if ent is not None and ent["mtime"] == mtime:
        return ent

    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Template not found: {path}")
    ent = {
        "mtime": mtime,
        "color": img,
        "gray": cv2.cvtColor(img, cv2.COLOR_BGR2GRAY),
    }
    _tmpl_cache[name] = ent
    return ent


def _prep(screen: np.ndarray, gray: bool) -> np.ndarray:
    if gray and screen.ndim == 3:
        return cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    return screen


def _tmpl_for(ent: dict, gray: bool) -> np.ndarray:
    return ent["gray"] if gray else ent["color"]


# -- Matching ----------------------------------------------------------------

def _match_at_scale(screen: np.ndarray, tmpl: np.ndarray, scale: float):
    """Resize tmpl by scale and match. Returns (score, x, y, tw, th) or None."""
    sh, sw = screen.shape[:2]
    new_w = max(4, int(tmpl.shape[1] * scale))
    new_h = max(4, int(tmpl.shape[0] * scale))
    if new_w > sw or new_h > sh:
        return None
    if scale == 1.0:
        resized = tmpl
    else:
        interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        resized = cv2.resize(tmpl, (new_w, new_h), interpolation=interp)
    result = cv2.matchTemplate(screen, resized, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(result)
    return score, loc[0], loc[1], new_w, new_h


def _best_match(screen: np.ndarray, tmpl: np.ndarray,
                name: str, threshold: float):
    """Returns (score, x, y, tw, th) or None. 1.0 fast path -> cache -> sweep."""
    if _fast_first():
        r = _match_at_scale(screen, tmpl, 1.0)
        if r and r[0] >= threshold:
            _scale_cache[name] = 1.0
            return r

    cached = _scale_cache.get(name)
    if cached is not None and cached != 1.0:
        for s in (cached, cached * 0.95, cached * 1.05):
            r = _match_at_scale(screen, tmpl, s)
            if r and r[0] >= threshold:
                return r

    best = None
    winning_scale = None
    for scale in _SEARCH_SCALES:
        r = _match_at_scale(screen, tmpl, scale)
        if r and (best is None or r[0] > best[0]):
            best = r
            winning_scale = scale

    if best and best[0] >= threshold:
        _scale_cache[name] = winning_scale
        return best
    return None


def _crop(screen: np.ndarray, region):
    if region is None:
        return screen, 0, 0
    h, w = screen.shape[:2]
    x0 = max(0, int(region[0])); y0 = max(0, int(region[1]))
    x1 = min(w, int(region[2])); y1 = min(h, int(region[3]))
    if x1 <= x0 or y1 <= y0:
        return screen, 0, 0
    return screen[y0:y1, x0:x1], x0, y0


# -- Public API --------------------------------------------------------------

def find(screen: np.ndarray, template_name: str,
         threshold: float = 0.82, region=None, gray=None):
    """
    Find a template (returns (cx, cy) centre of best match, or None).
    gray: None=config default, True=grayscale, False=colour (use for item icons).
    region: optional pixel (x0, y0, x1, y1) to restrict the search area.
    """
    try:
        ent = _load_entry(template_name)
    except FileNotFoundError:
        logger.debug(f"Template file missing: {template_name}")
        return None

    g = _resolve_gray(gray)
    prep, ox, oy = _crop(_prep(screen, g), region)
    r = _best_match(prep, _tmpl_for(ent, g), template_name, threshold)
    if r is None:
        logger.debug(f"'{template_name}' not found")
        return None

    score, x, y, tw, th = r
    cx, cy = x + tw // 2 + ox, y + th // 2 + oy
    logger.debug(f"'{template_name}' -> ({cx},{cy}) score={score:.2f} "
                 f"scale={_scale_cache.get(template_name, 1.0):.2f}")
    return cx, cy


def find_all(screen: np.ndarray, template_name: str,
             threshold: float = 0.82, return_scores: bool = False,
             region=None, gray=None):
    """
    Find all non-overlapping occurrences.
    Returns [(cx, cy)] or, with return_scores, [(cx, cy, score)].
    gray: None=config default, True=grayscale, False=colour (use for item icons).
    """
    try:
        ent = _load_entry(template_name)
    except FileNotFoundError:
        return []

    g = _resolve_gray(gray)
    prep, ox, oy = _crop(_prep(screen, g), region)
    tmpl = _tmpl_for(ent, g)

    scale = _scale_cache.get(template_name)
    if scale is None:
        r = _best_match(prep, tmpl, template_name, threshold)
        if r is None:
            return []
        scale = _scale_cache.get(template_name, 1.0)

    if scale == 1.0:
        resized = tmpl
    else:
        new_w = max(4, int(tmpl.shape[1] * scale))
        new_h = max(4, int(tmpl.shape[0] * scale))
        resized = cv2.resize(tmpl, (new_w, new_h))
    tw, th = resized.shape[1], resized.shape[0]

    result = cv2.matchTemplate(prep, resized, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)
    points = list(zip(*locations[::-1]))

    filtered = []  # (cx, cy, score)
    for (x, y) in points:
        cx, cy = int(x + tw // 2 + ox), int(y + th // 2 + oy)
        if all(abs(cx - fx) > tw // 2 or abs(cy - fy) > th // 2
               for fx, fy, _ in filtered):
            filtered.append((cx, cy, float(result[y, x])))

    logger.debug(f"'{template_name}' -> {len(filtered)} matches at scale={scale:.2f}")
    if return_scores:
        return filtered
    return [(cx, cy) for cx, cy, _ in filtered]


def wait_for(screen_fn, template_name: str,
             timeout: float = 10.0, interval: float = 0.5, region=None, gray=None):
    """Poll until template appears or timeout. Returns (cx, cy) or None."""
    import time
    elapsed = 0.0
    while elapsed < timeout:
        pos = find(screen_fn(), template_name, region=region, gray=gray)
        if pos:
            return pos
        time.sleep(interval)
        elapsed += interval
    logger.warning(f"Timeout waiting for '{template_name}'")
    return None


def invalidate_cache(template_name: str | None = None) -> None:
    """Clear caches - call after recapturing templates."""
    if template_name:
        _scale_cache.pop(template_name, None)
        _tmpl_cache.pop(template_name, None)
    else:
        _scale_cache.clear()
        _tmpl_cache.clear()

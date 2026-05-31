"""
Navigator — nav points + named routes for menu traversal.

Nav points : individual (x, y) clicks recorded via calibration
Routes     : named sequences of nav point keys, e.g. "to_secret_shop"
"""

import json
import time
from pathlib import Path
from loguru import logger
from bot import input as inp
from bot import vision

NAV_FILE    = Path("assets/nav_points.json")
ROUTES_FILE = Path("assets/nav_routes.json")


# ── Low-level data access ─────────────────────────────────────────────────────

def _load_points() -> dict:
    if not NAV_FILE.exists():
        return {}
    with open(NAV_FILE) as f:
        return json.load(f).get("points", {})


def _load_routes() -> dict:
    if not ROUTES_FILE.exists():
        return {}
    with open(ROUTES_FILE) as f:
        return json.load(f).get("routes", {})


def _save_points(points: dict) -> None:
    data = {"points": points}
    with open(NAV_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _save_routes(routes: dict) -> None:
    data = {"routes": routes}
    with open(ROUTES_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Nav points ────────────────────────────────────────────────────────────────

def save_point(name: str, x: int, y: int, landmark: str | None = None) -> None:
    points = _load_points()
    points[name] = {"x": x, "y": y}
    if landmark:
        points[name]["landmark"] = landmark
    _save_points(points)
    logger.info(f"Saved nav point: {name} ({x}, {y})")


def delete_point(name: str) -> None:
    points = _load_points()
    points.pop(name, None)
    _save_points(points)


# ── Routes ────────────────────────────────────────────────────────────────────

def save_route(name: str, steps: list[str], description: str = "") -> None:
    """Save a named route as an ordered list of nav point keys."""
    routes = _load_routes()
    routes[name] = {"steps": steps, "description": description}
    _save_routes(routes)
    logger.info(f"Saved route: {name} → {' → '.join(steps)}")


def delete_route(name: str) -> None:
    routes = _load_routes()
    routes.pop(name, None)
    _save_routes(routes)


def get_route(name: str) -> list[str] | None:
    """Return the step list for a route, or None if not found."""
    routes = _load_routes()
    if name not in routes:
        logger.error(f"Route '{name}' not defined")
        return None
    return routes[name]["steps"]


# ── Execution ─────────────────────────────────────────────────────────────────

def follow_route(hwnd: int, screen_fn, route_name: str, step_wait: float = 1.0) -> bool:
    """
    Execute a named route end-to-end.
    Returns True on success, False if any step is missing or fails.

    Example:
        navigator.follow_route(hwnd, screen_fn, "to_secret_shop")
    """
    steps = get_route(route_name)
    if steps is None:
        return False
    logger.info(f"Following route: {route_name} ({len(steps)} steps)")
    return _execute_steps(hwnd, screen_fn, steps, step_wait)


def go(hwnd: int, screen_fn, *point_names: str, wait: float = 1.0) -> bool:
    """Execute an ad-hoc sequence of nav point names (no route needed)."""
    return _execute_steps(hwnd, screen_fn, list(point_names), wait)


def _execute_steps(hwnd: int, screen_fn, steps: list[str], wait: float) -> bool:
    points = _load_points()
    for name in steps:
        if name not in points:
            logger.error(f"Nav point '{name}' not recorded — run calibration first")
            return False
        pt = points[name]
        x, y = pt["x"], pt["y"]

        # Optional: wait for a landmark before clicking
        landmark = pt.get("landmark")
        if landmark:
            if not vision.wait_for(screen_fn, landmark, timeout=8.0):
                logger.warning(f"Landmark '{landmark}' not visible before '{name}'")

        inp.click(hwnd, x, y)
        logger.debug(f"Nav: {name} ({x}, {y})")
        time.sleep(wait)

    return True

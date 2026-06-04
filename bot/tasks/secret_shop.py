"""
Secret shop task.

Flow (mirrors reference bot's check_store + refresh loop):
  1. Scan visible items  — buy covenant bookmarks / mystic medals if present
  2. Scroll down
  3. Scan again          — buy any that are now visible
  4. Refresh shop (costs 3 skystones) + confirm
  5. Repeat up to refresh_limit times
"""

import time
from loguru import logger
from bot import vision, input as inp, navigator
from config import cfg


def run(hwnd: int, screen_fn, should_run=None, recorder=None,
        step_fn=None, restart_fn=None) -> None:
    if should_run is None:
        should_run = lambda: True
    if step_fn is None:
        step_fn = lambda s: None
    if restart_fn is None:
        restart_fn = lambda: False

    logger.info("Starting secret shop task")
    vision.invalidate_cache()

    if navigator._load_routes().get("to_secret_shop"):
        step_fn("navigate")
        if not navigator.follow_route(hwnd, screen_fn, "to_secret_shop"):
            logger.error("Could not navigate to secret shop - aborting")
            return

    for i in range(cfg["secret_shop"]["refresh_limit"]):
        if not should_run():
            logger.info("Stop requested")
            break

        if recorder:
            recorder.start_roll(i + 1)

        screen = screen_fn()
        h, w = screen.shape[:2]
        t = cfg["timing"]

        # Per-template flags — exact equivalent of reference's mystic_bought /
        # covenant_bought. Once a type is bought it is NEVER searched again
        # this roll, so a sold icon scrolling into view can't trigger a click.
        bought_templates: set[str] = set()

        # ── Scan 1 (top of list) ─────────────────────────────────────────
        step_fn("scan_top")
        _buy_items(hwnd, screen_fn, should_run, recorder,
                   which="top", bought_templates=bought_templates)

        if not should_run():
            if recorder: recorder.record_outcome("stopped", []); recorder.finish_roll()
            break

        if restart_fn():
            if recorder: recorder.record_outcome("restarted", []); recorder.finish_roll()
            continue

        # ── Scroll down ──────────────────────────────────────────────────
        step_fn("scroll_1")
        inp.scroll_list(hwnd, w, h, direction="down",
                        amount=t.get("scroll_amount", 0.35),
                        duration=t.get("scroll_duration", 0.3))
        time.sleep(0.5)

        # ── Scan 2 (bottom of list) ──────────────────────────────────────
        step_fn("scan_bot")
        _buy_items(hwnd, screen_fn, should_run, recorder,
                   which="bottom", bought_templates=bought_templates)

        if not should_run():
            if recorder: recorder.record_outcome("stopped", []); recorder.finish_roll()
            break

        if restart_fn():
            if recorder: recorder.record_outcome("restarted", []); recorder.finish_roll()
            continue

        # ── Refresh ───────────────────────────────────────────────────────
        step_fn("refresh")
        refresh_btn = vision.find(screen_fn(), "shop_refresh_btn")
        if not refresh_btn:
            logger.warning("Refresh button not found — stopping")
            if recorder: recorder.record_outcome("refresh_button_missing", []); recorder.finish_roll()
            break

        inp.click(hwnd, *refresh_btn, delay=t["click_delay"])
        confirm = vision.wait_for(screen_fn, "shop_confirm_refresh_btn", timeout=4.0)
        if confirm:
            inp.click(hwnd, *confirm, delay=t["click_delay"])
        else:
            logger.warning("Refresh confirm not found")

        if recorder:
            recorder.record_outcome("refreshed", [])
            recorder.finish_roll()

        time.sleep(t["navigation_delay"])
        logger.info(f"Refreshed ({i + 1}/{cfg['secret_shop']['refresh_limit']})")

    logger.info("Secret shop task done")


def _buy_items(hwnd: int, screen_fn, should_run=None,
               recorder=None, which=None,
               bought_templates: "set[str] | None" = None) -> None:
    """
    Scan for covenant bookmarks and mystic medals and buy them.

    bought_templates is shared across both scans in a roll — once a template
    type is bought it is skipped entirely in the next scan, regardless of
    screen position. This mirrors the reference bot's mystic_bought /
    covenant_bought instance flags that prevent re-detecting a sold icon
    after it has scrolled into a new Y position.
    """
    if should_run is None:
        should_run = lambda: True
    if bought_templates is None:
        bought_templates = set()

    record = recorder is not None and which is not None
    if record:
        recorder.add_screenshot(which, screen_fn())

    targets = []
    if cfg["secret_shop"]["buy_mystic_medals"]:
        targets.append("item_mystic_medal")
    if cfg["secret_shop"]["buy_bookmarks"]:
        targets.append("item_covenant_bookmark")

    for template in targets:
        if not should_run():
            break

        # Already bought this type this roll — don't even look for it
        if template in bought_templates:
            logger.debug(f"Skipping {template} — already bought this roll")
            continue

        current = screen_fn()
        h, w = current.shape[:2]

        pos = vision.find(current, template, threshold=0.82, gray=True)
        if pos is None:
            logger.debug(f"{template} not found")
            continue

        cx, cy = pos
        buy_x = w - 65
        logger.info(f"Found {template} at ({cx},{cy}) — clicking buy ({buy_x},{cy})")
        inp.click(hwnd, buy_x, cy, delay=cfg["timing"]["click_delay"])

        confirm = vision.wait_for(screen_fn, "shop_confirm_buy_btn", timeout=3.0)
        if confirm:
            inp.click(hwnd, *confirm, delay=cfg["timing"]["click_delay"])
            logger.info(f"Bought: {template}")
            bought_templates.add(template)
            if record:
                recorder.record_detection(which, template, cx, cy, 0.0, "bought")
            time.sleep(cfg["timing"].get("after_purchase_delay", 1.2))
        else:
            logger.warning(f"No confirm for {template} — marking as done to avoid retry")
            bought_templates.add(template)
            if record:
                recorder.record_detection(which, template, cx, cy, 0.0, "found_not_bought")

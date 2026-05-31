"""
Secret shop task.

Flow:
  1. Scan visible items — buy matching ones (covenant bookmark, mystic medal)
  2. Click Refresh (bottom-left, costs 3 skystones)
  3. Confirm skystone dialog
  4. Repeat up to refresh_limit times

Buy logic uses a fresh screen before every purchase attempt to avoid
stale-position bugs (e.g. the purchased row's Buy button graying out
while the old position list still references that row).
"""

import time
from loguru import logger
from bot import vision, input as inp, navigator
from config import cfg

_DEFAULT_ITEM_THRESHOLD = 0.88


def _item_threshold() -> float:
    return float(cfg["secret_shop"].get("item_threshold", _DEFAULT_ITEM_THRESHOLD))


def run(hwnd: int, screen_fn, should_run=None, recorder=None) -> None:
    if should_run is None:
        should_run = lambda: True

    logger.info("Starting secret shop task")

    if navigator._load_routes().get("to_secret_shop"):
        if not navigator.follow_route(hwnd, screen_fn, "to_secret_shop"):
            logger.error("Could not navigate to secret shop - aborting")
            return

    for i in range(cfg["secret_shop"]["refresh_limit"]):
        if not should_run():
            logger.info("Stop requested - ending secret shop task")
            break

        if recorder:
            recorder.start_roll(i + 1)
        warnings = []

        screen = screen_fn()
        h, w = screen.shape[:2]

        t = cfg["timing"]
        scroll_kw = dict(
            amount=t.get("scroll_amount", 0.35),
            duration=t.get("scroll_duration", 0.3),
        )

        # Pass 1 — top of the visible list
        _buy_items(hwnd, screen_fn, should_run, recorder, which="top")

        if not should_run():
            if recorder:
                recorder.record_outcome("stopped", warnings)
                recorder.finish_roll()
            break

        # Pass 2 — scroll down, scan middle
        inp.scroll_list(hwnd, w, h, direction="down", **scroll_kw)
        _buy_items(hwnd, screen_fn, should_run, recorder, which=None)

        if not should_run():
            if recorder:
                recorder.record_outcome("stopped", warnings)
                recorder.finish_roll()
            break

        # Pass 3 — scroll down again, scan bottom
        inp.scroll_list(hwnd, w, h, direction="down", **scroll_kw)
        _buy_items(hwnd, screen_fn, should_run, recorder, which="bottom")

        if not should_run():
            if recorder:
                recorder.record_outcome("stopped", warnings)
                recorder.finish_roll()
            break

        # Refresh
        refresh = vision.find(screen_fn(), "shop_refresh_btn")
        if not refresh:
            logger.warning("Refresh button not found - navigating back to shop")
            warnings.append("refresh button not found")
            if recorder:
                recorder.record_outcome("refresh_button_missing", warnings)
                recorder.finish_roll()
            break

        inp.click(hwnd, *refresh, delay=cfg["timing"]["click_delay"])

        confirm = vision.wait_for(screen_fn, "shop_confirm_refresh_btn", timeout=4.0)
        if confirm:
            inp.click(hwnd, *confirm, delay=cfg["timing"]["click_delay"])
        else:
            logger.warning("Confirm dialog not found after refresh click")
            warnings.append("refresh confirm dialog not found")

        if recorder:
            recorder.record_outcome("refreshed", warnings)
            recorder.finish_roll()

        time.sleep(cfg["timing"]["navigation_delay"])
        logger.info(f"Refreshed ({i + 1}/{cfg['secret_shop']['refresh_limit']})")

    logger.info("Secret shop task done")


def _buy_items(hwnd: int, screen_fn, should_run=None,
               recorder=None, which=None) -> None:
    """
    Scan for wanted items and buy each one.

    Key design: we re-capture a fresh screen before every buy attempt.
    This prevents stale-position bugs where the purchased row's Buy button
    becomes grayed and the bot would otherwise click the wrong row.
    """
    if should_run is None:
        should_run = lambda: True

    targets = []
    if cfg["secret_shop"]["buy_bookmarks"]:
        targets.append("item_covenant_bookmark")
    if cfg["secret_shop"]["buy_mystic_medals"]:
        targets.append("item_mystic_medal")

    thr = _item_threshold()
    record = recorder is not None and which is not None

    # Save the pre-purchase screenshot for history (shows what was on screen)
    if record:
        recorder.add_screenshot(which, screen_fn())

    for template in targets:
        # Keep buying until none of this item type remains visible
        while should_run():
            current = screen_fn()
            hits = vision.find_all(current, template, threshold=thr,
                                   return_scores=True, gray=False)
            if not hits:
                break  # None left — move on to next template

            item_x, item_y, score = hits[0]
            buy_x = _buy_button_x(current, item_y)

            logger.debug(
                f"Buying {template} at ({item_x},{item_y}) "
                f"score={score:.2f}, buy_x={buy_x}"
            )
            inp.click(hwnd, buy_x, item_y, delay=cfg["timing"]["click_delay"])

            confirm = vision.wait_for(screen_fn, "shop_confirm_buy_btn", timeout=3.0)
            if confirm:
                inp.click(hwnd, *confirm, delay=cfg["timing"]["click_delay"])
                logger.info(f"Bought: {template} (score {score:.2f})")
                if record:
                    recorder.record_detection(which, template,
                                              item_x, item_y, score, "bought")
            else:
                # No confirm dialog — we probably clicked the wrong button.
                # Stop immediately to avoid buying unintended items.
                logger.warning(
                    f"No confirm dialog for {template} — "
                    "stopping to avoid wrong purchase"
                )
                if record:
                    recorder.record_detection(which, template,
                                              item_x, item_y, score,
                                              "found_not_bought")
                return

            # Wait for the UI to fully settle before the next scan
            time.sleep(0.4)


def _buy_button_x(screen, item_y: int) -> int:
    h, w = screen.shape[:2]
    y1 = max(0, item_y - 40)
    y2 = min(h, item_y + 40)
    pos = vision.find(screen, "shop_buy_btn", threshold=0.80,
                      region=(0, y1, w, y2))
    if pos:
        return pos[0]
    return w - 65  # fallback: Buy buttons sit ~65px from the right edge

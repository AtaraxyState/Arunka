"""
Secret shop task — thin wrapper around SecretShopBot.

SecretShopBot handles all detection/buying logic. This module wires it to
Arunka's ADB + screen infrastructure, adds history recording, and emits
the loguru "Bought:" messages the UI counter listens for.
"""

import time
from pathlib import Path
from loguru import logger

from bot import navigator, input as inp
from bot.tasks.adb_controller import ADBController
from bot.tasks.image_matcher import ImageMatcher
from bot.tasks.secret_shop_bot import SecretShopBot
from bot import vision
from config import cfg

_ASSETS = Path("assets/templates")


def _make_bot(hwnd: int, screen_fn) -> SecretShopBot:
    adb = ADBController(hwnd, screen_fn)

    automation_settings = {
        "swipe": {
            "duration_ms":   cfg["timing"].get("scroll_duration", 0.3) * 1000,
            "x_ratio":       0.75,
            "start_y_ratio": 0.75,
            "end_y_ratio":   0.25,
        },
        "macro": {
            "enabled_items": _enabled_items(),
            "timings": {
                "after_scroll":                   0.5,
                "after_refresh":                  cfg["timing"].get("navigation_delay", 0.5),
                "after_screenshot":               0.2,
                "after_purchase_tap":             0.5,
                "buy_button_wait_attempts":       4,
                "buy_button_wait_interval":       0.5,
                "verify_interval":                0.3,
                "close_popup_delay":              0.3,
                "refresh_confirm_attempts":       5,
                "refresh_confirm_delay":          0.5,
                "refresh_confirm_retry_interval": 0.3,
                "refresh_recovery_attempts":      1,
                "refresh_retry":                  2.0,
            },
        },
    }

    bot = SecretShopBot(
        adb_controller=adb,
        base_dir=str(_ASSETS),
        automation_settings=automation_settings,
    )

    # Flat asset directory — override sub-dirs and filenames
    bot.ITEMS_DIR   = ""
    bot.BUTTONS_DIR = ""
    bot.MYSTIC_MEDAL             = "item_mystic_medal.png"
    bot.COVENANT_BOOKMARK        = "item_covenant_bookmark.png"
    bot.FRIENDSHIP_POINT         = "friendship_point.png"
    bot.REFRESH_BUTTON           = "shop_refresh_btn.png"
    bot.REFRESH_CONFIRM_BUTTON   = "shop_confirm_refresh_btn.png"
    bot.PURCHASE_BUTTON          = "shop_buy_btn.png"
    bot.BUY_BUTTON               = "shop_confirm_buy_btn.png"
    bot.PURCHASE_BUTTON_DISABLED = "shop_buy_btn_disabled.png"

    bot.item_definitions = bot._build_item_definitions()
    bot.enabled_items    = bot._build_enabled_items()
    bot.button_images    = bot._build_button_images()

    return bot


def _enabled_items() -> list:
    items = []
    if cfg["secret_shop"].get("buy_mystic_medals", True):
        items.append("mystic_medal")
    if cfg["secret_shop"].get("buy_bookmarks", True):
        items.append("covenant_bookmark")
    return items


# Map SecretShopBot item key → our template name (for recorder)
_TEMPLATE_NAME = {
    "mystic_medal":      "item_mystic_medal",
    "covenant_bookmark": "item_covenant_bookmark",
}


def _scan_and_buy(bot: SecretShopBot, page_num: int, which: str,
                  screen_fn, recorder, should_run) -> int:
    """
    Run one scan+buy pass. Returns number of items bought this pass.
    Handles history screenshots and loguru counter messages.
    """
    bought = 0

    # Screenshot for history before scanning
    if recorder:
        frame = screen_fn()
        recorder.add_screenshot(which, frame)

    found = bot._scan_shop_page(page_num=page_num)

    for item_name, location in found.items():
        if not should_run():
            break

        # Snapshot stats before purchase attempt
        stat_key = bot.item_definitions.get(item_name, {}).get("stat_key", "")
        before = bot.stats.get(stat_key, 0)

        success = bot._purchase_item(item_name, location, verification_count=1)

        after = bot.stats.get(stat_key, 0)
        purchased = after > before  # SecretShopBot increments on success

        template = _TEMPLATE_NAME.get(item_name, item_name)
        cx = location[0] + location[2] // 2
        cy = location[1] + location[3] // 2

        if purchased:
            logger.info(f"Bought: {template}")   # triggers UI counter in api
            bought += 1
            if recorder:
                recorder.record_detection(which, template, cx, cy, 0.0, "bought")
        else:
            logger.warning(f"Purchase failed for {item_name}")
            if recorder:
                recorder.record_detection(which, template, cx, cy, 0.0, "found_not_bought")

        if not success and not purchased:
            # Hard failure (e.g. gold shortage) — stop the whole run
            logger.error("Purchase hard-failed — stopping shop task")
            return -1

    return bought


def run(hwnd: int, screen_fn, should_run=None, recorder=None,
        step_fn=None, restart_fn=None, sky_fn=None,
        sky_decrement_fn=None) -> None:

    if should_run       is None: should_run       = lambda: True
    if step_fn          is None: step_fn          = lambda s: None
    if restart_fn       is None: restart_fn       = lambda: False
    if sky_fn           is None: sky_fn           = lambda: None
    if sky_decrement_fn is None: sky_decrement_fn = sky_fn

    logger.info("Secret shop starting")
    vision.invalidate_cache()

    # Read skystone at the very start
    sky_fn()

    if navigator._load_routes().get("to_secret_shop"):
        if not navigator.follow_route(hwnd, screen_fn, "to_secret_shop"):
            logger.error("Navigation failed")
            return

    bot = _make_bot(hwnd, screen_fn)
    refresh_limit = cfg["secret_shop"]["refresh_limit"]

    for i in range(refresh_limit):
        if not should_run():
            break

        if recorder:
            recorder.start_roll(i + 1)

        screen = screen_fn()
        h, w   = screen.shape[:2]

        logger.info(f"Roll {i + 1}/{refresh_limit}")

        # ── Scan page 1 ───────────────────────────────────────────────────
        step_fn("scan_top")
        result = _scan_and_buy(bot, page_num=1, which="top",
                               screen_fn=screen_fn, recorder=recorder,
                               should_run=should_run)
        if result == -1:
            if recorder: recorder.record_outcome("purchase_failed", []); recorder.finish_roll()
            break

        if not should_run():
            if recorder: recorder.record_outcome("stopped", []); recorder.finish_roll()
            break

        # ── Scroll ────────────────────────────────────────────────────────
        step_fn("scroll_1")
        bot._scroll_down()
        time.sleep(bot._timing("after_scroll", 0.5))

        # ── Scan page 2 ───────────────────────────────────────────────────
        step_fn("scan_bot")
        result = _scan_and_buy(bot, page_num=2, which="bottom",
                               screen_fn=screen_fn, recorder=recorder,
                               should_run=should_run)
        if result == -1:
            if recorder: recorder.record_outcome("purchase_failed", []); recorder.finish_roll()
            break

        if not should_run():
            if recorder: recorder.record_outcome("stopped", []); recorder.finish_roll()
            break

        # ── Refresh ───────────────────────────────────────────────────────
        step_fn("refresh")
        if not bot._refresh_shop_with_recovery():
            logger.warning("Refresh failed — stopping")
            if recorder: recorder.record_outcome("refresh_button_missing", []); recorder.finish_roll()
            break

        bot.mystic_bought   = False
        bot.covenant_bought = False

        # Decrement skystone by 3 (cost per refresh) — no OCR needed
        sky_decrement_fn()

        if recorder:
            recorder.record_outcome("refreshed", [])
            recorder.finish_roll()

        time.sleep(cfg["timing"]["navigation_delay"])
        logger.info(f"Refreshed {i + 1}/{refresh_limit}")

    logger.info("Secret shop done")

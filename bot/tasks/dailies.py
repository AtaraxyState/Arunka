"""
Dailies task - collect daily rewards and complete quick daily missions.
"""

import time
from loguru import logger
from bot import vision, input as inp
from config import cfg


DAILY_STEPS = [
    # (key, screen to navigate to, button template, confirm template or None)
    ("missions",   "daily_missions_tab",  "daily_claim_all_btn",   None),
    ("mailbox",    "mailbox_tab",         "mailbox_claim_all_btn",  None),
    ("reputation", "reputation_tab",      "reputation_claim_btn",   "confirm_btn"),
]


def run(hwnd: int, screen_fn, selections=None, should_run=None) -> None:
    """
    Collect daily rewards.

    selections: optional dict like {"missions": True, "mailbox": False, ...}.
                Steps whose key is False are skipped. Missing keys default to True.
    should_run: optional callable returning False when the UI requests a stop.
    """
    if should_run is None:
        should_run = lambda: True
    if selections is None:
        selections = {}

    from bot import navigator
    logger.info("Starting dailies task")

    if navigator._load_routes().get("to_daily_missions"):
        if not navigator.follow_route(hwnd, screen_fn, "to_daily_missions"):
            logger.error("Could not navigate to daily missions - aborting")
            return

    for key, nav_template, action_template, confirm_template in DAILY_STEPS:
        if not should_run():
            logger.info("Stop requested - ending dailies task")
            break
        if not selections.get(key, True):
            logger.info(f"Skipping '{key}' (disabled)")
            continue

        # Navigate to the right tab
        nav = vision.wait_for(screen_fn, nav_template, timeout=8.0)
        if not nav:
            logger.warning(f"Could not find '{nav_template}', skipping step")
            continue

        inp.click(hwnd, *nav)
        time.sleep(cfg["timing"]["navigation_delay"])

        # Perform the action
        action = vision.wait_for(screen_fn, action_template, timeout=5.0)
        if not action:
            logger.info(f"'{action_template}' not found - nothing to collect here")
            continue

        inp.click(hwnd, *action)

        if confirm_template:
            confirm = vision.wait_for(screen_fn, confirm_template, timeout=3.0)
            if confirm:
                inp.click(hwnd, *confirm)

        time.sleep(cfg["timing"]["navigation_delay"])
        logger.info(f"Completed step: {action_template}")

    logger.info("Dailies task done")

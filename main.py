"""
Arunka — Epic Seven bot
Run from terminal: python main.py
"""

import time
from loguru import logger
from config import cfg
from bot.window import find_window, capture_window
from bot.tasks import secret_shop, dailies


def main():
    logger.add("arunka.log", rotation="1 day", retention="7 days")
    logger.info("Arunka starting up")

    hwnd = find_window("")

    # Convenience wrapper so tasks always get a fresh capture
    def screen():
        return capture_window(hwnd)

    if cfg["bot"]["tasks"].get("dailies"):
        dailies.run(hwnd, screen)

    if cfg["bot"]["tasks"].get("secret_shop"):
        secret_shop.run(hwnd, screen)

    logger.info("All tasks complete")


if __name__ == "__main__":
    main()

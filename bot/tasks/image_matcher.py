"""
ImageMatcher adapter — implements the interface expected by
secret_shop_bot.SecretShopBot using plain OpenCV (grayscale).
"""

import cv2
import numpy as np
from typing import Optional


class ImageMatcher:
    def __init__(self, threshold: float = 0.92):
        self.threshold = threshold

    # ── single best match ─────────────────────────────────────────────────────
    def find_image(self, screenshot_path: str, template_path: str,
                   threshold: float = None) -> Optional[tuple]:
        """Returns (x, y, w, h) of best match or None."""
        thr = threshold if threshold is not None else self.threshold
        img = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        tpl = cv2.imread(template_path,   cv2.IMREAD_GRAYSCALE)
        if img is None or tpl is None:
            return None
        result = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val >= thr:
            th, tw = tpl.shape[:2]
            return (max_loc[0], max_loc[1], tw, th)
        return None

    # ── all non-overlapping matches ───────────────────────────────────────────
    def find_all_images(self, screenshot_path: str, template_path: str,
                        threshold: float = None) -> list:
        """Returns list of (x, y, w, h)."""
        thr = threshold if threshold is not None else self.threshold
        img = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        tpl = cv2.imread(template_path,   cv2.IMREAD_GRAYSCALE)
        if img is None or tpl is None:
            return []
        result = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
        th, tw = tpl.shape[:2]
        locs = np.where(result >= thr)
        points = list(zip(*locs[::-1]))   # (x, y) pairs
        filtered: list[tuple] = []
        for x, y in points:
            cx, cy = x + tw // 2, y + th // 2
            if all(abs(cx - (fx + fw // 2)) > tw // 2 or
                   abs(cy - (fy + fh // 2)) > th // 2
                   for fx, fy, fw, fh in filtered):
                filtered.append((int(x), int(y), tw, th))
        return filtered

    # ── helpers ───────────────────────────────────────────────────────────────
    def get_center(self, location: tuple) -> tuple[int, int]:
        x, y, w, h = location
        return x + w // 2, y + h // 2

    def get_similarity_at_location(self, screenshot_path: str,
                                   template_path: str,
                                   location: tuple) -> float:
        """Return match score at the given (x, y, w, h) location."""
        img = cv2.imread(screenshot_path, cv2.IMREAD_GRAYSCALE)
        tpl = cv2.imread(template_path,   cv2.IMREAD_GRAYSCALE)
        if img is None or tpl is None:
            return 0.0
        result = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
        x, y = location[0], location[1]
        if 0 <= y < result.shape[0] and 0 <= x < result.shape[1]:
            return float(result[y, x])
        return 0.0

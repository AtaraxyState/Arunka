"""
debug_sky.py — OCR diagnostic for the skystone counter.

Saves:
  debug_sky_full.png        full screenshot with ROI rectangles drawn
  debug_sky_roi_current.png current ROI crop (raw)
  debug_sky_roi_gray.png    grayscale
  debug_sky_roi_scaled.png  3× upscaled
  debug_sky_roi_inv.png     inverted
  debug_sky_roi_thresh.png  final binary threshold fed to Tesseract

Also sweeps a grid of candidate horizontal ranges so you can see which
column slice actually contains the skystone number.
"""

import cv2
import numpy as np
import pytesseract
import re

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from bot.window import find_window, capture_window

# ── Capture ──────────────────────────────────────────────────────────────────
hwnd   = find_window("")
screen = capture_window(hwnd)
h, w   = screen.shape[:2]
print(f"\nScreen: {w}x{h}")

# ── Helper: run OCR on a crop ────────────────────────────────────────────────
def ocr_crop(crop, label=""):
    gray  = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    large = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    inv   = cv2.bitwise_not(large)
    _, th = cv2.threshold(inv, 50, 255, cv2.THRESH_BINARY)
    text  = pytesseract.image_to_string(
        th, config="--psm 7 -c tessedit_char_whitelist=0123456789,"
    ).strip()
    nums  = [int(n.replace(",","")) for n in re.findall(r"\d[\d,]+", text)]
    candidates = [n for n in nums if 100 <= n <= 999_999]
    result = candidates[0] if candidates else None
    if label:
        print(f"  {label:30s} → raw: {repr(text):20s}  parsed: {result}")
    return result, th

# ── 1. Current ROI (as used in _read_skystone) ───────────────────────────────
print("\n── Current ROI (w*0.37 : w*0.52, h*0.07) ──")
x0c = int(w * 0.67); x1c = int(w * 0.80); y1c = int(h * 0.07)
roi_current = screen[0:y1c, x0c:x1c]
cv2.imwrite("debug_sky_roi_current.png", roi_current)

gray_c  = cv2.cvtColor(roi_current, cv2.COLOR_BGR2GRAY)
large_c = cv2.resize(gray_c, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
inv_c   = cv2.bitwise_not(large_c)
_, th_c = cv2.threshold(inv_c, 50, 255, cv2.THRESH_BINARY)
cv2.imwrite("debug_sky_roi_gray.png",   gray_c)
cv2.imwrite("debug_sky_roi_scaled.png", large_c)
cv2.imwrite("debug_sky_roi_inv.png",    inv_c)
cv2.imwrite("debug_sky_roi_thresh.png", th_c)

text_c = pytesseract.image_to_string(
    th_c, config="--psm 6 -c tessedit_char_whitelist=0123456789,"
).strip()
print(f"  Raw OCR text : {repr(text_c)}")
nums_c = [int(n.replace(",","")) for n in re.findall(r"\d[\d,]+", text_c)]
cands_c = [n for n in nums_c if 100 <= n <= 999_999]
print(f"  Skystone candidates: {cands_c}")

# ── 2. Horizontal sweep — find where the skystone number actually lives ───────
print("\n── Horizontal sweep (top 7% of height) ──")
y1 = int(h * 0.07)
sweep_ranges = [
    (0.30, 0.45), (0.35, 0.50), (0.40, 0.55),
    (0.45, 0.60), (0.50, 0.65), (0.55, 0.70),
    (0.60, 0.75), (0.63, 0.76), (0.65, 0.78),
    (0.67, 0.80), (0.70, 0.82), (0.72, 0.84),
]
best_val = None
best_range = None
for (xa, xb) in sweep_ranges:
    x0 = int(w * xa); x1 = int(w * xb)
    crop = screen[0:y1, x0:x1]
    val, _ = ocr_crop(crop, label=f"x={xa:.2f}–{xb:.2f}  ({x0}–{x1}px)")
    if val is not None and best_val is None:
        best_val   = val
        best_range = (xa, xb, x0, x1)

# ── 3. Annotate full screenshot ───────────────────────────────────────────────
vis = screen.copy()
# Current ROI in red
cv2.rectangle(vis, (x0c, 0), (x1c, y1c), (0, 0, 255), 2)
cv2.putText(vis, "CURRENT ROI", (x0c, y1c + 14),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
# Best found range in green
if best_range:
    xa, xb, bx0, bx1 = best_range
    cv2.rectangle(vis, (bx0, 0), (bx1, y1), (0, 220, 80), 2)
    cv2.putText(vis, f"BEST {best_val}", (bx0, y1 + 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 80), 1)
cv2.imwrite("debug_sky_full.png", vis)

# ── 4. Summary ────────────────────────────────────────────────────────────────
print(f"\n── Summary ──")
print(f"  Current ROI result : {cands_c}")
if best_range:
    xa, xb, bx0, bx1 = best_range
    print(f"  Best range found   : w*{xa:.2f} – w*{xb:.2f}  ({bx0}–{bx1}px)  → {best_val}")
    print(f"\n  ➜  Update _read_skystone to use:")
    print(f"       roi = screen[0:int(h*0.07), int(w*{xa}):int(w*{xb})]")
else:
    print("  No skystone number found in any range.")
    print("  Check debug_sky_full.png — the red box shows where we're currently looking.")

print("\nSaved: debug_sky_full.png, debug_sky_roi_current.png,")
print("       debug_sky_roi_gray.png, debug_sky_roi_scaled.png,")
print("       debug_sky_roi_inv.png,  debug_sky_roi_thresh.png")

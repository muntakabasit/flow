#!/usr/bin/env python3
"""Generate Flow PWA icons — amber F on dark navy background."""
import sys
sys.path.insert(0, "/Users/kulturestudios/BelawuOS/dawt_bridge_backend/.venv/lib/python3.9/site-packages")

from PIL import Image, ImageDraw, ImageFont

BG = (8, 9, 12)          # #08090c
ACCENT = (224, 168, 70)   # #e0a846
ACCENT2 = (240, 198, 110) # #f0c66e — gradient highlight

def make_icon(size, out_path):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rect background
    pad = int(size * 0.06)
    radius = int(size * 0.18)
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=radius,
        fill=BG,
    )

    # Subtle inner glow/border
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=radius,
        outline=(30, 34, 48),
        width=max(1, size // 128),
    )

    # Draw "F" letterform — using a bold system font
    font_size = int(size * 0.52)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/SFCompact-Bold.otf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    letter = "F"
    bbox = draw.textbbox((0, 0), letter, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = (size - th) / 2 - bbox[1] - size * 0.02  # slight upward offset

    # Draw the letter with amber color
    draw.text((tx, ty), letter, fill=ACCENT, font=font)

    # Add a small accent bar under the F (like a sound wave indicator)
    bar_w = int(size * 0.28)
    bar_h = max(2, int(size * 0.025))
    bar_x = (size - bar_w) // 2
    bar_y = int(size * 0.72)
    bar_radius = bar_h // 2
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
        radius=bar_radius,
        fill=ACCENT2,
    )

    # Two smaller bars flanking (wave pattern)
    small_w = int(size * 0.12)
    small_h = max(2, int(size * 0.02))
    # left
    draw.rounded_rectangle(
        [bar_x - int(size * 0.03) - small_w, bar_y + (bar_h - small_h) // 2,
         bar_x - int(size * 0.03), bar_y + (bar_h - small_h) // 2 + small_h],
        radius=small_h // 2,
        fill=(*ACCENT2, 140),
    )
    # right
    draw.rounded_rectangle(
        [bar_x + bar_w + int(size * 0.03), bar_y + (bar_h - small_h) // 2,
         bar_x + bar_w + int(size * 0.03) + small_w, bar_y + (bar_h - small_h) // 2 + small_h],
        radius=small_h // 2,
        fill=(*ACCENT2, 140),
    )

    img.save(out_path, "PNG")
    print(f"  -> {out_path} ({size}x{size})")


if __name__ == "__main__":
    out_dir = "/Users/kulturestudios/BelawuOS/flow/static"
    print("Generating Flow icons...")
    make_icon(192, f"{out_dir}/icon-192.png")
    make_icon(512, f"{out_dir}/icon-512.png")
    print("Done!")

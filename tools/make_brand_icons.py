"""Make icon.ico and logo.png for a brand from its logo-source image.

Dev-only (needs Pillow): python tools/make_brand_icons.py brands/spider-team
"""

import os
import sys

from PIL import Image

ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
LOGO_SIZE = 72  # shown on the dashboard


def main(folder):
    src = next(os.path.join(folder, f) for f in sorted(os.listdir(folder))
               if f.startswith("logo-source."))
    img = Image.open(src).convert("RGBA")
    side = min(img.size)  # centre square crop
    left, top = (img.width - side) // 2, (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img.save(os.path.join(folder, "icon.ico"), sizes=ICO_SIZES)
    img.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS).save(os.path.join(folder, "logo.png"))
    print("wrote icon.ico and logo.png in", folder)


if __name__ == "__main__":
    main(sys.argv[1])

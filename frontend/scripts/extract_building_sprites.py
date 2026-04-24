from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

SOURCE_IMAGE = Path("buildings.png")
OUTPUT_DIR = Path("frontend/public/assets/buildings")
GRID_COLUMNS = 6
GRID_ROWS = 10
MASK_THRESHOLD = 245
MIN_FOREGROUND_PIXELS = 180
INNER_MARGIN = 8
PADDING = 3


def to_transparent(crop: Image.Image) -> Image.Image:
    rgba = crop.convert("RGBA")
    data = np.array(rgba)
    white_mask = np.all(data[:, :, :3] >= MASK_THRESHOLD, axis=2)
    data[white_mask, 3] = 0
    return Image.fromarray(data)


def main() -> None:
    if not SOURCE_IMAGE.exists():
        raise FileNotFoundError(f"Missing source image: {SOURCE_IMAGE}")

    image = Image.open(SOURCE_IMAGE).convert("RGB")
    pixels = np.array(image)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUTPUT_DIR.glob("building_*.png"):
        old.unlink()

    index = 1
    for row in range(GRID_ROWS):
        top = round(row * image.height / GRID_ROWS)
        bottom = round((row + 1) * image.height / GRID_ROWS)
        for col in range(GRID_COLUMNS):
            left = round(col * image.width / GRID_COLUMNS)
            right = round((col + 1) * image.width / GRID_COLUMNS)

            cell = pixels[top:bottom, left:right]
            if cell.size == 0:
                continue

            inner = cell[INNER_MARGIN : max(INNER_MARGIN, cell.shape[0] - INNER_MARGIN), INNER_MARGIN : max(INNER_MARGIN, cell.shape[1] - INNER_MARGIN)]
            if inner.size == 0:
                continue

            mask = np.any(inner < MASK_THRESHOLD, axis=2)
            if int(mask.sum()) < MIN_FOREGROUND_PIXELS:
                continue

            ys, xs = np.where(mask)
            min_x = int(xs.min()) + INNER_MARGIN
            max_x = int(xs.max()) + INNER_MARGIN
            min_y = int(ys.min()) + INNER_MARGIN
            max_y = int(ys.max()) + INNER_MARGIN

            crop_left = max(0, min_x - PADDING)
            crop_top = max(0, min_y - PADDING)
            crop_right = min(cell.shape[1], max_x + PADDING + 1)
            crop_bottom = min(cell.shape[0], max_y + PADDING + 1)

            crop = Image.fromarray(cell[crop_top:crop_bottom, crop_left:crop_right])
            transparent = to_transparent(crop)
            out_path = OUTPUT_DIR / f"building_{index:02d}.png"
            transparent.save(out_path)
            index += 1

    print(f"Saved {index - 1} building sprites to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

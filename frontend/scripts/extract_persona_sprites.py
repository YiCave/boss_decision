from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

SOURCE_IMAGE = Path("pixel character.jpeg")
OUTPUT_DIR = Path("frontend/public/assets/personas")
MASK_THRESHOLD = 245
MIN_COMPONENT_PIXELS = 30
PADDING = 2


def connected_components(mask: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    boxes: list[tuple[int, int, int, int, int]] = []

    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue
            queue: deque[tuple[int, int]] = deque([(y, x)])
            visited[y, x] = True
            min_x = max_x = x
            min_y = max_y = y
            count = 0

            while queue:
                cy, cx = queue.popleft()
                count += 1
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)

                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if ny < 0 or nx < 0 or ny >= height or nx >= width:
                        continue
                    if visited[ny, nx] or not mask[ny, nx]:
                        continue
                    visited[ny, nx] = True
                    queue.append((ny, nx))

            if count > MIN_COMPONENT_PIXELS:
                boxes.append((min_x, min_y, max_x, max_y, count))

    return boxes


def cluster_rows(boxes: list[tuple[int, int, int, int, int]], max_gap: int = 40) -> list[list[tuple[int, int, int, int, int]]]:
    ordered = sorted(boxes, key=lambda item: (item[1], item[0]))
    rows: list[list[tuple[int, int, int, int, int]]] = []

    for box in ordered:
        if not rows:
            rows.append([box])
            continue
        last_row = rows[-1]
        row_y = sum(item[1] for item in last_row) / len(last_row)
        if abs(box[1] - row_y) <= max_gap:
            last_row.append(box)
        else:
            rows.append([box])

    for row in rows:
        row.sort(key=lambda item: item[0])

    return rows


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
    mask = np.any(pixels < MASK_THRESHOLD, axis=2)

    boxes = connected_components(mask)
    rows = cluster_rows(boxes)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    index = 1
    for row in rows:
        for min_x, min_y, max_x, max_y, _ in row:
            left = max(0, min_x - PADDING)
            top = max(0, min_y - PADDING)
            right = min(image.width, max_x + PADDING + 1)
            bottom = min(image.height, max_y + PADDING + 1)

            crop = image.crop((left, top, right, bottom))
            transparent = to_transparent(crop)
            out_path = OUTPUT_DIR / f"persona_{index:02d}.png"
            transparent.save(out_path)
            index += 1

    print(f"Saved {index - 1} sprites to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

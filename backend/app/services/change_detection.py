from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError


class InvalidImageError(ValueError):
    pass


def validate_image(path: Path) -> None:
    try:
        with Image.open(path) as image:
            image.verify()
            if image.format not in {"PNG", "JPEG", "WEBP"}:
                raise InvalidImageError("Only PNG, JPEG, and WebP images are supported")
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("Uploaded file is not a valid image") from exc


def compare_images(before_path: Path, after_path: Path) -> tuple[dict[str, Any], np.ndarray]:
    before = cv2.imread(str(before_path), cv2.IMREAD_GRAYSCALE)
    after = cv2.imread(str(after_path), cv2.IMREAD_GRAYSCALE)
    if before is None or after is None:
        raise InvalidImageError("Could not decode one of the uploaded images")
    height, width = before.shape
    if after.shape != before.shape:
        after = cv2.resize(after, (width, height), interpolation=cv2.INTER_AREA)
    difference = cv2.absdiff(before, after)
    _, mask = cv2.threshold(difference, 30, 255, cv2.THRESH_BINARY)
    changed_pixels = int(cv2.countNonZero(mask))
    total_pixels = int(width * height)
    count, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    components = [
        {
            "x": int(stats[index, cv2.CC_STAT_LEFT]),
            "y": int(stats[index, cv2.CC_STAT_TOP]),
            "width": int(stats[index, cv2.CC_STAT_WIDTH]),
            "height": int(stats[index, cv2.CC_STAT_HEIGHT]),
            "area_pixels": int(stats[index, cv2.CC_STAT_AREA]),
        }
        for index in range(1, count)
        if stats[index, cv2.CC_STAT_AREA] >= 16
    ]
    components.sort(key=lambda item: item["area_pixels"], reverse=True)
    regions = [{"id": f"REG-{index:03d}", **component} for index, component in enumerate(components[:100], start=1)]
    color = cv2.imread(str(after_path), cv2.IMREAD_COLOR)
    if color is None:
        raise InvalidImageError("Could not decode the latest image for annotation")
    if color.shape[:2] != before.shape:
        color = cv2.resize(color, (width, height), interpolation=cv2.INTER_AREA)
    tint = color.copy()
    tint[mask > 0] = (45, 65, 235)
    annotated = cv2.addWeighted(color, 0.72, tint, 0.28, 0)
    for region in regions:
        x, y, box_width, box_height = region["x"], region["y"], region["width"], region["height"]
        cv2.rectangle(annotated, (x, y), (x + box_width, y + box_height), (100, 255, 55), 2)
        label_y = max(14, y - 4)
        cv2.putText(annotated, region["id"], (x, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 55), 1, cv2.LINE_AA)
    percent = changed_pixels / total_pixels * 100
    metrics = {
        "changed_percent": round(percent, 2),
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "image_width": int(width),
        "image_height": int(height),
        "changed_regions": len(regions),
        "regions": regions,
        "summary": f"Detected {percent:.2f}% pixel-level change across {len(regions)} significant region(s).",
    }
    return metrics, annotated

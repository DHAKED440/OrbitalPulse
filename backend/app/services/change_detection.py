from pathlib import Path

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


def compare_images(before_path: Path, after_path: Path) -> dict[str, int | float | str]:
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
    regions = sum(1 for area in stats[1:, cv2.CC_STAT_AREA] if area >= 16)
    percent = changed_pixels / total_pixels * 100
    return {
        "changed_percent": round(percent, 2),
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "changed_regions": regions,
        "summary": f"Detected {percent:.2f}% pixel-level change across {regions} significant region(s).",
    }

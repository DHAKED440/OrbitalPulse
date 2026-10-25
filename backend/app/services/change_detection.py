from __future__ import annotations

import base64
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


class InvalidImageError(ValueError):
    pass


def validate_image(path: Path, *, max_dimension: int = 10_000, max_pixels: int = 40_000_000) -> None:
    try:
        with Image.open(path) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"}:
                raise InvalidImageError("Only PNG, JPEG, and WebP images are supported")
            width, height = image.size
            if width < 1 or height < 1 or width > max_dimension or height > max_dimension:
                raise InvalidImageError(f"Image dimensions must be between 1 and {max_dimension} pixels per side")
            if width * height > max_pixels:
                raise InvalidImageError(f"Image exceeds the {max_pixels:,}-pixel limit")
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidImageError("Uploaded file is not a valid image") from exc


def _decode_image(path: Path) -> np.ndarray:
    try:
        with Image.open(path) as image:
            rgb = np.asarray(ImageOps.exif_transpose(image).convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise InvalidImageError("Could not decode one of the uploaded images") from exc


def _resize_working(image: np.ndarray, width: int, height: int) -> np.ndarray:
    interpolation = cv2.INTER_AREA if image.shape[1] > width or image.shape[0] > height else cv2.INTER_CUBIC
    return cv2.resize(image, (width, height), interpolation=interpolation)


def _gray(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)


def _gray_raw(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _normalize_appearance(before_gray: np.ndarray, after_gray: np.ndarray, valid_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Match robust grayscale percentiles before local contrast normalization."""
    valid = valid_mask > 0
    reference = before_gray[valid]
    moving = after_gray[valid]
    if not reference.size or not moving.size:
        return before_gray, after_gray
    before_low, before_high = np.percentile(reference, (2, 98))
    after_low, after_high = np.percentile(moving, (2, 98))
    if before_high - before_low < 1 or after_high - after_low < 1:
        return before_gray, after_gray
    scale = (before_high - before_low) / max(after_high - after_low, 1.0)
    normalized_after = np.clip((after_gray.astype(np.float32) - after_low) * scale + before_low, 0, 255).astype(np.uint8)
    return before_gray, normalized_after


def _structural_difference(before_gray: np.ndarray, after_gray: np.ndarray) -> np.ndarray:
    """Return a local-SSIM dissimilarity map in the 0..255 range."""
    before = before_gray.astype(np.float32)
    after = after_gray.astype(np.float32)
    mu_before = cv2.GaussianBlur(before, (7, 7), 1.5)
    mu_after = cv2.GaussianBlur(after, (7, 7), 1.5)
    mu_before_sq, mu_after_sq = mu_before * mu_before, mu_after * mu_after
    covariance = cv2.GaussianBlur(before * after, (7, 7), 1.5) - mu_before * mu_after
    variance_before = cv2.GaussianBlur(before * before, (7, 7), 1.5) - mu_before_sq
    variance_after = cv2.GaussianBlur(after * after, (7, 7), 1.5) - mu_after_sq
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    numerator = (2 * mu_before * mu_after + c1) * (2 * covariance + c2)
    denominator = (mu_before_sq + mu_after_sq + c1) * (variance_before + variance_after + c2)
    similarity = numerator / np.maximum(denominator, 1e-6)
    return np.clip((1.0 - similarity) * 127.5, 0, 255).astype(np.uint8)


def _estimate_registration(before: np.ndarray, after: np.ndarray) -> tuple[np.ndarray | None, str]:
    """Estimate a homography mapping after-image coordinates into the before image."""
    before_gray, after_gray = _gray(before), _gray(after)
    detector = cv2.ORB_create(nfeatures=3500, scaleFactor=1.2, nlevels=8, fastThreshold=10)
    key_before, desc_before = detector.detectAndCompute(before_gray, None)
    key_after, desc_after = detector.detectAndCompute(after_gray, None)
    if desc_before is None or desc_after is None or len(key_before) < 8 or len(key_after) < 8:
        return None, "orb"

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(desc_after, desc_before, k=2)
    good = [first for pair in pairs if len(pair) == 2 for first, second in [pair] if first.distance < 0.75 * second.distance]
    if len(good) < 8:
        return None, "orb"

    after_points = np.float32([key_after[match.queryIdx].pt for match in good]).reshape(-1, 1, 2)
    before_points = np.float32([key_before[match.trainIdx].pt for match in good]).reshape(-1, 1, 2)
    homography, inliers = cv2.findHomography(after_points, before_points, cv2.RANSAC, 3.0, maxIters=3000, confidence=0.995)
    if homography is None or inliers is None or not np.isfinite(homography).all():
        return None, "orb"
    inlier_count = int(inliers.sum())
    if inlier_count < 10 or inlier_count / len(good) < 0.25:
        return None, "orb"

    height, width = before.shape[:2]
    inlier_mask = inliers.ravel().astype(bool)
    src_inliers = after_points.reshape(-1, 2)[inlier_mask]
    dst_inliers = before_points.reshape(-1, 2)[inlier_mask]
    for points in (src_inliers, dst_inliers):
        spread = np.ptp(points, axis=0)
        if spread[0] < width * 0.15 or spread[1] < height * 0.15:
            return None, "orb"

    normalized_h = homography / homography[2, 2] if abs(homography[2, 2]) > 1e-10 else homography
    if abs(np.linalg.det(normalized_h)) < 1e-10 or np.linalg.cond(normalized_h) > 1e12:
        return None, "orb"
    projected = cv2.perspectiveTransform(src_inliers.reshape(-1, 1, 2), homography).reshape(-1, 2)
    residuals = np.linalg.norm(projected - dst_inliers, axis=1)
    if not np.isfinite(residuals).all() or np.percentile(residuals, 90) > 3.5:
        return None, "orb"

    corners = np.float32([[[0, 0]], [[width - 1, 0]], [[width - 1, height - 1]], [[0, height - 1]]])
    projected_corners = cv2.perspectiveTransform(corners, homography).reshape(-1, 2)
    contour = projected_corners.astype(np.float32).reshape(-1, 1, 2)
    if not np.isfinite(projected_corners).all() or not cv2.isContourConvex(contour):
        return None, "orb"
    projected_area = abs(cv2.contourArea(contour))
    area_ratio = projected_area / max(width * height, 1)
    if not 0.5 <= area_ratio <= 2.0:
        return None, "orb"

    valid = np.full((height, width), 255, dtype=np.uint8)
    warped_valid = cv2.warpPerspective(valid, homography, (width, height), flags=cv2.INTER_NEAREST)
    if cv2.countNonZero(warped_valid) < width * height * 0.55:
        return None, "orb"
    return normalized_h.astype(np.float64), "orb"


def _preview_data_url(image: np.ndarray, *, quality: int = 86) -> str:
    height, width = image.shape[:2]
    scale = min(1.0, 1400 / max(width, height))
    if scale < 1.0:
        image = cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("Could not encode the analysis preview")
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")


def compare_images(
    before_path: Path,
    after_path: Path,
    *,
    max_working_dimension: int = 2048,
    threshold: int = 38,
    min_region_area: int = 24,
    min_region_percent: float = 0.0001,
    comparison_mode: str = "registered",
) -> dict[str, object]:
    """Compare an image pair and return pixel metrics plus visual previews.

    ORB/RANSAC registration is attempted in ``registered`` mode. Invalid
    transformations are rejected before warping. ``original`` mode deliberately
    skips registration and photometric normalization, preserving appearance
    evidence while resizing to a compatible grid. Pixel coordinates are
    relative to the before image.
    """
    if comparison_mode not in {"registered", "original"}:
        raise ValueError("comparison_mode must be 'registered' or 'original'")
    started = time.perf_counter()
    before_original = _decode_image(before_path)
    after_original = _decode_image(after_path)
    before_height, before_width = before_original.shape[:2]
    after_height, after_width = after_original.shape[:2]

    scale = min(1.0, max_working_dimension / max(before_width, before_height))
    work_width = max(1, round(before_width * scale))
    work_height = max(1, round(before_height * scale))
    before = _resize_working(before_original, work_width, work_height) if (work_width, work_height) != (before_width, before_height) else before_original.copy()
    after_resized = _resize_working(after_original, work_width, work_height)

    warnings: list[str] = []
    if comparison_mode == "original":
        homography, registration_method = None, "none"
        aligned_after = after_resized
        valid_mask = np.full((work_height, work_width), 255, dtype=np.uint8)
        registration_status = "not_attempted"
        warnings.append("Original comparison mode skipped image registration and appearance normalization.")
    else:
        if np.array_equal(before, after_resized):
            homography, registration_method = np.eye(3, dtype=np.float64), "identity"
        else:
            homography, registration_method = _estimate_registration(before, after_resized)
        height, width = before.shape[:2]
        if homography is None:
            aligned_after = after_resized
            valid_mask = np.full((height, width), 255, dtype=np.uint8)
            registration_status = "fallback_unregistered"
            warnings.append("Image registration failed validation; resized images were compared without geometric alignment.")
        else:
            aligned_after = cv2.warpPerspective(after_resized, homography, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            valid_mask = cv2.warpPerspective(np.full((height, width), 255, dtype=np.uint8), homography, (width, height), flags=cv2.INTER_NEAREST)
            registration_status = "registered"

    height, width = before.shape[:2]
    before_gray_raw, after_gray_raw = _gray_raw(before), _gray_raw(aligned_after)
    if comparison_mode == "registered":
        before_gray_raw, after_gray_normalized = _normalize_appearance(before_gray_raw, after_gray_raw, valid_mask)
        before_gray, after_gray = _gray(before_gray_raw), _gray(after_gray_normalized)
    else:
        before_gray, after_gray = before_gray_raw, after_gray_raw
    before_smooth = cv2.GaussianBlur(before_gray, (5, 5), 0)
    after_smooth = cv2.GaussianBlur(after_gray, (5, 5), 0)
    intensity_difference = cv2.absdiff(before_smooth, after_smooth)
    before_edges = cv2.Canny(before_smooth, 50, 140)
    after_edges = cv2.Canny(after_smooth, 50, 140)
    edge_difference = cv2.absdiff(before_edges, after_edges)
    structural_difference = _structural_difference(before_smooth, after_smooth)
    combined_difference = cv2.addWeighted(intensity_difference, 0.62, structural_difference, 0.28, 0)
    combined_difference = cv2.addWeighted(combined_difference, 0.9, edge_difference, 0.1, 0)
    _, binary = cv2.threshold(combined_difference, threshold, 255, cv2.THRESH_BINARY)
    binary = cv2.bitwise_and(binary, valid_mask)

    open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, open_kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, close_kernel)
    cleaned = cv2.bitwise_and(cleaned, valid_mask)

    label_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
    filtered_mask = np.zeros_like(cleaned)
    working_valid_pixels = int(cv2.countNonZero(valid_mask))
    area_threshold = max(min_region_area, int(np.ceil(min_region_percent * working_valid_pixels)))
    before_lab = cv2.cvtColor(before, cv2.COLOR_BGR2LAB)
    after_lab = cv2.cvtColor(aligned_after, cv2.COLOR_BGR2LAB)
    regions_work: list[dict[str, object]] = []
    for label in range(1, label_count):
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        region_width = int(stats[label, cv2.CC_STAT_WIDTH])
        region_height = int(stats[label, cv2.CC_STAT_HEIGHT])
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < area_threshold:
            continue
        filtered_mask[labels == label] = 255
        component_mask = labels == label
        component_pixels = int(np.count_nonzero(component_mask))
        edge_changed = int(np.count_nonzero((edge_difference > threshold) & component_mask))
        before_values = before_gray_raw[component_mask].astype(np.float32)
        after_values = after_gray_raw[component_mask].astype(np.float32)
        before_spread, after_spread = float(before_values.std()), float(after_values.std())
        texture_score = min(1.0, abs(before_spread - after_spread) / max(before_spread, after_spread, 1.0))
        color_delta = before_lab[component_mask].astype(np.float32) - after_lab[component_mask].astype(np.float32)
        color_delta[:, 0] *= 100.0 / 255.0
        color_score = min(100.0, float(np.linalg.norm(color_delta, axis=1).mean()))
        regions_work.append({
            "x": x,
            "y": y,
            "width": region_width,
            "height": region_height,
            "area": area,
            "edge_change_percent": edge_changed / component_pixels * 100 if component_pixels else 0.0,
            "texture_change_score": texture_score,
            "color_change_score": color_score,
        })

    working_changed_pixels = int(cv2.countNonZero(filtered_mask))
    area_scale = (before_width / work_width) * (before_height / work_height)
    total_pixels = max(1, round(working_valid_pixels * area_scale))
    changed_pixels = round(working_changed_pixels * area_scale)
    changed_percent = changed_pixels / total_pixels * 100 if total_pixels else 0.0

    regions = []
    for index, region in enumerate(sorted(regions_work, key=lambda item: (item["y"], item["x"])), start=1):
        region_area = round(int(region["area"]) * area_scale)
        region_percent = region_area / total_pixels * 100 if total_pixels else 0.0
        size_category = "small" if region_percent < 0.1 else "medium" if region_percent < 1.0 else "large"
        source_x = round(int(region["x"]) * before_width / work_width)
        source_y = round(int(region["y"]) * before_height / work_height)
        source_width = min(before_width - source_x, max(1, round(int(region["width"]) * before_width / work_width)))
        source_height = min(before_height - source_y, max(1, round(int(region["height"]) * before_height / work_height)))
        regions.append({
            "region_id": f"region-{index:03d}",
            "x": source_x,
            "y": source_y,
            "width": source_width,
            "height": source_height,
            "area": region_area,
            "percent_of_valid_area": round(region_percent, 4),
            "size_category": size_category,
            "indicators": {
                "edge_change_percent": round(float(region["edge_change_percent"]), 2),
                "texture_change_score": round(float(region["texture_change_score"]), 3),
                "color_change_score": round(float(region["color_change_score"]), 2),
            },
        })

    overlay = cv2.addWeighted(before, 0.5, aligned_after, 0.5, 0)
    for region in regions_work:
        # The overlay is drawn on the working-resolution images, so use the
        # same coordinates as connected components (before scaling API boxes).
        x, y = int(region["x"]), int(region["y"])
        x2, y2 = x + int(region["width"]), y + int(region["height"])
        cv2.rectangle(overlay, (x, y), (x2, y2), (0, 220, 255), 2)

    heatmap = cv2.applyColorMap(filtered_mask, cv2.COLORMAP_TURBO)
    heatmap[valid_mask == 0] = 0
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    summary = f"Detected {len(regions)} changed region(s) across {changed_percent:.2f}% of the valid comparison area."
    if registration_status == "fallback_unregistered":
        summary += " Images were compared without registration."

    detection_method = (
        "ORB/RANSAC registration, robust percentile brightness/contrast normalization, "
        "local SSIM plus intensity and edge differences, morphology, and connected-component filtering."
        if comparison_mode == "registered"
        else "Original appearance comparison on a resized common grid using SSIM, intensity and edge differences, morphology, and connected-component filtering."
    )

    return {
        "changed_percent": round(changed_percent, 2),
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "changed_regions": len(regions),
        "regions": regions,
        "image_dimensions": {
            "before": {"width": before_width, "height": before_height},
            "after": {"width": after_width, "height": after_height},
            "comparison": {"width": width, "height": height},
        },
        "registration_status": registration_status,
        "registration_method": registration_method,
        "comparison_mode": comparison_mode,
        "detection_method": detection_method,
        "warnings": warnings,
        "processing_duration_ms": duration_ms,
        "annotated_preview": _preview_data_url(overlay),
        "difference_preview": _preview_data_url(heatmap),
        "summary": summary,
    }

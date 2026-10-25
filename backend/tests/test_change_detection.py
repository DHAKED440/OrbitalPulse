import cv2
import numpy as np
import pytest

from app.services.change_detection import InvalidImageError, _estimate_registration, compare_images


def textured_scene(seed=19, size=256):
    rng = np.random.default_rng(seed)
    noise = rng.integers(0, 256, (size, size, 3), dtype=np.uint8)
    scene = cv2.GaussianBlur(noise, (5, 5), 0)
    for x in range(18, size - 15, 38):
        cv2.rectangle(scene, (x, 20), (x + 19, 39), (35, 150, 80), -1)
    cv2.line(scene, (12, size // 2), (size - 12, size // 2), (240, 90, 20), 3)
    return scene


def compare(tmp_path, before_image, after_image, **kwargs):
    before, after = tmp_path / "before.png", tmp_path / "after.png"
    assert cv2.imwrite(str(before), before_image)
    assert cv2.imwrite(str(after), after_image)
    return compare_images(before, after, **kwargs)


def box_iou(box, target):
    x1 = max(box["x"], target[0])
    y1 = max(box["y"], target[1])
    x2 = min(box["x"] + box["width"], target[0] + target[2])
    y2 = min(box["y"] + box["height"], target[1] + target[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = box["width"] * box["height"] + target[2] * target[3] - intersection
    return intersection / union if union else 0.0


def test_identical_images_have_no_pixel_change(tmp_path):
    scene = textured_scene()

    result = compare(tmp_path, scene, scene.copy())

    assert result["changed_pixels"] == 0
    assert result["changed_percent"] == 0
    assert result["registration_status"] == "registered"
    assert result["registration_method"] == "identity"
    assert result["regions"] == []
    assert result["annotated_preview"].startswith("data:image/jpeg;base64,")
    assert result["difference_preview"].startswith("data:image/jpeg;base64,")


def test_added_rectangular_region_is_detected_in_expected_location(tmp_path):
    before = textured_scene()
    after = before.copy()
    cv2.rectangle(after, (90, 92), (144, 139), (255, 255, 255), -1)

    result = compare(tmp_path, before, after)

    assert result["changed_regions"] >= 1
    assert 2.0 < result["changed_percent"] < 12.0
    target = max(result["regions"], key=lambda region: box_iou(region, (90, 92, 55, 48)))
    assert box_iou(target, (90, 92, 55, 48)) > 0.45
    assert target["area"] > 1000
    assert set(target) == {
        "region_id", "x", "y", "width", "height", "area", "percent_of_valid_area", "size_category", "indicators"
    }
    assert target["region_id"].startswith("region-")
    assert target["indicators"]["color_change_score"] >= 0
    assert abs(sum(region["area"] for region in result["regions"]) - result["changed_pixels"]) <= len(result["regions"])
    assert abs(sum(region["percent_of_valid_area"] for region in result["regions"]) - result["changed_percent"]) < 0.02


def test_removed_rectangular_region_is_detected(tmp_path):
    before = textured_scene()
    cv2.rectangle(before, (76, 80), (132, 135), (240, 240, 240), -1)
    after = textured_scene()

    result = compare(tmp_path, before, after)

    assert result["changed_regions"] >= 1
    assert result["changed_pixels"] > 1000
    assert any(region["x"] < 132 and region["x"] + region["width"] > 76 for region in result["regions"])


def test_small_noisy_differences_are_filtered(tmp_path):
    before = textured_scene()
    after = before.copy()
    rng = np.random.default_rng(3)
    ys = rng.integers(0, 256, 80)
    xs = rng.integers(0, 256, 80)
    after[ys, xs] = np.clip(after[ys, xs].astype(np.int16) + 2, 0, 255).astype(np.uint8)

    result = compare(tmp_path, before, after, min_region_area=40)

    assert result["changed_pixels"] == 0
    assert result["changed_regions"] == 0


def test_brightness_and_contrast_change_is_normalized(tmp_path):
    before = textured_scene()
    after = cv2.convertScaleAbs(before, alpha=0.72, beta=36)

    result = compare(tmp_path, before, after)

    assert result["changed_percent"] < 1.0
    assert result["changed_regions"] == 0


def test_minor_translation_is_registered_without_a_false_event(tmp_path):
    before = textured_scene()
    shifted = cv2.warpAffine(
        before,
        np.float32([[1, 0, 2], [0, 1, -2]]),
        (before.shape[1], before.shape[0]),
        borderMode=cv2.BORDER_REFLECT,
    )

    result = compare(tmp_path, before, shifted)

    assert result["registration_status"] == "registered"
    assert result["changed_percent"] < 1.0
    assert result["changed_regions"] == 0


def test_different_dimensions_are_registered_and_metrics_use_before_coordinates(tmp_path):
    before = textured_scene()
    after = before.copy()
    cv2.rectangle(after, (96, 104), (146, 154), (255, 255, 255), -1)
    larger_after = cv2.resize(after, (320, 320), interpolation=cv2.INTER_CUBIC)

    result = compare(tmp_path, before, larger_after)

    assert result["image_dimensions"]["before"] == {"width": 256, "height": 256}
    assert result["image_dimensions"]["after"] == {"width": 320, "height": 320}
    assert result["changed_regions"] >= 1
    assert result["changed_percent"] > 1
    assert any(
        region["x"] < 146
        and region["x"] + region["width"] > 96
        and region["y"] < 154
        and region["y"] + region["height"] > 104
        for region in result["regions"]
    )


def test_registration_failure_uses_unregistered_fallback_and_warning(tmp_path):
    before = np.zeros((128, 128, 3), dtype=np.uint8)
    after = before.copy()
    cv2.rectangle(after, (40, 42), (80, 82), (255, 255, 255), -1)

    result = compare(tmp_path, before, after)

    assert result["registration_status"] == "fallback_unregistered"
    assert result["warnings"]
    assert "without geometric alignment" in result["warnings"][0]
    assert result["changed_regions"] >= 1


def test_original_mode_skips_registration_and_photometric_normalization(tmp_path):
    before = textured_scene()
    after = cv2.convertScaleAbs(before, alpha=0.75, beta=25)

    result = compare(tmp_path, before, after, comparison_mode="original")

    assert result["comparison_mode"] == "original"
    assert result["registration_status"] == "not_attempted"
    assert result["registration_method"] == "none"
    assert result["warnings"]


def test_singular_registration_transform_is_rejected(monkeypatch):
    scene = textured_scene()
    called = False

    def invalid_homography(source, destination, *args, **kwargs):
        nonlocal called
        called = True
        return np.zeros((3, 3), dtype=np.float64), np.ones((len(source), 1), dtype=np.uint8)

    monkeypatch.setattr(cv2, "findHomography", invalid_homography)
    homography, _method = _estimate_registration(scene, scene.copy())

    assert called
    assert homography is None


def test_corrupted_image_raises_a_safe_validation_error(tmp_path):
    before, after = tmp_path / "before.png", tmp_path / "after.png"
    before.write_bytes(b"corrupted image")
    cv2.imwrite(str(after), textured_scene())

    with pytest.raises(InvalidImageError, match="Could not decode"):
        compare_images(before, after)

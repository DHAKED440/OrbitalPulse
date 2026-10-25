import cv2
import numpy as np

from app.services.change_detection import compare_images


def test_identical_images_have_no_pixel_change(tmp_path):
    image = np.zeros((32, 32), dtype=np.uint8)
    before, after = tmp_path / "before.png", tmp_path / "after.png"
    cv2.imwrite(str(before), image)
    cv2.imwrite(str(after), image)

    result, annotated = compare_images(before, after)

    assert result["changed_pixels"] == 0
    assert result["changed_percent"] == 0
    assert result["regions"] == []
    assert annotated.shape == (32, 32, 3)


def test_detects_and_bounds_a_changed_region(tmp_path):
    before_image = np.zeros((40, 50, 3), dtype=np.uint8)
    after_image = before_image.copy()
    after_image[10:20, 12:22] = 255
    before, after = tmp_path / "before.png", tmp_path / "after.png"
    cv2.imwrite(str(before), before_image)
    cv2.imwrite(str(after), after_image)

    result, annotated = compare_images(before, after)

    assert result["changed_pixels"] == 100
    assert result["changed_regions"] == 1
    assert result["regions"][0] == {"id": "REG-001", "x": 12, "y": 10, "width": 10, "height": 10, "area_pixels": 100}
    assert annotated.shape == after_image.shape

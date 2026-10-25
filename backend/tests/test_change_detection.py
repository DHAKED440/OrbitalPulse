import cv2
import numpy as np

from app.services.change_detection import compare_images


def test_identical_images_have_no_pixel_change(tmp_path):
    image = np.zeros((32, 32), dtype=np.uint8)
    before, after = tmp_path / "before.png", tmp_path / "after.png"
    cv2.imwrite(str(before), image)
    cv2.imwrite(str(after), image)

    result = compare_images(before, after)

    assert result["changed_pixels"] == 0
    assert result["changed_percent"] == 0

from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings
from app.schemas.analysis import SemanticAnalysis
from app.services.vision import VisionImage, VisionProvider


class VisionInputLimitError(ValueError):
    pass


def _load_rgb(path: Path) -> Image.Image:
    try:
        with Image.open(path) as image:
            return ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise VisionInputLimitError("An image could not be prepared for semantic analysis") from exc


def _encode_jpeg(image: Image.Image, *, max_dimension: int, max_bytes: int) -> bytes:
    image = image.copy()
    image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    for quality in (84, 72, 60):
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True)
        encoded = buffer.getvalue()
        if len(encoded) <= max_bytes:
            return encoded
    raise VisionInputLimitError("Images exceed the configured semantic-analysis size limit")


def _as_vision_image(label: str, encoded: bytes) -> VisionImage:
    data = base64.b64encode(encoded).decode("ascii")
    return VisionImage(label=label, data_url=f"data:image/jpeg;base64,{data}")


def _prepare_images(
    before_path: Path,
    after_path: Path,
    regions: list[dict[str, object]],
    settings: Settings,
    comparison_dimensions: dict[str, object] | None = None,
) -> list[VisionImage]:
    before = _load_rgb(before_path)
    after = _load_rgb(after_path)
    original_before_size = before.size
    common_after = after.resize(original_before_size, Image.Resampling.LANCZOS)
    comparison_width = original_before_size[0]
    comparison_height = original_before_size[1]
    if comparison_dimensions:
        comparison_width = max(1, int(comparison_dimensions.get("width", comparison_width)))
        comparison_height = max(1, int(comparison_dimensions.get("height", comparison_height)))
    scale_x = original_before_size[0] / comparison_width
    scale_y = original_before_size[1] / comparison_height

    images = [
        _as_vision_image(
            "Full before image",
            _encode_jpeg(before, max_dimension=settings.vision_max_image_dimension, max_bytes=settings.vision_max_image_bytes),
        ),
        _as_vision_image(
            "Full after image",
            _encode_jpeg(common_after, max_dimension=settings.vision_max_image_dimension, max_bytes=settings.vision_max_image_bytes),
        ),
    ]

    for region in sorted(regions, key=lambda item: int(item.get("area", 0)), reverse=True)[: settings.vision_max_region_crops]:
        x, y = round(int(region["x"]) * scale_x), round(int(region["y"]) * scale_y)
        width, height = max(1, round(int(region["width"]) * scale_x)), max(1, round(int(region["height"]) * scale_y))
        pad_x, pad_y = max(width // 4, 12), max(height // 4, 12)
        box = (
            max(0, x - pad_x),
            max(0, y - pad_y),
            min(original_before_size[0], x + width + pad_x),
            min(original_before_size[1], y + height + pad_y),
        )
        region_id = str(region.get("region_id", "region"))
        before_crop = before.crop(box)
        after_crop = common_after.crop(box)
        crop_limit = min(settings.vision_max_image_dimension, 768)
        images.append(
            _as_vision_image(
                f"Before crop for {region_id}; common-grid crop for visual context",
                _encode_jpeg(before_crop, max_dimension=crop_limit, max_bytes=settings.vision_max_image_bytes),
            )
        )
        images.append(
            _as_vision_image(
                f"After crop for {region_id}; common-grid crop for visual context",
                _encode_jpeg(after_crop, max_dimension=crop_limit, max_bytes=settings.vision_max_image_bytes),
            )
        )

    payload_size = sum(len(image.data_url) * 3 // 4 for image in images)
    if payload_size > settings.vision_max_payload_bytes:
        raise VisionInputLimitError("Prepared images exceed the configured semantic-analysis request limit")
    return images


async def classify_analysis(
    provider: VisionProvider,
    before_path: Path,
    after_path: Path,
    computer_vision_result: dict[str, object],
    *,
    settings: Settings,
    location: str | None = None,
    before_acquisition_date: str | None = None,
    after_acquisition_date: str | None = None,
) -> SemanticAnalysis:
    """Prepare bounded full images and top changed-region crops, then classify."""
    regions = computer_vision_result.get("regions", [])
    if not isinstance(regions, list):
        regions = []
    dimensions = computer_vision_result.get("image_dimensions", {})
    comparison_dimensions = dimensions.get("comparison", {}) if isinstance(dimensions, dict) else {}
    images = _prepare_images(before_path, after_path, regions, settings, comparison_dimensions)
    context: dict[str, object] = {
        "location": location,
        "before_acquisition_date": before_acquisition_date,
        "after_acquisition_date": after_acquisition_date,
        "computer_vision": {
            "summary": computer_vision_result.get("summary"),
            "changed_percent": computer_vision_result.get("changed_percent"),
            "changed_pixels": computer_vision_result.get("changed_pixels"),
            "total_pixels": computer_vision_result.get("total_pixels"),
            "registration_status": computer_vision_result.get("registration_status"),
            "warnings": computer_vision_result.get("warnings", []),
            "regions": sorted(regions, key=lambda item: int(item.get("area", 0)), reverse=True)[: settings.vision_max_region_crops],
        },
    }
    return await provider.classify(images, context)

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.routes import analysis, reports, samples


def png_bytes(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".png", image)
    assert success
    return encoded.tobytes()


def test_upload_report_and_annotated_image_flow(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        storage_dir=tmp_path / "storage",
        sample_dir=Path(__file__).resolve().parents[2] / "data" / "samples",
        max_upload_mb=2,
        vision_provider="disabled",
    )
    for route_module in (analysis, reports, samples):
        monkeypatch.setattr(route_module, "get_settings", lambda: settings)

    before = np.zeros((36, 48, 3), dtype=np.uint8)
    after = before.copy()
    after[8:18, 10:20] = (255, 255, 255)
    client = TestClient(app)

    listed = client.get("/api/samples")
    assert listed.status_code == 200
    scenarios = listed.json()
    assert {item["id"] for item in scenarios} == {"vegetation-loss", "new-construction", "flood-expansion"}
    assert all(item["synthetic"] is True for item in scenarios)

    for scenario in scenarios:
        baseline = client.get(scenario["before"]["url"])
        latest = client.get(scenario["after"]["url"])
        assert baseline.status_code == latest.status_code == 200
        result = client.post(
            "/api/analyze",
            files={
                "before_image": (scenario["before"]["filename"], BytesIO(baseline.content), "image/png"),
                "after_image": (scenario["after"]["filename"], BytesIO(latest.content), "image/png"),
            },
        )
        assert result.status_code == 200, f"{scenario['id']}: {result.text}"
        metrics = result.json()
        assert metrics["changed_pixels"] > 0, scenario["id"]
        assert metrics["changed_regions"] > 0, scenario["id"]

    response = client.post(
        "/api/analyze",
        files={
            "before_image": ("before.png", BytesIO(png_bytes(before)), "image/png"),
            "after_image": ("after.png", BytesIO(png_bytes(after)), "image/png"),
        },
        data={"location": "Test site", "before_date": "2025-01-01", "after_date": "2025-02-01"},
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["changed_percent"] > 0
    assert result["location"] == "Test site"
    assert result["before_date"] == "2025-01-01"
    assert result["regions"][0]["id"] == "REG-001"
    report = client.get(result["report_url"])
    assert report.status_code == 200
    assert report.json() == result
    annotated = client.get(result["annotated_image_url"])
    assert annotated.status_code == 200
    assert annotated.headers["content-type"] == "image/png"
    assert annotated.content.startswith(b"\x89PNG\r\n\x1a\n")

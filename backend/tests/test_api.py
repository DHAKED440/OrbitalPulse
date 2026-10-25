from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import Settings
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    settings = Settings(storage_dir=tmp_path / "runtime", max_upload_mb=1, max_image_pixels=100_000)
    monkeypatch.setattr("app.routes.analysis.get_settings", lambda: settings)
    return TestClient(app)


def image_bytes(color=(20, 30, 40), size=(16, 16)):
    image = Image.new("RGB", size, color)
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def upload_pair(before=None, after=None, content_type="image/png"):
    return {
        "before_image": ("before.png", before if before is not None else image_bytes(), content_type),
        "after_image": ("after.png", after if after is not None else image_bytes((200, 200, 200)), content_type),
    }


def test_health_reports_backend_and_ai_configuration(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "ai_configured": False, "ai_status": "unavailable"}


def test_analyze_returns_real_metrics_metadata_and_retained_report(client):
    response = client.post(
        "/api/analyze",
        files=upload_pair(),
        data={"location": "Test site", "before_acquisition_date": "2026-10-01", "after_acquisition_date": "2026-10-20"},
    )

    assert response.status_code == 200
    report = response.json()
    assert report["analysis_id"]
    assert report["changed_percent"] > 0
    assert report["location"] == "Test site"
    assert report["before_acquisition_date"] == "2026-10-01"
    assert report["registration_status"] in {"registered", "fallback_unregistered"}
    assert report["comparison_mode"] == "registered"
    assert report["detection_method"]
    assert report["processing_duration_ms"] >= 0
    assert report["regions"]
    assert report["annotated_preview"].startswith("data:image/jpeg;base64,")
    assert report["difference_preview"].startswith("data:image/jpeg;base64,")
    assert report["report"]["classification_source"] == "COMPUTER_VISION_HEURISTIC"
    assert report["report"]["analysis_timestamp"].endswith("Z") or "+00:00" in report["report"]["analysis_timestamp"]
    assert report["report"]["confidence"] is None
    assert "visual-extent rule" in report["report"]["severity_explanation"]
    assert client.get(f"/api/report/{report['analysis_id']}").json() == report


def test_fallback_report_downloads_match_retained_analysis_and_escape_html(client):
    response = client.post("/api/analyze", files=upload_pair(), data={"location": "<img src=x onerror=alert(1)>"})
    result = response.json()
    analysis_id = result["analysis_id"]

    raw = client.get(f"/api/report/{analysis_id}/download?format=json")
    markdown = client.get(f"/api/report/{analysis_id}/download?format=markdown")
    rendered_html = client.get(f"/api/report/{analysis_id}/download?format=html")
    assert raw.status_code == markdown.status_code == rendered_html.status_code == 200
    assert raw.json() == result
    assert analysis_id in markdown.text
    assert "<img src=x onerror=alert(1)>" not in rendered_html.text
    assert "&lt;img src=x onerror=alert(1)&gt;" in rendered_html.text
    assert "attachment" in rendered_html.headers["content-disposition"]


def test_unsupported_upload_type_returns_415(client):
    response = client.post("/api/analyze", files=upload_pair(content_type="image/gif"))

    assert response.status_code == 415
    assert "PNG, JPEG, and WebP" in response.json()["detail"]


def test_upload_over_limit_returns_413(client, monkeypatch, tmp_path):
    from app.routes import analysis
    current = analysis.get_settings()
    monkeypatch.setattr(analysis, "get_settings", lambda: current.model_copy(update={"storage_dir": tmp_path / "runtime", "max_upload_mb": 1}))
    response = client.post("/api/analyze", files=upload_pair(before=b"x" * (1024 * 1024 + 1)))

    assert response.status_code == 413
    assert "upload limit" in response.json()["detail"]


def test_corrupted_image_returns_400(client):
    response = client.post("/api/analyze", files=upload_pair(before=b"not an image"))

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is not a valid image"


def test_excessive_pixel_count_returns_400(client, monkeypatch):
    from app.routes import analysis
    current = analysis.get_settings()
    monkeypatch.setattr(analysis, "get_settings", lambda: current.model_copy(update={"max_image_pixels": 10}))
    response = client.post("/api/analyze", files=upload_pair())

    assert response.status_code == 400
    assert "pixel limit" in response.json()["detail"]


def test_excessive_dimension_returns_400(client, monkeypatch):
    from app.routes import analysis
    current = analysis.get_settings()
    monkeypatch.setattr(analysis, "get_settings", lambda: current.model_copy(update={"max_image_dimension": 8}))
    response = client.post("/api/analyze", files=upload_pair())

    assert response.status_code == 400
    assert "dimensions" in response.json()["detail"]


def test_missing_uploads_and_invalid_dates_return_422(client):
    missing = client.post("/api/analyze")
    invalid_date = client.post("/api/analyze", files=upload_pair(), data={"before_acquisition_date": "not-a-date"})

    assert missing.status_code == 422
    assert invalid_date.status_code == 422


def test_original_comparison_mode_and_invalid_mode(client):
    original = client.post("/api/analyze", files=upload_pair(), data={"comparison_mode": "original"})
    invalid = client.post("/api/analyze", files=upload_pair(), data={"comparison_mode": "unsupported"})

    assert original.status_code == 200
    assert original.json()["comparison_mode"] == "original"
    assert original.json()["registration_status"] == "not_attempted"
    assert invalid.status_code == 422


def test_provider_is_not_called_without_explicit_consent(client, monkeypatch):
    from app.services import analysis

    class Provider:
        async def classify(self, images, context):
            raise AssertionError("provider must not receive images without consent")

    monkeypatch.setattr(analysis, "get_vision_provider", lambda settings: Provider())
    response = client.post("/api/analyze", files=upload_pair())
    assert response.status_code == 200
    assert response.json()["semantic_status"] == "consent_required"
    assert response.json()["changed_pixels"] >= 0


def test_provider_rate_limit_keeps_computer_vision_result(client, monkeypatch):
    from app.services import analysis
    from app.services.vision import VisionRateLimitError

    class Provider:
        async def classify(self, images, context):
            raise VisionRateLimitError("secret provider details")

    monkeypatch.setattr(analysis, "get_vision_provider", lambda settings: Provider())
    response = client.post("/api/analyze", files=upload_pair(), data={"ai_consent": "true"})
    assert response.status_code == 200
    result = response.json()
    assert result["semantic_status"] == "rate_limited"
    assert result["semantic_analysis"] is None
    assert "secret provider details" not in response.text
    assert result["annotated_preview"].startswith("data:image/jpeg;base64,")


def test_ai_report_uses_validated_classification_and_no_invented_confidence(client, monkeypatch):
    from app.services import analysis
    from app.schemas.analysis import SemanticAnalysis

    class Provider:
        async def classify(self, images, context):
            return SemanticAnalysis(
                category="NATURAL_EVENT",
                observation_types=["flood_like_water_expansion"],
                observation="A larger dark water-like area is visible in the after image.",
                possible_event="Possible water expansion.",
                supporting_evidence=["The water-like region occupies more pixels."],
                alternative_explanations=["Shadow or acquisition differences."],
                unknowns=["Depth and cause cannot be determined."],
                limitations=["Image evidence is not ground truth."],
            )

    monkeypatch.setattr(analysis, "get_vision_provider", lambda settings: Provider())
    response = client.post("/api/analyze", files=upload_pair(), data={"ai_consent": "true"})
    assert response.status_code == 200
    result = response.json()
    assert result["report"]["classification_source"] == "AI_VISION_MODEL"
    assert result["report"]["change_category"] == "NATURAL_EVENT"
    assert result["report"]["confidence"] is None
    assert result["report"]["alternative_explanations"] == ["Shadow or acquisition differences."]
    assert client.get(f"/api/report/{result['analysis_id']}/download?format=json").json() == result


def test_report_not_found_and_empty_samples(client):
    assert client.get("/api/report/not-an-id").status_code == 404
    assert client.get("/api/report/not-an-id/download?format=html").status_code == 404
    assert client.get("/api/report/00000000000000000000000000000000").status_code == 404
    assert client.get("/api/samples").json() == {"samples": []}


def test_cors_allows_local_frontend(client):
    response = client.options(
        "/api/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
